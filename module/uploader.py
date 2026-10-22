# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2025/9/6 23:00
# File:uploader.py
import os
import hashlib
import asyncio
import inspect

from functools import partial
from typing import (
    List,
    Dict,
    Union,
    Callable
)

import pyrogram

from pyrogram import raw, utils
from pyrogram.errors.exceptions import (
    FilePartMissing,
    FilePartLengthInvalid,
    ChatAdminRequired,
    PhotoInvalidDimensions,
    PhotoSaveFileInvalid
)
from pyrogram.errors.exceptions.bad_request_400 import ChannelPrivate as ChannelPrivate_400
from pyrogram.errors.exceptions.not_acceptable_406 import ChannelPrivate as ChannelPrivate_406
from pymediainfo import MediaInfo

from module import (
    log,
    console
)
from module.language import _t
from module.task import UploadTask
from module.path_tool import get_mime_from_extension
from module.stdio import (
    MetaData,
    ProgressBar
)
from module.path_tool import (
    split_path,
    safe_delete
)
from module.enums import (
    KeyWord,
    UploadStatus
)
from module.util import (
    parse_link,
    is_allow_upload,
    get_chat_with_notify,
    truncate_display_filename
)


class UploadPaused(Exception):
    pass


class UploadCancelled(Exception):
    pass


