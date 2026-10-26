# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2025/2/27 17:38
# File:task.py
import os
import json
import math
import time
import asyncio

from functools import wraps
from typing import (
    Union,
    Optional,
    Callable
)

import pyrogram

from module import (
    log,
    console
)
from module.language import _t
from module.stdio import MetaData
from module.parser import PARSE_ARGS
from module.util import get_work_directory
from module.path_tool import (
    safe_delete,
    calc_sha256,
)
from module.enums import (
    KeyWord,
    UploadStatus,
    DownloadStatus
)


class ChatInfo:
    TITLE: dict = {}

    @staticmethod
    def add(chat: Union[pyrogram.types.Chat, None], chat_id: Union[str, int, None] = None) -> None:
        """快取頻道的標題,避免網頁面板只顯示頻道ID。"""
        if chat is None:
            return
        _chat_id: str = str(chat_id if chat_id is not None else getattr(chat, 'id', ''))
        title: str = str(getattr(chat, 'title', '') or getattr(chat, 'first_name', '') or '')
        if _chat_id and title:
            ChatInfo.TITLE[_chat_id] = title

    @staticmethod
    def get(chat_id: Union[str, int, None]) -> str:
        """取得快取的頻道標題,不存在時返回空字串。"""
        return ChatInfo.TITLE.get(str(chat_id), '')


