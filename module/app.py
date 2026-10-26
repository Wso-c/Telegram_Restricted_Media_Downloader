# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2024/7/25 12:32
# File:app.py
import os
import time
import datetime
import subprocess

from typing import Union
from functools import wraps

import pyrogram

from module import (
    SLEEP_THRESHOLD,
    console,
    log,
    SOFTWARE_FULL_NAME
)
from module.language import _t
from module.config import UserConfig
from module.util import get_message_dtype
from module.stdio import StatisticalTable
from module.client import TelegramRestrictedMediaDownloaderClient

from module.enums import (
    KeyWord,
    DownloadType,
    DownloadStatus
)
from module.path_tool import (
    validate_title,
    get_extension,
    truncate_filename,
    is_compressed_file,
    extract_full_extension
)


class Application(UserConfig, StatisticalTable):

    def __init__(self):
        UserConfig.__init__(self)
        StatisticalTable.__init__(self)
        self.client = self.build_client()
        self.check_download_type()
        self.current_task_num: int = 0

    def build_client(self) -> pyrogram.Client:
        """用填寫的設定檔,構造pyrogram用戶端。"""
        os.makedirs(self.work_directory, exist_ok=True)
        return TelegramRestrictedMediaDownloaderClient(
            name=SOFTWARE_FULL_NAME.replace(' ', ''),
            api_id=self.api_id,
            api_hash=self.api_hash,
            proxy=self.proxy if self.enable_proxy else None,
            workdir=self.work_directory,
            max_concurrent_transmissions=self.max_download_task,
            sleep_threshold=SLEEP_THRESHOLD
        )
        # v1.3.7 新增多任務下載功能,無論是否Telegram會員。
        # https://stackoverflow.com/questions/76714896/pyrogram-download-multiple-files-at-the-same-time

    def process_shutdown(self, second: int) -> None:
        """處理關機邏輯。"""
        self.shutdown_task(second=second) if self.config.get('is_shutdown') else None

    def get_temp_file_path(
            self,
            message: pyrogram.types.Message,
            dtype: str
    ) -> str:
        """取得下載檔案時的臨時儲存路徑。"""

        def splice_chat_id(_file_name) -> str:
            try:
                chat_id: str = str(getattr(message.chat, 'id', 0))
                if chat_id:
                    temp_directory_with_chat_id: str = os.path.join(self.temp_directory, chat_id)
                    os.makedirs(temp_directory_with_chat_id, exist_ok=True)
                    _file: str = os.path.join(temp_directory_with_chat_id, validate_title(_file_name))
                else:
                    raise ValueError('chat id is empty.')
            except Exception as e:
                _file: str = os.path.join(self.temp_directory, validate_title(_file_name))
                log.warning(f'拼接臨時路徑時,無法取得頻道id,{_t(KeyWord.REASON)}:"{e}"')
            return _file

        os.makedirs(self.temp_directory, exist_ok=True)
        dt = DownloadFileName(message=message, download_type=dtype)
        if dtype in (DownloadType.VIDEO, DownloadType.VIDEO_NOTE):
            file_name: str = dt.get_video_filename()
        elif dtype in (DownloadType.PHOTO, DownloadType.LIVE_PHOTO):
            file_name: str = dt.get_photo_filename()
        elif dtype == DownloadType.DOCUMENT:
            file_name: str = dt.get_document_filename()
        elif dtype in (DownloadType.AUDIO, DownloadType.VOICE, DownloadType.ANIMATION):
            file_name: str = dt.get_filename()
        else:
            file_id = getattr(message, 'id', '0')
            time_format = '%Y-%m-%d_%H-%M-%S'
            file_name: str = f'{file_id} - {datetime.datetime.now().strftime(time_format)}.unknown'
        return truncate_filename(splice_chat_id(file_name))

    def on_record(func):  # noqa.

        @wraps(func)  # noqa.
        def wrapper(self, *args):
            res = func(self, *args)  # noqa.
            download_type = res
            _, file_name, download_status = args
            self.update_download_status(download_type, download_status, file_name)
            return res

        return wrapper

    def increase_task_num(self) -> None:
        """遞增目前下載任務數。"""
        self.current_task_num += 1

    def decrease_task_num(self) -> None:
        """遞減目前下載任務數。"""
        self.current_task_num -= 1

    def update_download_status(
            self,
            download_type: str,
            download_status: str,
            file_name: str
    ):
        type_to_success = {
            DownloadType.PHOTO: self.success_photo,
            DownloadType.VIDEO: self.success_video,
            DownloadType.DOCUMENT: self.success_document,
            DownloadType.AUDIO: self.success_audio,
            DownloadType.VOICE: self.success_voice,
            DownloadType.ANIMATION: self.success_animation,
            DownloadType.VIDEO_NOTE: self.success_video_note,
            DownloadType.LIVE_PHOTO: self.success_live_photo
        }

        type_to_failure = {
            DownloadType.PHOTO: self.failure_photo,
            DownloadType.VIDEO: self.failure_video,
            DownloadType.DOCUMENT: self.failure_document,
            DownloadType.AUDIO: self.failure_audio,
            DownloadType.VOICE: self.failure_voice,
            DownloadType.ANIMATION: self.failure_animation,
            DownloadType.VIDEO_NOTE: self.failure_video_note,
            DownloadType.LIVE_PHOTO: self.failure_live_photo
        }

        type_to_skip = {
            DownloadType.PHOTO: self.skip_photo,
            DownloadType.VIDEO: self.skip_video,
            DownloadType.DOCUMENT: self.skip_document,
            DownloadType.AUDIO: self.skip_audio,
            DownloadType.VOICE: self.skip_voice,
            DownloadType.ANIMATION: self.skip_animation,
            DownloadType.VIDEO_NOTE: self.skip_video_note,
            DownloadType.LIVE_PHOTO: self.skip_live_photo
        }

        if download_status == DownloadStatus.SUCCESS:
            target_set = type_to_success[download_type]
        elif download_status == DownloadStatus.FAILURE:
            target_set = type_to_failure[download_type]
        elif download_status == DownloadStatus.SKIP:
            target_set = type_to_skip[download_type]
        else:
            return
        # 同一檔案只計入一種狀態:寫入目標集合前,先從同類型的其它狀態集合中移除該檔案。
        # 成功記錄為臨時路徑(帶 .temp)、失敗記錄為最終路徑,故按"去掉.temp後綴的歸一化檔案名稱"匹配。
        # 相容同一檔案重試成功的情況,又避免僅按basename誤刪其它同名但不同的檔案。
        base_name: str = os.path.basename(str(file_name))
        norm_name: str = base_name[:-len('.temp')] if base_name.lower().endswith('.temp') else base_name
        for other_set in (type_to_success[download_type], type_to_failure[download_type], type_to_skip[download_type]):
            if other_set is target_set:
                continue
            other_set.discard(file_name)
            other_set.discard(norm_name)
            other_set.difference_update({
                i for i in other_set
                if (os.path.basename(str(i))[:-len('.temp')]
                    if os.path.basename(str(i)).lower().endswith('.temp')
                    else os.path.basename(str(i))) == norm_name
            })
        target_set.add(file_name)

    def get_download_type(self, message: pyrogram.types.Message, default_type: str) -> str:
        """取得訊息的下載類型,只用於展示,不記錄任何統計資訊。"""
        return get_message_dtype(message, self.download_type) or default_type or 'unknown_type'

    @on_record  # noqa.
    def get_file_type(self, *args) -> str:
        message, file_name, download_type = args
        return self.get_download_type(message=message, default_type=download_type)

    def check_download_type(self) -> None:
        for dtype in self.download_type:
            if dtype not in DownloadType():
                self.download_type.remove(dtype)
                p = f'"{dtype}"不是支援的下載類型,已移除。'
                console.log(p, style='#FF4689')
                log.info(p)
        if self.download_type:
            return None
        self.download_type = [_ for _ in DownloadType()]
        self.config['download_type'] = self.download_type
        self.save_config(config=self.config)
        console.log('未找到任何支援的下載類型,已設定為[#f08a5d]「預設」[/#f08a5d]所有已支援的下載類型。')

    def shutdown_task(self, second: int) -> None:
        """下載完成後自動關機的功能。"""
        try:
            if self.platform == 'Windows':
                # 啟動關機命令 目前只支援對 Windows 系統的關機。
                shutdown_command: str = f'shutdown -s -t {second}'
                subprocess.Popen(shutdown_command, shell=True)  # 異步執行關機。
            else:
                shutdown_command: str = f'shutdown -h +{second // 60}'
                subprocess.Popen(shutdown_command, shell=True)  # 異步執行關機。
            # 即時顯示倒計時。
            for remaining in range(second, 0, -1):
                console.print(f'即將在{remaining}秒後關機, 按「CTRL+C」可取消。', end='\r', style='#ff4805')
                time.sleep(1)
            console.print('\n關機即將執行!', style='#f6ad00')
        except KeyboardInterrupt:
            cancel_flag: bool = False
            # 如果用戶按下 CTRL+C，取消關機。
            if self.platform == 'Windows':
                subprocess.Popen('shutdown -a', shell=True)  # 取消關機。
                cancel_flag: bool = True
            else:
                try:
                    # Linux/macOS 取消關機命令。
                    subprocess.Popen('shutdown -c', shell=True)
                    cancel_flag: bool = True
                except Exception as e:
                    log.warning(f'取消關機任務失敗,可能是目前系統不支援,{_t(KeyWord.REASON)}:"{e}"')
            console.print('\n關機已被用戶取消!', style='#4bd898') if cancel_flag else 0
        except Exception as e:
            log.error(f'執行關機任務失敗,可能是目前系統不支援自動關機,{_t(KeyWord.REASON)}:"{e}"')