class TelegramUploader:
    def __init__(
            self,
            download_object
    ):
        self.app = download_object.app
        self.client: pyrogram.Client = self.app.client
        self.loop: asyncio.AbstractEventLoop = download_object.loop
        self.event: asyncio.Event = asyncio.Event()
        self.pb: ProgressBar = download_object.pb
        self.is_premium: bool = self.client.me.is_premium
        self.current_task_num: int = 0
        self.max_upload_task: int = self.app.max_upload_task
        self.max_upload_retries: int = self.app.max_upload_retries
        self.is_bot_running = download_object.is_bot_running
        self.upload_queue: asyncio.Queue = asyncio.Queue()
        self.valid_link_cache = {}
        UploadTask.NOTIFY = download_object.done_notice
        UploadTask.DIRECTORY_NAME = os.path.join(UploadTask.DIRECTORY_NAME, str(download_object.my_id))
        asyncio.create_task(self.send_media_worker())

    @staticmethod
    def release_upload_key(file_path: str) -> None:
        entry = UploadTask.UPLOADING_KEYS.pop(file_path, None)
        if entry is not None:
            entry['success'] = False
            entry['event'].set()

    async def resume_upload(
            self,
            upload_task: UploadTask,
            progress: Callable = None,
            progress_args: tuple = ()
    ):
        missing_parts = upload_task.get_missing_parts()
        chat_id = upload_task.chat_id
        path = upload_task.file_path
        file_id = upload_task.file_id
        file_size: int = upload_task.file_size
        file_total_parts: int = upload_task.file_total_parts
        if not missing_parts:
            # 所有分片都已上載,準備發送訊息。
            log.info(f'所有分片已上載完成,正在發送訊息...')
        else:
            log.info(f'需要上載的分片:{len(missing_parts)}/{file_total_parts}')
        # 上載缺失的分片。
        for part_index in missing_parts:
            if upload_task.cancel_requested:
                raise UploadCancelled
            if upload_task.pause_requested:
                raise UploadPaused
            try:
                # 上載單個分片。
                part_size = 512 * 1024
                await self.client.save_file(
                    path=path,
                    file_id=file_id,
                    file_part=part_index
                )
                # 更新上載記錄。
                upload_task.update_file_part(part_index)
                # 調用進度回調。
                if progress:
                    current_size = min((part_index + 1) * part_size, file_size)
                    func = partial(
                        progress,
                        current_size,
                        file_size,
                        *progress_args
                    )

                    if inspect.iscoroutinefunction(progress):
                        await func()
                    else:
                        await self.loop.run_in_executor(self.client.executor, func)

            except Exception as e:
                log.error(
                    f'{_t(KeyWord.UPLOAD_FILE_PART)}:{part_index},'
                    f'{_t(KeyWord.STATUS)}:{_t(UploadStatus.FAILURE)},'
                    f'{_t(KeyWord.REASON)}:"{e}"'
                )
                raise  # 重新拋出異常,由重試機制處理。

        if upload_task.cancel_requested:
            raise UploadCancelled
        if upload_task.pause_requested:
            raise UploadPaused

        # 檢查是否所有分片都上載完成。
        if len(upload_task.file_part) != file_total_parts:
            raise Exception(f'分片上載不完整:{len(upload_task.file_part)}/{file_total_parts}')

        is_big = file_size > 10 * 1024 * 1024
        if is_big:
            file = raw.types.InputFileBig(
                id=file_id,
                parts=file_total_parts,
                name=os.path.basename(path)
            )
        else:
            md5_hash = hashlib.md5()
            with open(path, 'rb') as f:
                for chunk in iter(lambda: f.read(8192), b''):
                    md5_hash.update(chunk)
            md5_sum = ''.join([hex(i)[2:].zfill(2) for i in md5_hash.digest()])

            file = raw.types.InputFile(
                id=file_id,
                parts=file_total_parts,
                name=os.path.basename(path),
                md5_checksum=md5_sum
            )

        file_path: Union[str, None] = getattr(file, 'name', '')
        if not file_path:
            file_path = str(path) if isinstance(path, str) else ''

        mime_type = self.client.guess_mime_type(file_path) or get_mime_from_extension(file_path)
        file_name = split_path(file_path).get('file_name', 'file')

        if file_path.lower().endswith(('.jpg', '.jpeg', '.png', '.gif', '.webp')):
            try:
                media = raw.types.InputMediaUploadedPhoto(
                    file=file,
                    spoiler=False
                )
                media = await self.client.invoke(
                    raw.functions.messages.UploadMedia(
                        peer=await self.client.resolve_peer(chat_id),
                        media=media
                    )
                )
                media = raw.types.InputMediaPhoto(
                    id=raw.types.InputPhoto(
                        id=media.photo.id,
                        access_hash=media.photo.access_hash,
                        file_reference=media.photo.file_reference
                    ),
                    spoiler=False
                )
            except (PhotoInvalidDimensions, PhotoSaveFileInvalid) as e:
                obj: str = ''
                if isinstance(e, PhotoInvalidDimensions):
                    obj: str = '尺寸'
                elif isinstance(e, PhotoSaveFileInvalid):
                    obj: str = '大小'
                p = f'[圖片]:"{file_path}"因來自Telegram的{obj}限制,回退為檔案格式進行上載,{_t(KeyWord.REASON)}:"{e}"'
                log.info(p)
                console.log(p, style='#FF4689')
                attributes = [raw.types.DocumentAttributeFilename(file_name=file_name)]
                media = await self.get_input_media_document(
                    chat_id=chat_id,
                    file=file,
                    attributes=attributes,
                    mime_type=mime_type
                )
        else:
            attributes = [raw.types.DocumentAttributeFilename(file_name=file_name)]
            if file_path.lower().endswith(('.mp4', '.mov', '.avi', '.mkv')):
                video_meta: Union[dict, None] = self.get_video_info(path)
                if video_meta:
                    attributes.append(raw.types.DocumentAttributeVideo(
                        supports_streaming=True,
                        duration=video_meta.get('duration'),
                        w=video_meta.get('width'),
                        h=video_meta.get('height')
                    ))
                    log.info(f'影片"{file_path}"將以原本格式進行上載。')
                else:
                    p = f'[影片]:"{file_path}"取得影片元資料失敗,回退為檔案格式進行上載。'
                    log.info(p)
                    console.log(p, style='#FF4689')
            media = await self.get_input_media_document(
                chat_id=chat_id,
                file=file,
                attributes=attributes,
                mime_type=mime_type
            )
        # 登記本檔案的上載結果,供後續同檔案任務(等待中的)複用其媒體引用直接發往各自頻道。
        entry = UploadTask.UPLOADING_KEYS.get(upload_task.file_path)
        if entry is not None:
            entry['media'] = media
            entry['success'] = True
            entry['event'].set()
        self.upload_queue.put_nowait((media, upload_task))

    async def send_media_worker(self):
        # 在函數內部使用本機快取。
        media_group_cache = {}  # media_group_id -> {message_id: media, ...}
        media_group_poll_tasks = {}  # media_group_id -> polling_task

        while self.is_bot_running:
            try:
                media, upload_task = await self.upload_queue.get()

                log.info(
                    f'[Upload Worker]取得到上載任務,'
                    f'chat_id={upload_task.chat_id}, '
                    f'is_media_group={upload_task.is_media_group}, '
                    f'message_id={upload_task.message_id}'
                )

                if upload_task.is_media_group and upload_task.send_as_media_group:
                    try:
                        media_group = await upload_task.get_media_group()
                        if not media_group:
                            log.info(f'[Upload Worker]警告:media_group為空。')
                            continue

                        media_group_id = media_group[0].media_group_id
                        if not media_group_id:
                            log.info(f'[Upload Worker]警告:media_group_id為空。')
                            # 如果不是媒體組，則作為單條訊息發送。
                            await self.send_media(media, upload_task)
                            continue

                        chat_id = upload_task.chat_id
                        message_id = upload_task.message_id

                        if media_group_id not in media_group_cache:
                            # 使用字典來儲存，鍵為message_id，值為InputSingleMedia。
                            media_group_cache[media_group_id] = {}

                        # 以message_id為鍵儲存。
                        media_group_cache[media_group_id][message_id] = raw.types.InputSingleMedia(
                            media=media,
                            random_id=self.client.rnd_id(),
                            **await utils.parse_text_entities(
                                self.client,
                                text='',
                                parse_mode=None,
                                entities=None
                            )
                        )
                        prompt = f'[媒體組]:"{media_group_id}"已收集{len(media_group_cache[media_group_id])}個媒體,等待所有媒體上載完成。'
                        console.log(
                            f'{_t(KeyWord.UPLOAD_TASK)}{prompt}')
                        upload_task.prompt = prompt

                        # 如果該媒體組還沒有輪詢任務，啟動一個。
                        if media_group_id not in media_group_poll_tasks:
                            # 取得media_group中所有需要上載的message_id。
                            message_ids = {m.id for m in media_group}
                            poll_task = asyncio.create_task(
                                self.send_media_group(
                                    chat_id=chat_id,
                                    media_group=media_group,
                                    media_group_id=media_group_id,
                                    message_ids=message_ids,
                                    media_group_cache=media_group_cache,
                                    media_group_poll_tasks=media_group_poll_tasks)
                            )
                            media_group_poll_tasks[media_group_id] = poll_task
                            log.info(
                                f'[Upload Worker]啟動媒體組"{media_group_id}"的輪詢任務,預期{len(message_ids)}個檔案。')

                    except Exception as e:
                        log.info(f'[Upload Worker]處理媒體組時出錯,回退到單條發送,{_t(KeyWord.REASON)}:"{e}"')
                        # 出錯時回退到單條發送。
                        await self.send_media(media, upload_task)

                else:
                    await self.send_media(media, upload_task)

            except Exception as e:
                log.error(f'[Upload Worker]錯誤,{_t(KeyWord.REASON)}:"{e}"', exc_info=True)
            finally:
                self.upload_queue.task_done()

    async def send_media_group(
            self,
            chat_id: int,
            media_group: list,
            media_group_id: int,
            message_ids: set,
            media_group_cache: dict,
            media_group_poll_tasks: dict
    ):
        try:
            # 原始頻道ID:下載佔用鍵為(原始chat_id, message_id),用於精確判定本相冊成員是否仍在下載中。
            origin_chat_id = getattr(getattr(media_group[0], 'chat', None), 'id', None) if media_group else None
            while self.is_bot_running:
                await asyncio.sleep(1)  # 每1秒檢查一次。

                # 檢查兩個條件：
                # 1. 所有需要上載的檔案都已建立UploadTask（沒有檔案還在下載中）。
                # 2. 沒有待處理的媒體組任務。
                created_count = UploadTask.get_media_group_task_count(message_ids)
                no_pending = not UploadTask.has_pending_media_group_tasks(
                    message_ids=message_ids, origin_chat_id=origin_chat_id)
                collected_count = len(media_group_cache.get(media_group_id, {}))

                log.debug(
                    f'[Upload Worker]發送媒體組"{media_group_id}"建立的任務數:{created_count},目前是否有任務:{not no_pending},媒體組收集的媒體數:{collected_count}。')
                if created_count == collected_count and no_pending:
                    # 所有需要上載的檔案都已建立且沒有待處理任務，發送已收集的媒體。
                    if media_group_id in media_group_cache:
                        # 按照原始message_id的順序排序。
                        sorted_media_group = []
                        for message in media_group:
                            msg_id = message.id
                            # 只發送在message_ids中的（用戶選擇的範圍）。
                            if msg_id in message_ids and msg_id in media_group_cache[media_group_id]:
                                sorted_media_group.append(media_group_cache[media_group_id][msg_id])

                        if sorted_media_group:
                            log.info(
                                f'[Upload Worker]發送媒體組"{media_group_id}",包含{len(sorted_media_group)}個媒體（共預期{len(message_ids)}個）。')
                            try:
                                await self.client.invoke(
                                    raw.functions.messages.SendMultiMedia(
                                        peer=await self.client.resolve_peer(chat_id),
                                        multi_media=sorted_media_group
                                    ),
                                    sleep_threshold=60
                                )
                                prompt = f'[媒體組]:"{media_group_id}"上載完成,包含{len(sorted_media_group)}個媒體。'
                                console.log(f'{_t(KeyWord.UPLOAD_TASK)}{prompt}')
                                # 將已發送的媒體組任務狀態更新為SENT。
                                for task in UploadTask.TASKS:
                                    if task.message_id in message_ids and task.status == UploadStatus.SUCCESS:
                                        task.status = UploadStatus.SENT
                                self.valid_link_cache = {k: v for k, v in self.valid_link_cache.items() if v != chat_id}
                            except Exception as send_error:
                                log.error(f'[Upload Worker]發送媒體組失敗,{_t(KeyWord.REASON)}:"{send_error}"',
                                          exc_info=True)
                        else:
                            log.warning(f'[Upload Worker]發送媒體組"{media_group_id}"沒有可發送的媒體。')

                    # 清理快取和輪詢任務。
                    if media_group_id in media_group_cache:
                        del media_group_cache[media_group_id]
                    if media_group_id in media_group_poll_tasks:
                        del media_group_poll_tasks[media_group_id]
                    break  # 輪詢結束。
                else:
                    # 還有檔案在下載中或還在上載，繼續等待。
                    if created_count < len(message_ids):
                        log.debug(
                            f'[Upload Worker]發送媒體組"{media_group_id}"已建立{created_count}/{len(message_ids)}個任務，等待下載...')
        except asyncio.CancelledError:
            log.info(f'[Upload Worker]發送媒體組"{media_group_id}"輪詢任務被取消。')
            if media_group_id in media_group_poll_tasks:
                del media_group_poll_tasks[media_group_id]
        except Exception as e:
            log.error(
                f'[Upload Worker]發送媒體組"{media_group_id}"輪詢任務出錯,{_t(KeyWord.REASON)}:"{e}"',
                exc_info=True
            )
            if media_group_id in media_group_cache:
                del media_group_cache[media_group_id]
            if media_group_id in media_group_poll_tasks:
                del media_group_poll_tasks[media_group_id]

    async def send_media(
            self,
            media: raw.types.InputMediaDocument,
            upload_task: UploadTask
    ):
        """發送單條媒體訊息。"""
        try:
            chat_id = upload_task.chat_id
            await self.client.invoke(
                raw.functions.messages.SendMedia(
                    peer=await self.client.resolve_peer(chat_id),
                    media=media,
                    random_id=self.client.rnd_id(),
                    **await utils.parse_text_entities(
                        self.client,
                        text='',
                        parse_mode=None,
                        entities=None
                    )
                )
            )
            upload_task.status = UploadStatus.SENT
            self.valid_link_cache = {k: v for k, v in self.valid_link_cache.items() if v != chat_id}
            log.info(f'[Upload Worker]單條訊息發送完成,{_t(KeyWord.CHANNEL)}:"{chat_id}"')
        except Exception as e:
            log.error(f'"[Upload Worker]發送單條訊息失敗,{_t(KeyWord.REASON)}:"{e}"', exc_info=True)

    @staticmethod
    def get_video_info(video_path: str) -> Union[Dict[str, int], None]:
        try:
            media_info = MediaInfo.parse(video_path)
            video_track = media_info.video_tracks[0]
            meta = {
                'width': video_track.width,
                'height': video_track.height,
                'duration': round(video_track.duration / 1000)
            }
            if all(meta.values()):
                return meta
        except Exception as e:
            log.error(f'取得影片元資料失敗,{_t(KeyWord.REASON)}:"{e}"')

    async def get_input_media_document(
            self,
            chat_id: Union[int, str],
            file: Union[raw.types.InputFile, raw.types.InputFileBig],
            attributes: List[raw.types.DocumentAttributeFilename],
            mime_type: str,
    ) -> raw.types.InputMediaDocument:
        media = raw.types.InputMediaUploadedDocument(
            mime_type=mime_type,
            file=file,
            attributes=attributes,
            force_file=False,
            thumb=None
        )
        media = await self.client.invoke(
            raw.functions.messages.UploadMedia(
                peer=await self.client.resolve_peer(chat_id),
                media=media
            )
        )
        return raw.types.InputMediaDocument(
            id=raw.types.InputDocument(
                id=media.document.id,
                access_hash=media.document.access_hash,
                file_reference=media.document.file_reference
            )
        )

    async def create_upload_task(
            self,
            link: Union[str, int],
            upload_task: UploadTask
    ) -> None:
        if isinstance(link, str):
            if link.startswith('https://t.me/'):
                if link in self.valid_link_cache:
                    chat_id: Union[int, str] = self.valid_link_cache[link]
                else:
                    target_meta: Union[dict, None] = await parse_link(
                        client=self.client,
                        link=link
                    )
                    chat_id: Union[int, str] = target_meta.get('chat_id')
                    target_chat = await get_chat_with_notify(
                        user_client=self.client,
                        chat_id=chat_id
                    )
                    if not target_chat:
                        raise ValueError
                    self.valid_link_cache[link] = chat_id
            else:
                chat_id: Union[int, str] = link
        else:
            chat_id: Union[int, str] = link
        file_path = upload_task.file_path
        file_size: int = os.path.getsize(file_path)
        upload_task.chat_id = chat_id
        if not is_allow_upload(file_size, self.is_premium):
            upload_task.error_msg = '上載大小超過限制(普通用戶2000MiB,會員用戶4000MiB)'
            upload_task.status = UploadStatus.FAILURE
            return None
        elif file_size == 0:
            upload_task.error_msg = '上載檔案大小為0'
            upload_task.status = UploadStatus.FAILURE
            return None

        retry = 0
        reset = 0
        while retry < self.max_upload_retries:
            if upload_task.cancel_requested:
                upload_task.status = UploadStatus.CANCELLED
                return None
            if upload_task.pause_requested:
                upload_task.status = UploadStatus.PAUSED
                return None
            try:
                await self.__add_task(
                    upload_task=upload_task
                )
                return None
            except UploadPaused:
                self.release_upload_key(upload_task.file_path)
                upload_task.status = UploadStatus.PAUSED
                return None
            except UploadCancelled:
                self.release_upload_key(upload_task.file_path)
                upload_task.status = UploadStatus.CANCELLED
                return None
            except FilePartMissing as e:
                missing_part = getattr(e, 'value')
                console.log(
                    f'{_t(KeyWord.UPLOAD_FILE_PART)}:{missing_part},'
                    f'{_t(KeyWord.STATUS)}:{_t(UploadStatus.UPLOADING)}。'
                )
                fp = upload_task.file_part
                if missing_part in fp:
                    fp.remove(missing_part)
                continue
            except FilePartLengthInvalid as e:
                # 複用了歷史會話的分片快取,但伺服器端已不存在這些分片,最終上報分片長度無效,需要丟棄快取並換用新的file_id重傳全部分片。
                if reset >= self.max_upload_retries:
                    upload_task.error_msg = str(e)
                    upload_task.status = UploadStatus.FAILURE
                    return None
                reset += 1
                upload_task.reset_upload(file_id=self.client.rnd_id())
                console.log(
                    f'{_t(KeyWord.UPLOAD_TASK)}'
                    f'{_t(KeyWord.RESUME)}:"{file_path}",'
                    f'{_t(KeyWord.RETRY_TIMES)}:{reset}/{self.max_upload_retries},'
                    f'{_t(KeyWord.REASON)}:"{e}"'
                )
                continue
            except (ChatAdminRequired, ChannelPrivate_400, ChannelPrivate_406) as e:
                upload_task.error_msg = str(e)
                upload_task.status = UploadStatus.FAILURE
                return None
            except Exception as e:
                console.log(
                    f'{_t(KeyWord.UPLOAD_TASK)}'
                    f'{_t(KeyWord.RE_UPLOAD)}:"{file_path}",'
                    f'{_t(KeyWord.RETRY_TIMES)}:{retry + 1}/{self.max_upload_retries},'
                    f'{_t(KeyWord.REASON)}:"{e}"'
                )
                retry += 1  # 只有非FilePartMissing異常才遞增重試計數。
                if retry == self.max_upload_retries:
                    upload_task.error_msg = str(e)
                    upload_task.status = UploadStatus.FAILURE

    async def __add_task(
            self,
            upload_task: UploadTask
    ):
        file_path = upload_task.file_path
        # 同一本機檔案已在上載中:
        # 等待主導任務完成,複用其已上載的媒體引用直接發往本任務頻道,避免重複上載與源檔案刪除競爭。
        if file_path in UploadTask.UPLOADING_KEYS:
            entry = UploadTask.UPLOADING_KEYS[file_path]
            while not entry['event'].is_set():
                if upload_task.cancel_requested:
                    raise UploadCancelled
                if upload_task.pause_requested:
                    raise UploadPaused
                try:
                    await asyncio.wait_for(entry['event'].wait(), timeout=0.5)
                except asyncio.TimeoutError:
                    pass
            if (entry['success']
                    and entry['media'] is not None
                    and not (upload_task.is_media_group and upload_task.send_as_media_group)):
                return await self.reuse_upload(upload_task, entry['media'])
            UploadTask.UPLOADING_KEYS.pop(file_path, None)  # 主導任務失敗,或本任務為媒體組(避免錯組):本任務轉為新的主導任務重新上載。
        # 成為該檔案的主導上載任務,登記以便後續同檔案任務複用。
        UploadTask.UPLOADING_KEYS[file_path] = {
            'event': asyncio.Event(),
            'media': None,
            'success': False
        }
        file_size = upload_task.file_size
        while self.current_task_num >= self.max_upload_task:
            if upload_task.cancel_requested:
                self.release_upload_key(file_path)
                raise UploadCancelled
            if upload_task.pause_requested:
                self.release_upload_key(file_path)
                raise UploadPaused
            await self.event.wait()
            self.event.clear()
        upload_task.status = UploadStatus.UPLOADING
        console.log(f'{_t(KeyWord.UPLOAD_TASK)}{_t(KeyWord.RESUME)}:"{file_path}"。') if upload_task.file_part else None
        format_file_size: str = MetaData.suitable_units_display(file_size)
        upload_file_name: str = split_path(file_path).get('file_name') or ''
        task_id = self.pb.progress.add_task(
            description='📤',
            channel=str(upload_task.chat_id) if upload_task.chat_id else '',
            filename=truncate_display_filename(upload_file_name),
            fullname=upload_file_name,  # 完整檔案名稱供網頁面板展示,filename按終端機寬度截斷僅供終端機顯示。
            info=f'0.00B/{format_file_size}',
            total=file_size
        )
        upload_task.task_id = task_id  # 記錄進度列任務ID,網頁面板據此關聯該上載任務的即時進度。
        _task = self.loop.create_task(
            self.resume_upload(
                upload_task=upload_task,
                progress=self.pb.upload,
                progress_args=(
                    self.pb.progress,
                    task_id,
                    upload_task
                )
            )
        )
        _task.add_done_callback(
            partial(
                self.upload_complete_callback,
                upload_task,
                task_id
            )
        )

        if _task:
            self.current_task_num += 1
            MetaData.print_current_task_num(
                prompt=_t(KeyWord.CURRENT_UPLOAD_TASK),
                num=self.current_task_num
            )
            await _task

    async def reuse_upload(
            self,
            upload_task: UploadTask,
            media
    ):
        """複用主導任務已上載的媒體引用,直接發往本任務頻道,避免重複上載與源檔案刪除競爭。"""
        upload_task.status = UploadStatus.UPLOADING
        try:
            await self.send_media(media, upload_task)
        except Exception as e:  # send_media 自身吞異常,此處僅為兜底。
            log.error(f'[複用上載]發送失敗,{_t(KeyWord.REASON)}:"{e}"', exc_info=True)
            upload_task.status = UploadStatus.FAILURE
            upload_task.error_msg = str(e)
            return None
        # send_media 內部只記錄日誌不拋異常,故以其是否把狀態置為 SENT 判定成敗。
        if upload_task.status != UploadStatus.SENT:
            upload_task.status = UploadStatus.FAILURE
            upload_task.error_msg = '複用已上載媒體發送失敗,詳見日誌。'
            log.error(f'[複用上載]"{upload_task.file_path}"發送失敗。')
            return None
        # 不做 UploadTask.TASKS.discard:與正常上載一致地保留在任務集中,供網頁面板與統計表展示。
        return None

    def upload_complete_callback(
            self,
            upload_task,
            task_id,
            _future
    ):
        try:
            _ = _future.result()
        except UploadPaused:
            self.current_task_num -= 1
            self.pb.progress.remove_task(task_id=task_id)
            self.event.set()
            entry = UploadTask.UPLOADING_KEYS.pop(upload_task.file_path, None)
            if entry is not None:
                entry['success'] = False
                entry['event'].set()
            upload_task.status = UploadStatus.PAUSED
            return
        except UploadCancelled:
            self.current_task_num -= 1
            self.pb.progress.remove_task(task_id=task_id)
            self.event.set()
            entry = UploadTask.UPLOADING_KEYS.pop(upload_task.file_path, None)
            if entry is not None:
                entry['success'] = False
                entry['event'].set()
            upload_task.status = UploadStatus.CANCELLED
            return
        except (asyncio.CancelledError, Exception) as e:
            self.current_task_num -= 1
            self.pb.progress.remove_task(task_id=task_id)
            self.event.set()
            # 主導任務失敗:通知等待者並清理,使後續同檔案任務可重新上載。
            entry = UploadTask.UPLOADING_KEYS.get(upload_task.file_path)
            if entry is not None:
                entry['success'] = False
                entry['event'].set()
            UploadTask.UPLOADING_KEYS.pop(upload_task.file_path, None)
            log.info(e)
            return
        file_path: str = upload_task.file_path
        self.current_task_num -= 1
        self.pb.progress.remove_task(task_id=task_id)
        # 成功後保留 UPLOADING_KEYS 條目(含已上載媒體引用),供等待中的同檔案任務複用;
        # 源檔案刪除僅由主導任務執行,複用任務不重複刪除。
        if upload_task.file_size < 10 * 1024 * 1024:
            if not safe_delete(os.path.join(UploadTask.DIRECTORY_NAME, f'{upload_task.sha256}.json')):
                log.warning(f'無法刪除"{os.path.basename(file_path)}"的上載快取管理檔案。')
            else:
                log.info(f'成功刪除"{os.path.basename(file_path)}"的上載快取管理檔案。')
        self.event.set()
        safe_delete(file_path) if upload_task.with_delete else None
        upload_task.status = UploadStatus.SUCCESS
        MetaData.print_current_task_num(
            prompt=_t(KeyWord.CURRENT_UPLOAD_TASK),
            num=self.current_task_num
        )

    async def web_control_task(self, task_id: str, action: str) -> dict:
        try:
            control_id = int(task_id)
        except (TypeError, ValueError):
            return {'status': False, 'e_code': '上載任務編號無效。'}
        upload_task = next((task for task in UploadTask.TASKS if task.control_id == control_id), None)
        if upload_task is None:
            return {'status': False, 'e_code': '找不到指定的上載項目。'}
        if action == 'pause':
            if upload_task.status not in (UploadStatus.PENDING, UploadStatus.UPLOADING):
                return {'status': False, 'e_code': '此上載項目目前無法暫停。'}
            upload_task.pause_requested = True
            self.event.set()
            return {'status': True}
        if action == 'resume':
            if upload_task.status != UploadStatus.PAUSED:
                return {'status': False, 'e_code': '只有已暫停的上載項目可以繼續。'}
            if not os.path.isfile(upload_task.file_path):
                return {'status': False, 'e_code': '找不到待上載的本機檔案。'}
            upload_task.pause_requested = False
            upload_task.cancel_requested = False
            upload_task.status = UploadStatus.PENDING
            asyncio.create_task(self.create_upload_task(link=upload_task.chat_id, upload_task=upload_task))
            return {'status': True}
        if action == 'cancel':
            if upload_task.status not in (UploadStatus.PENDING, UploadStatus.UPLOADING, UploadStatus.PAUSED):
                return {'status': False, 'e_code': '此上載項目目前無法取消。'}
            upload_task.cancel_requested = True
            upload_task.pause_requested = False
            self.event.set()
            if upload_task.status in (UploadStatus.PENDING, UploadStatus.PAUSED):
                upload_task.status = UploadStatus.CANCELLED
            return {'status': True}
        return {'status': False, 'e_code': '未知的上載操作。'}

    def download_upload(self, with_upload: dict, file_path: str):
        if isinstance(with_upload, dict):
            asyncio.create_task(
                self.create_upload_task(
                    link=with_upload.get('link'),
                    upload_task=UploadTask(
                        chat_id=None,
                        file_path=file_path,
                        file_id=self.client.rnd_id(),
                        file_size=os.path.getsize(file_path),
                        file_part=[],
                        status=UploadStatus.PENDING,
                        with_delete=with_upload.get('with_delete'),
                        media_group=with_upload.get('media_group'),
                        message_id=with_upload.get('message_id'),
                        send_as_media_group=with_upload.get('send_as_media_group', False)
                    )
                )
            )