class DownloadTask:
    """下載任務,按連結維護待下載的訊息與其下載進度統計。"""

    TASKS: dict = {}  # 連結 -> DownloadTask。
    ORDER: list = []  # 連結首次出現的順序,調度器按此順序派發。
    DOWNLOADING_KEYS: set = set()  # (chat_id, message_id) -> 正在下載中的訊息,防止不同連結(如媒體組與組內單條?single)併發下載同一訊息導致資料競爭。

    def __init__(self, link: Union[str, int]):
        self.link: str = str(link)
        self.link_type: Optional[str] = None
        self.chat_id: Union[str, int, None] = None
        self.member_num: int = 0
        self.complete_num: int = 0
        self.file_name: set = set()
        self.error_msg: dict = {}
        self.fail_id: set = set()  # 已徹底失敗(重試耗盡)的訊息ID。
        self.items: dict = {}  # 訊息ID -> 待下載訊息(dict,字段見add_item)。
        self.messages: dict = {}  # 訊息ID -> 原始訊息,供網頁面板重試。
        self.member_info: dict = {}  # 訊息ID -> 該連結下訊息的展示資訊與狀態,完成後不移除。

    @property
    def fail_num(self) -> int:
        """徹底失敗(重試耗盡)的檔案數。"""
        return len(self.fail_id)

    @classmethod
    def get_or_create(cls, link: Union[str, int]) -> 'DownloadTask':
        """取得連結對應的下載任務,不存在時建立並記錄順序。"""
        _link: str = str(link)
        task: Union[DownloadTask, None] = cls.TASKS.get(_link)
        if task is None:
            task = cls(_link)
            cls.TASKS[_link] = task
            cls.ORDER.append(_link)
        return task

    @classmethod
    def get(cls, link: Union[str, int, None]) -> Union['DownloadTask', None]:
        """取得連結對應的下載任務。"""
        return cls.TASKS.get(str(link))

    @classmethod
    def ordered_tasks(cls) -> list:
        """按連結首次出現的順序返回下載任務。"""
        return [cls.TASKS[link] for link in list(cls.ORDER) if link in cls.TASKS]

    @classmethod
    def add_item(
            cls,
            link: Union[str, int],
            chat_id: Union[str, int],
            message: Union[pyrogram.types.Message, list],
            link_type: Optional[str] = None,
            retry: Optional[dict] = None,
            with_upload: Optional[dict] = None,
            diy_download_type: Optional[list] = None
    ) -> None:
        """將訊息加入下載任務,已存在時重置為排隊狀態。"""
        task: DownloadTask = cls.get_or_create(link)
        messages: list = message if isinstance(message, list) else [message]
        retry_dict: dict = retry if retry else {'id': -1, 'count': 0}
        retry_id: int = int(retry_dict.get('id') or -1)
        retry_count: int = int(retry_dict.get('count') or 0)
        if retry_count == 0:
            task.clear_error()  # 非重試(重新拉取)的任務,清空該連結此前的失敗記錄。
            task.clear_fail()
        for _message in messages:
            key: int = int(getattr(_message, 'id', 0))
            task.messages[key] = _message
            if retry_count != 0 and key != retry_id:
                continue  # 重試時只保留需要重試的那條訊息,避免整個媒體組被重複排隊。
            task.remove_fail(message_id=key)  # 重新排隊(含重試)時,清除該訊息的失敗記錄。
            existing: Union[dict, None] = task.items.get(key)
            current_status: Optional[str] = existing.get('status') if existing else None
            # 正在下載中的訊息不降級為排隊:避免面板把"下載中"誤顯示為"佇列中",也避免被調度器重複拉起。
            # 例外: 若該訊息已無活動下載協程佔用(DOWNLOADING_KEYS不含其鍵, 說明此前崩潰/被強殺後未回寫終態)。
            # 則視為孤兒並恢復為排隊,避免重拉鍊接時永久卡在DOWNLOADING。
            dl_key = (_message.chat.id, key) if getattr(_message, 'chat', None) else None
            orphan_downloading: bool = (
                    current_status == DownloadStatus.DOWNLOADING
                    and dl_key is not None
                    and dl_key not in cls.DOWNLOADING_KEYS
            )
            if orphan_downloading:
                cls.DOWNLOADING_KEYS.discard(dl_key)  # 防禦性清理可能殘留的佔用標記。
            re_enqueue: bool = current_status != DownloadStatus.DOWNLOADING or orphan_downloading
            task.update_member(  # 登記連結成員,包括下載完成後仍需展示的訊息。
                message_id=key,
                status=DownloadStatus.PENDING if re_enqueue else None,
                date=str(getattr(_message, 'date', '') or '')[:10]
            )
            item: Union[dict, None] = task.items.get(key)
            if item is None:
                task.items[key] = {
                    'link': task.link,
                    'chat_id': chat_id,
                    'message': _message,
                    'link_type': link_type,
                    'retry': retry_dict,
                    'with_upload': with_upload,
                    'diy_download_type': diy_download_type,
                    'status': DownloadStatus.PENDING,
                    'create_time': time.time(),
                    'meta': None,  # 網頁面板的展示資訊快取。
                    'pause_requested': False,
                    'cancel_requested': False,
                    'future': None
                }
            elif re_enqueue:
                item['status'] = DownloadStatus.PENDING  # 重試時重置狀態。
                item['pause_requested'] = False
                item['cancel_requested'] = False
            # 正在下載中(re_enqueue 為 False)時保留原狀態,不做降級。

    def set_item_status(self, message_id: Union[int, str], status: str) -> None:
        """設定指定訊息的排隊狀態,並同步到連結成員。"""
        item: Union[dict, None] = self.items.get(int(message_id))
        if item is not None:
            item['status'] = status
        self.update_member(message_id=message_id, status=status)

    def update_member(
            self,
            message_id: Union[int, str],
            status: Optional[str] = None,
            name: Optional[str] = None,
            size: Optional[str] = None,
            size_byte: Optional[int] = None,
            date: Optional[str] = None,
            task_id: Optional[int] = None,
            note: Optional[str] = None
    ) -> None:
        """登記或更新連結下某個訊息成員的展示資訊與狀態。"""
        key: int = int(message_id)
        member: dict = self.member_info.get(key) or {
            'name': f'訊息 {key}',
            'size': '',
            'size_byte': 0,
            'date': '',
            'state': DownloadStatus.PENDING,
            'task_id': None,
            'note': ''
        }
        if status:
            member['state'] = status
        if name:
            member['name'] = name
        if size:
            member['size'] = size
        if size_byte is not None:
            member['size_byte'] = int(size_byte)
        if date is not None:
            member['date'] = date
        if task_id is not None:
            member['task_id'] = task_id
        if note:
            member['note'] = note
        self.member_info[key] = member

    def remove_item(self, message_id: Union[int, str]) -> None:
        """從下載任務中移除指定的訊息。"""
        self.items.pop(int(message_id), None)

    def get_pending_items(self, limit: int = 50) -> dict:
        """取得該下載任務中排隊(PENDING)的訊息。"""
        items: list = [item for item in self.items.values() if item.get('status') == DownloadStatus.PENDING]
        return {'items': items[:limit], 'total': len(items)}

    @classmethod
    def queued_items(cls, limit: int = 50) -> list:
        """取得尚未開始下載(PENDING)的訊息。"""
        result: list = []
        for task in cls.ordered_tasks():
            for item in task.items.values():
                if item.get('status') == DownloadStatus.PENDING:
                    result.append(item)
        return result[:limit]

    @classmethod
    def pick_pending(cls) -> Union[dict, None]:
        """按連結首次出現的順序取出一個排隊(PENDING)中的訊息。

        若訊息已被其他任務佔用(正在下載中),則跳過,避免相同訊息被多個連結併發下載導致資料競爭。
        """
        for task in cls.ordered_tasks():
            for item in task.items.values():
                if item.get('status') != DownloadStatus.PENDING:
                    continue
                message = item.get('message')
                if not isinstance(message, pyrogram.types.Message):
                    continue
                if (message.chat.id, message.id) in cls.DOWNLOADING_KEYS:
                    continue
                return item
        return None

    @classmethod
    def has_task(cls) -> bool:
        """判斷是否還存在未處理完畢或未開始的任務。"""
        for task in cls.ordered_tasks():
            for item in task.items.values():
                if item.get('status') in (
                    DownloadStatus.PENDING,
                    DownloadStatus.DOWNLOADING,
                    DownloadStatus.PAUSED
                ):
                    return True
        return False

    @classmethod
    def has_active_task(cls) -> bool:
        """判斷是否仍有需要在關閉前排空的下載任務。"""
        return any(
            item.get('status') in (DownloadStatus.PENDING, DownloadStatus.DOWNLOADING)
            for task in cls.ordered_tasks()
            for item in list(task.items.values())
        )

    @classmethod
    def has_pending_message(cls, message_ids: set, chat_id: Optional[int] = None) -> bool:
        """判斷指定訊息中是否仍有處於排隊或下載中的項(按訊息範圍判定,不做全局檢查)。

        Args:
            message_ids: 需要檢查的message_id集合(如媒體組全部成員)。
            chat_id: 原始頻道ID。給出時按下載佔用鍵(chat_id, message_id)精確匹配,用於捕捉"同一條訊息正被其它連結併發下載中"的情況。

        Returns:
            存在排隊/下載中的成員返回True,否則False。
        """
        if chat_id is not None:
            for message_id in message_ids:
                if (chat_id, message_id) in cls.DOWNLOADING_KEYS:
                    return True
        for task in cls.ordered_tasks():
            for key, item in task.items.items():
                if key not in message_ids:
                    continue
                if chat_id is not None:
                    message = item.get('message')
                    if not isinstance(message, pyrogram.types.Message) or message.chat.id != chat_id:
                        continue
                if item.get('status') in (
                    DownloadStatus.PENDING,
                    DownloadStatus.DOWNLOADING,
                    DownloadStatus.PAUSED
                ):
                    return True
        return False

    def add_file_name(self, file_name: str) -> None:
        """記錄已完成的檔案名稱,並同步完成數。"""
        self.file_name.add(file_name)
        self.complete_num = len(self.file_name)

    def set_error(self, value, key: Optional[str] = None) -> None:
        """記錄下載錯誤資訊。"""
        self.error_msg[key if key else 'all_member'] = value

    def clear_error(self, key: Optional[str] = None) -> None:
        """清除下載錯誤資訊,指定key時只清除該檔案的失敗記錄。"""
        if key is None:
            self.error_msg.clear()
            return
        self.error_msg.pop(key, None)

    def add_fail(self, message_id: Union[int, str]) -> None:
        """記錄徹底失敗(重試耗盡)的訊息。"""
        self.fail_id.add(int(message_id))

    def remove_fail(self, message_id: Union[int, str]) -> None:
        """移除訊息的失敗記錄,該訊息重新排隊或下載成功時調用。"""
        self.fail_id.discard(int(message_id))

    def clear_fail(self) -> None:
        """清空全部失敗記錄。"""
        self.fail_id.clear()

    def on_create_task(func):  # noqa.
        @wraps(func)  # noqa.
        async def wrapper(self, *args, **kwargs):
            message_ids = kwargs.get('message_ids')
            link = message_ids
            if isinstance(message_ids, pyrogram.types.Message):
                link = message_ids.link if message_ids.link else message_ids.id
            task: DownloadTask = DownloadTask.get_or_create(link)
            res: dict = await func(self, *args, **kwargs)  # noqa.
            status: Union[str, None] = res.get('status')
            e_code: Union[dict, None] = res.get('e_code')
            if status == DownloadStatus.FAILURE:
                task.error_msg = e_code
                reason: str = e_code.get('error_msg')
                if reason:
                    log.error(
                        f'{_t(KeyWord.DOWNLOAD_TASK)}'
                        f'{_t(KeyWord.LINK)}:"{link}"{reason},'
                        f'{_t(KeyWord.REASON)}:"{e_code.get("all_member")}",'
                        f'{_t(KeyWord.STATUS)}:{_t(DownloadStatus.FAILURE)}。'
                    )
                else:
                    log.warning(
                        f'{_t(KeyWord.DOWNLOAD_TASK)}'
                        f'{_t(KeyWord.LINK)}:"{link}"{e_code.get("all_member")},'
                        f'{_t(KeyWord.STATUS)}:{_t(DownloadStatus.FAILURE)}。'
                    )
            elif status == DownloadStatus.DOWNLOADING:
                pass
            return res

        return wrapper

    def on_complete(func):  # noqa.
        @wraps(func)  # noqa.
        def wrapper(self, *args, **kwargs):
            res = func(self, *args, **kwargs)  # noqa.
            if all(i is None for i in res):
                return None
            link, file_name = res
            task: Union[DownloadTask, None] = DownloadTask.get(link)
            if task is None:
                return res
            task.add_file_name(file_name)
            if task.member_num == task.complete_num:
                console.log(
                    f'{_t(KeyWord.DOWNLOAD_TASK)}'
                    f'{_t(KeyWord.LINK)}:"{link}",'
                    f'{_t(KeyWord.STATUS)}:{_t(DownloadStatus.SUCCESS)}。'
                )
                task.error_msg = {}
                asyncio.create_task(self.done_notice(f'"{link}"下載完成。'))
                log.info(f'連結:"{link}"下載完成。')
            return res

        return wrapper