class DownloadFileName:
    def __init__(
            self,
            message: pyrogram.types.Message,
            download_type: Union[str, 'DownloadType']
    ):
        self.message = message
        self.download_type = download_type

    def get_video_filename(self):
        """處理影片檔案的檔案名稱。"""
        default_mtype: str = 'video/mp4'  # v1.2.8 健全取得檔案名稱邏輯。
        media_object = getattr(self.message, self.download_type)
        title: Union[str, None] = getattr(media_object, 'file_name', None)  # v1.2.8 修復當檔案名稱不存在時,下載報錯問題。
        try:
            if isinstance(title, str):
                if title.lower().startswith('video_'):  # v1.5.6 嘗試修復以日期命名的標題重複下載的問題。
                    title = None
            if title is None:
                title: str = 'None'
            else:
                title: str = os.path.splitext(title)[0]
        except Exception as e:
            title: str = 'None'
            log.warning(f'取得檔案名稱時出錯,已重命名為:"{title}",{_t(KeyWord.REASON)}:"{e}"')
        return '{} - {}.{}'.format(
            getattr(self.message, 'id', '0'),
            title,
            get_extension(
                file_id=media_object.file_id,
                mime_type=getattr(media_object, 'mime_type', default_mtype),
                dot=False
            )
        )

    def get_photo_filename(self):
        """處理圖片檔案的檔案名稱。"""
        default_mtype: str = 'image/jpg'  # v1.2.8 健全取得檔案名稱邏輯。
        media_object = getattr(self.message, self.download_type)
        extension: str = 'unknown'
        if self.download_type == DownloadType.LIVE_PHOTO:
            media_object = getattr(self.message, DownloadType.LIVE_PHOTO)
            extension = 'mov'
        elif self.download_type == DownloadType.PHOTO:
            extension: str = get_extension(
                file_id=media_object.file_id,
                mime_type=default_mtype,
                dot=False
            )
        elif self.download_type == DownloadType.DOCUMENT:
            extension: str = get_extension(
                file_id=media_object.file_id,
                mime_type=getattr(media_object, 'mime_type', default_mtype),
                dot=False
            )
        return '{} - {}.{}'.format(
            getattr(self.message, 'id', '0'),
            getattr(media_object, 'file_unique_id', 'None'),
            extension
        )

    def get_document_filename(self):
        """處理文件媒體的檔案名稱。"""
        try:
            document_obj = getattr(self.message, self.download_type)
            _mime_type = getattr(document_obj, 'mime_type')
            if 'video' in _mime_type:
                return self.get_video_filename()
            elif 'image' in _mime_type:
                return self.get_photo_filename()
            elif _mime_type:
                origin_filename = getattr(document_obj, 'file_name', None)
                if origin_filename and is_compressed_file(origin_filename):
                    log.warning(
                        f'檢測到壓縮檔案"{origin_filename}",為確保完整性(如分卷)已保留原始檔案名稱,如遇命名衝突請手動處理。')
                    return origin_filename
                return self.get_filename()

        except (AttributeError, Exception) as e:
            log.info(f'無法找到該文件的副檔名,{_t(KeyWord.REASON)}:"{e}"')
            file_id = getattr(self.message, 'id', '0')
            time_format = '%Y-%m-%d_%H-%M-%S'
            return f'{file_id} - {datetime.datetime.now().strftime(time_format)}.unknown'

    def get_filename(self):
        try:
            origin_extension = None
            media_obj = getattr(self.message, self.download_type)
            _mime_type = getattr(media_obj, 'mime_type')
            _origin_file_name = getattr(media_obj, 'file_name', None)

            if _origin_file_name:
                origin_extension = extract_full_extension(_origin_file_name)

            if not origin_extension:
                origin_extension = get_extension(
                    file_id=media_obj.file_id,
                    mime_type=_mime_type,
                    dot=False
                )

            return '{} - {}.{}'.format(
                getattr(self.message, 'id', '0'),
                getattr(media_obj, 'file_unique_id', 'None'),
                origin_extension
            )
        except Exception as e:
            log.info(f'無法找到該{_t(self.download_type)}檔案的副檔名,{_t(KeyWord.REASON)}:"{e}"')
            file_id = getattr(self.message, 'id', '0')
            time_format = '%Y-%m-%d_%H-%M-%S'
            return f'{file_id} - {datetime.datetime.now().strftime(time_format)}.unknown'