class UploadTask:
    DIRECTORY_NAME: str = PARSE_ARGS.temp or os.path.join(get_work_directory(), 'temp')
    PART_SIZE: int = 512 * 1024
    TASKS: set = set()
    TASK_COUNTER: int = 0
    NOTIFY: Optional[Callable] = None
    # 正在上載中的本機檔案路徑 -> {'event': asyncio.Event, 'media': 已上載媒體的引用或None, 'success': bool}。
    # 用於同一檔案併發上載時,後續任務等待主導任務完成後複用其已上載的媒體引用。
    # 直接發往自己的頻道,避免重複上載與源檔案刪除競爭(源檔案僅由主導任務刪除)。
    UPLOADING_KEYS: dict = {}

    def __init__(
            self,
            chat_id: Union[str, int, None],
            file_path: str,
            file_id: int,
            file_size: int,
            file_part: Union[list],
            status: Union[UploadStatus, str],
            error_msg: Union[str, None] = None,
            with_delete: bool = False,
            media_group: Optional[asyncio.Task] = None,
            message_id: Optional[int] = None,
            send_as_media_group: bool = False
    ):
        UploadTask.TASKS.add(self)
        UploadTask.TASK_COUNTER += 1
        self.control_id: int = UploadTask.TASK_COUNTER
        self.chat_id: Union[str, int, None] = chat_id
        self.file_path: str = file_path
        self.file_name: str = os.path.basename(file_path)
        self.file_id: int = file_id
        self.file_size: int = file_size
        self.file_part: list = file_part
        self.status: Union[UploadStatus, str] = status
        self.error_msg: Union[str, None] = error_msg
        self.with_delete: bool = with_delete
        self.file_total_parts = int(math.ceil(file_size / UploadTask.PART_SIZE))
        self.__media_group: asyncio.Task = media_group
        self.message_id: Optional[int] = message_id
        self.send_as_media_group: bool = send_as_media_group
        self.sha256: str = calc_sha256(file_path=self.file_path)
        self.prompt: str = ''
        self.task_id: Union[int, None] = None  # 進度列任務ID,供網頁面板關聯上載進度。
        self.pause_requested: bool = False
        self.cancel_requested: bool = False

    def __setattr__(self, name, value):
        if name.startswith('_'):
            super().__setattr__(name, value)
        else:
            if hasattr(self, name):
                old_value = getattr(self, name)
                if old_value != value:
                    super().__setattr__(name, value)
                    if name == 'status':
                        if value == UploadStatus.PENDING:
                            pass
                        elif value == UploadStatus.UPLOADING:
                            console.log(
                                f'{_t(KeyWord.UPLOAD_TASK)}'
                                f'{_t(KeyWord.CHANNEL)}:"{self.chat_id}",'
                                f'{_t(KeyWord.FILE)}:"{self.file_path}",'
                                f'{_t(KeyWord.SIZE)}:{MetaData.suitable_units_display(self.file_size)},'
                                f'{_t(KeyWord.STATUS)}:{_t(UploadStatus.UPLOADING)}。'
                            )
                        elif value == UploadStatus.SUCCESS:
                            more = ''
                            if self.send_as_media_group:
                                more += f'(等待所有媒體上載完成以媒體組發送)'
                            if self.with_delete:
                                more += '(本機檔案已刪除)'
                            console.log(
                                f'{_t(KeyWord.UPLOAD_TASK)}'
                                f'{_t(KeyWord.CHANNEL)}:"{self.chat_id}",'
                                f'{_t(KeyWord.FILE)}:"{self.file_path}",'
                                f'{_t(KeyWord.SIZE)}:{MetaData.suitable_units_display(self.file_size)},'
                                f'{_t(KeyWord.STATUS)}:{_t(UploadStatus.SUCCESS)}{more}。',
                            )
                            self.notice(f'"{self.file_path}" ⬆️ "{self.chat_id}"上載完成。\n{more}')
                        elif value == UploadStatus.SENT:
                            pass
                        elif value == UploadStatus.FAILURE:
                            log.error(
                                f'{_t(KeyWord.UPLOAD_TASK)}'
                                f'{_t(KeyWord.CHANNEL)}:"{self.chat_id}",'
                                f'{_t(KeyWord.FILE)}:"{self.file_path}",'
                                f'{_t(KeyWord.SIZE)}:{MetaData.suitable_units_display(self.file_size)},'
                                f'{_t(KeyWord.REASON)}:"{self.error_msg}",'
                                f'{_t(KeyWord.STATUS)}:{_t(str(value))}。'
                            )
                            self.notice(f'"{self.file_path}" ⬆️ "{self.chat_id}"上載失敗。')
                    elif name == 'chat_id':
                        if value:
                            self.upload_manager_path: str = os.path.join(
                                UploadTask.DIRECTORY_NAME,
                                f'{self.sha256}.json'
                            )
                        os.makedirs(os.path.dirname(self.upload_manager_path), exist_ok=True)
                        self.load_json()
                    elif name == 'prompt':
                        self.notice(self.prompt)

            else:
                super().__setattr__(name, value)

    @property
    def is_media_group(self) -> bool:
        if self.__media_group:
            return True
        return False

    async def get_media_group(self) -> Union[pyrogram.types.List, None]:
        if self.is_media_group:
            return await self.__media_group

    def notice(self, message: str):
        if isinstance(self.NOTIFY, Callable):
            asyncio.create_task(
                self.NOTIFY(
                    message
                )
            )

    @property
    def complete_task(self) -> int:
        complete = []
        for task in UploadTask.TASKS:
            if task.status == UploadStatus.SUCCESS:
                complete.append(task)
        return len(complete)

    def save_json(self):
        with open(file=self.upload_manager_path, mode='w', encoding='UTF-8') as f:
            json.dump(
                obj={
                    'file_id': self.file_id,
                    'file_size': self.file_size,
                    'file_part': self.file_part,
                    'file_total_parts': self.file_total_parts
                },
                fp=f,
                ensure_ascii=False,
                indent=4
            )

    def load_json(self):
        if not os.path.exists(self.upload_manager_path):
            self.save_json()
            return
        with open(file=self.upload_manager_path, mode='r', encoding='UTF-8') as f:
            _json: dict = {}
            try:
                _json = json.load(f)
            except Exception as e:
                log.info(f'UploadManager的json內容可能為空,即將重新生成,{_t(KeyWord.REASON)}:"{e}"')
                safe_delete(self.upload_manager_path)
                self.save_json()
        self.file_id = _json.get('file_id', self.file_id)
        self.file_size = _json.get('file_size', self.file_size)
        self.file_part = _json.get('file_part', self.file_part)
        self.file_total_parts = _json.get('file_total_parts', self.file_total_parts)

    def update_file_part(self, file_part: int):
        if file_part not in self.file_part and file_part < self.file_total_parts:
            self.file_part.append(file_part)
            self.save_json()

    def reset_upload(self, file_id: int):
        """丟棄歷史分片快取,改用新的file_id重新上載全部分片。"""
        self.file_id = file_id
        self.file_part = []
        self.save_json()

    @staticmethod
    def has_pending_media_group_tasks(
            message_ids: Optional[set] = None,
            origin_chat_id: Optional[int] = None
    ) -> bool:
        """檢查是否還有PENDING/UPLOADING狀態且屬於媒體組的上載任務,或本媒體組成員仍在下載中。
        僅判斷上載佇列不足以判定媒體組是否已齊:某成員可能仍處於下載階段、尚未生成上載任務,此時若判定為"無待處理"會提前發出不完整的相冊,因此同時檢查下載任務。
        Args:
            message_ids: 本媒體組成員的message_id集合。給出時只檢查這些訊息的下載狀態,避免被無關的下載任務拖住;不給出則退化為全局檢查。
            origin_chat_id: 原始頻道ID,配合message_ids精確匹配下載佔用鍵。
        """
        for task in UploadTask.TASKS:
            if task.status in (
                UploadStatus.PENDING,
                UploadStatus.UPLOADING,
                UploadStatus.PAUSED
            ) and task.is_media_group:
                return True
        # 同時檢查本媒體組成員是否仍在下載中(PENDING/DOWNLOADING),避免成員還在下載就被誤判為已齊。
        if not message_ids:
            return DownloadTask.has_task()
        return DownloadTask.has_pending_message(message_ids=message_ids, chat_id=origin_chat_id)

    @staticmethod
    def get_media_group_task_count(message_ids: set) -> int:
        """取得指定media_group_id和message_ids列表中已建立的UploadTask數量。

        Args:
            message_ids: 需要檢查的message_id集合。

        Returns:
            int: 已建立的UploadTask數量(排除已發送的任務)。
        """
        if not message_ids:
            return 0

        count = 0
        for task in UploadTask.TASKS:
            if task.message_id in message_ids and task.status != UploadStatus.SENT:
                count += 1

        return count

    def get_missing_parts(self) -> list:
        """取得缺失的分片索引。"""
        valid_parts = []
        for part in self.file_part:
            if isinstance(part, int) and 0 <= part < self.file_total_parts and part not in valid_parts:
                valid_parts.append(part)
            else:
                log.info(f'過濾無效分片索引:{part}(有效範圍:0-{self.file_total_parts - 1})。')

        if len(valid_parts) != len(self.file_part):
            self.file_part = valid_parts
            self.save_json()
            log.info(f'清理後的分片索引:{valid_parts}。')

        all_parts = set(range(self.file_total_parts))
        uploaded_parts = set(valid_parts)
        missing_parts = sorted(list(all_parts - uploaded_parts))

        log.info(f'總需分片:{all_parts},已上載:{uploaded_parts},缺失:{missing_parts}。')
        return missing_parts
