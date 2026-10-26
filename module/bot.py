# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2025/1/24 21:27
# File:bot.py
import os
import copy
import asyncio
import datetime
import calendar

from functools import partial
from dataclasses import dataclass
from abc import (
    ABC,
    abstractmethod
)
from typing import (
    List,
    Dict,
    Union,
    Optional,
    Callable
)

import pyrogram
from pyrogram.types.messages_and_media import (
    ReplyParameters,
    LinkPreviewOptions
)
from pyrogram.handlers import (
    MessageHandler,
    CallbackQueryHandler
)
from pyrogram.errors import (
    FloodWait,
    FloodPremiumWait
)
from pyrogram.errors.exceptions.bad_request_400 import (
    MessageNotModified,
    AccessTokenInvalid
)
from pyrogram.types.bots_and_keyboards import (
    BotCommand,
    CallbackQuery,
    InlineKeyboardButton,
    InlineKeyboardMarkup
)

from module import (
    __version__,
    __copyright__,
    __license__,
    log,
    console,
    VERSION_SEMVER,
    SOFTWARE_SHORT_NAME
)
from module.remote import rc
from module.language import _t
from module.stdio import MetaData

from module.config import GlobalConfig
from module.path_tool import safe_scan_directory_file
from module.task import (
    DownloadTask,
    UploadTask
)
from module.util import (
    is_docker,
    parse_link,
    safe_index,
    check_update,
    safe_message,
    is_allow_upload,
    get_valid_chat_id
)
from module.enums import (
    KeyWord,
    BotButton,
    BotMessage,
    UploadStatus,
    DownloadType,
    BotCommandText,
    BotCallbackText,
    CalenderKeyboard
)


class Bot:
    BOT_NAME: str = 'TRMD_BOT'
    COMMANDS: List[BotCommand] = [
        BotCommand(BotCommandText.HELP[0], BotCommandText.HELP[1]),
        BotCommand(BotCommandText.DOWNLOAD[0], BotCommandText.DOWNLOAD[1].replace('`', '')),
        BotCommand(BotCommandText.TABLE[0], BotCommandText.TABLE[1]),
        BotCommand(BotCommandText.FORWARD[0], BotCommandText.FORWARD[1].replace('`', '')),
        BotCommand(BotCommandText.EXIT[0], BotCommandText.EXIT[1]),
        BotCommand(BotCommandText.LISTEN_DOWNLOAD[0], BotCommandText.LISTEN_DOWNLOAD[1].replace('`', '')),
        BotCommand(BotCommandText.LISTEN_FORWARD[0], BotCommandText.LISTEN_FORWARD[1].replace('`', '')),
        BotCommand(BotCommandText.LISTEN_INFO[0], BotCommandText.LISTEN_INFO[1]),
        BotCommand(BotCommandText.UPLOAD[0], BotCommandText.UPLOAD[1].replace('`', '')),
        BotCommand(BotCommandText.UPLOAD_R[0], BotCommandText.UPLOAD_R[1].replace('`', '')),
        BotCommand(BotCommandText.DOWNLOAD_CHAT[0], BotCommandText.DOWNLOAD_CHAT[1].replace('`', ''))
    ]
    LINK_PREVIEW_OPTIONS = LinkPreviewOptions(is_disabled=True)

    def __init__(self):
        self.application = None
        self.user: Union[pyrogram.Client, None] = None
        self.bot: Union[pyrogram.Client, None] = None
        self.forwarded_media_handler: Union[MessageHandler, None] = None
        self.is_bot_running: bool = False
        self.bot_task_link: set = set()
        self.gc = GlobalConfig()
        self.root: list = []
        self.last_client: Union[pyrogram.Client, None] = None
        self.last_message: Union[pyrogram.types.Message, None] = None
        self.listen_download_chat: dict = {}
        self.listen_forward_chat: dict = {}
        self.handle_media_groups: dict = {}
        self.download_chat_filter: dict = {}
        self.adding_keywords: list = []  # 用於跟蹤正在添加的關鍵詞列表。
        self.keyword_handler: Union[MessageHandler, None] = None  # 關鍵詞輸入模式的handler。

    def add_handler(self, handler, group: int = 0):
        """添加handler到指定的group。直接操作dispatcher.groups以確保正確添加。"""
        if group not in self.bot.dispatcher.groups:
            self.bot.dispatcher.groups[group] = []
        self.bot.dispatcher.groups[group].append(handler)
        log.info(f'添加handler到group={group},目前handler數量:{len(self.bot.dispatcher.groups[group])}')

    def remove_handler(self, handler, group: int = 0):
        """從指定的group中移除handler。直接操作dispatcher.groups以確保正確移除。"""
        if group in self.bot.dispatcher.groups and handler in self.bot.dispatcher.groups[group]:
            self.bot.dispatcher.groups[group].remove(handler)
            log.info(f'從group={group}移除handler,剩餘handler數量:{len(self.bot.dispatcher.groups[group])}')

    def add_keyword_mode_handler(
            self,
            chat_id,
            callback_query: CallbackQuery,
            callback_prompt: Callable,
            enable: bool,
    ):
        """添加或移除關鍵詞輸入模式的handler。"""
        if enable:
            # 先建立 handler 對象，然後添加。
            self.keyword_handler = MessageHandler(
                partial(self.handle_keyword_input, chat_id, callback_query, callback_prompt),
                filters=pyrogram.filters.user(self.root) & pyrogram.filters.text & (
                    lambda client, m: isinstance(
                        m,
                        pyrogram.types.Message
                    ) and m.text and m.text.strip() and not m.text.startswith(
                        '/') and not m.text.startswith('http')
                )
            )
            # 使用group=-1確保在process_error_message(group=0)之前處理。
            self.add_handler(self.keyword_handler, group=-1)
            log.info(f'用戶輸入模式已開啟,Handler:"{self.keyword_handler}"。')
        else:
            if self.keyword_handler:
                self.remove_handler(self.keyword_handler, group=-1)
                log.info('用戶輸入模式已關閉,Handler已清空。')
                self.keyword_handler = None

    async def process_error_message(self, client: pyrogram.Client, message: pyrogram.types.Message) -> None:
        if self.keyword_handler:
            return
        await self.help(client, message)
        await client.send_message(
            chat_id=message.from_user.id,
            reply_parameters=ReplyParameters(message_id=message.id),
            text='⚠️⚠️⚠️未知命令⚠️⚠️⚠️\n請查看說明後重試。',
            link_preview_options=Bot.LINK_PREVIEW_OPTIONS
        )

    async def handle_keyword_input(
            self,
            chat_id: Union[str, int],
            callback_query: CallbackQuery,
            callback_prompt: Callable,
            _client: pyrogram.Client,
            message: pyrogram.types.Message
    ) -> None:
        """處理用戶輸入的關鍵詞。"""

        text: str = message.text.strip()

        if not text:
            return None

        # 以空格分隔關鍵詞。
        keywords = [kw.strip() for kw in text.split() if kw.strip()]
        for keyword in keywords:
            if keyword in self.adding_keywords:
                try:
                    await callback_query.message.edit_text(
                        text=f'🚛`{keyword}`已被添加,選擇處理方式後繼續。',
                        reply_markup=InlineKeyboardMarkup([
                            [
                                InlineKeyboardButton(
                                    BotButton.DROP,
                                    callback_data=f'{BotCallbackText.DROP_KEYWORD}_{keyword}'
                                ),
                                InlineKeyboardButton(
                                    BotButton.IGNORE,
                                    callback_data=f'{BotCallbackText.IGNORE_KEYWORD}_{keyword}'
                                )
                            ]
                        ]
                        )
                    )
                    return None
                except MessageNotModified:
                    pass
            else:
                self.download_chat_filter[chat_id]['keyword'][keyword] = True
                self.adding_keywords.append(keyword)  # 添加到正在添加的關鍵詞列表。
                try:
                    await callback_query.message.edit_text(
                        text=callback_prompt(),
                        reply_markup=KeyboardButton.keyword_filter_button(self.adding_keywords)
                    )
                except MessageNotModified:
                    pass

    @staticmethod
    async def check_download_range(
            start_id: int,
            end_id: int,
            client: pyrogram.Client,
            message: pyrogram.types.Message
    ) -> bool:
        if end_id != -1:
            if start_id > end_id:
                await client.send_message(
                    chat_id=message.from_user.id,
                    reply_parameters=ReplyParameters(message_id=message.id),
                    text='❌❌❌起始ID>結束ID❌❌❌'
                )
                return False
        if start_id == -1 or end_id == -1:
            text: str = '未知錯誤'
            if start_id == -1:
                text: str = '沒有指定起始ID'
            if end_id == -1:
                text: str = '沒有指定結束ID'
            if start_id == end_id:
                text: str = '沒有指定起始ID和結束ID'
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text=f'❌❌❌{text}❌❌❌'
            )
            return False
        return True

    async def get_download_link_from_bot(
            self,
            client: pyrogram.Client,
            message: pyrogram.types.Message,
            with_upload: Union[dict, None] = None
    ) -> Union[Dict[str, Union[set, pyrogram.types.Message]], None]:
        text: str = message.text
        if text == '/download':
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text='⚠️⚠️⚠️請提供下載連結⚠️⚠️⚠️語法:\n`/download https://t.me/x/x`',
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS
            )
        elif text.startswith('https://t.me/'):
            if text[len('https://t.me/'):].count('/') >= 1:
                try:
                    await client.delete_messages(chat_id=message.from_user.id, message_ids=message.id)
                    await self.send_message_to_bot(text=f'/download {text}', catch=True)
                except Exception as e:
                    await client.send_message(
                        chat_id=message.from_user.id,
                        reply_parameters=ReplyParameters(message_id=message.id),
                        text=f'{e}\n⬇️⬇️⬇️請使用以下命令分配下載任務⬇️⬇️⬇️\n`/download {text}`',
                        link_preview_options=Bot.LINK_PREVIEW_OPTIONS
                    )
            else:
                await client.send_message(
                    chat_id=message.from_user.id,
                    reply_parameters=ReplyParameters(message_id=message.id),
                    text=f'⬇️⬇️⬇️請使用以下命令分配下載任務⬇️⬇️⬇️\n`/download https://t.me/x/x`',
                    link_preview_options=Bot.LINK_PREVIEW_OPTIONS
                )
        elif len(text) <= 25 or text == '/download https://t.me/x/x' or text.endswith('.txt'):
            await self.help(client, message)
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text='❌❌❌連結錯誤❌❌❌\n請查看說明後重試。',
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS
            )
        else:
            link: list = text.split()
            link.remove('/download') if '/download' in link else None
            link = [_.rstrip('/') for _ in link]
            if (
                    safe_index(link, 0, '').startswith('https://t.me/') and
                    not safe_index(link, 1, 'https://t.me/').startswith('https://t.me/') and
                    len(link) == 3
            ):
                # v1.5.1 支援範圍下載。
                start_id: int = int(safe_index(link, 1, -1))
                end_id: int = int(safe_index(link, 2, -1))
                if not await self.check_download_range(
                        start_id=start_id,
                        end_id=end_id,
                        client=client,
                        message=message
                ):
                    return None
                right_link: set = set()
                invalid_link: set = set()
                for i in range(start_id, end_id + 1):
                    right_link.add(f'{link[0]}/{i}?single')  # v1.6.7 修復範圍下載連結為組時,重複下載問題。
            else:
                right_link: set = set([_ for _ in link if _.startswith('https://t.me/')])
                invalid_link: set = set([_ for _ in link if not _.startswith('https://t.me/')])
            if right_link:
                return {
                    'right_link': right_link,
                    'invalid_link': invalid_link,
                    'last_bot_message': await self.safe_process_message(
                        client=client, message=message,
                        text=self.update_text(
                            right_link=right_link,
                            invalid_link=invalid_link if invalid_link else None
                        )
                    )
                }
            else:
                return None

    async def get_download_chat_link_from_bot(
            self,
            client: pyrogram.Client,
            message: pyrogram.types.Message,
    ):
        if BotCallbackText.DOWNLOAD_CHAT_ID != 'download_chat_id':
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text='⚠️⚠️⚠️請執行或取消上一次頻道下載任務設定⚠️⚠️⚠️',
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS
            )
            return None
        text: str = message.text
        if text == '/download_chat':
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text='⚠️⚠️⚠️請提供下載連結⚠️⚠️⚠️語法:\n`/download_chat https://t.me/x/x`',
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS
            )
            return None
        command = text.split()
        if len(command) != 2:
            await self.help(client, message)
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text='❌❌❌命令語法錯誤❌❌❌\n請查看說明後重試。',
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS
            )
            return None
        chat_link = command[1]
        try:
            meta = await parse_link(client=self.user, link=chat_link)
        except ValueError:
            meta = None
        if not isinstance(meta, dict):
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text='❌❌❌找不到頻道❌❌❌',
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS
            )
            return None
        chat_id = meta.get('chat_id')
        if not chat_id:
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text='❌❌❌無法取得頻道名❌❌❌',
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS
            )
            return None
        if chat_id in self.download_chat_filter:
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text='⚠️⚠️⚠️該頻道已在下載中⚠️⚠️⚠️\n'
                     f'{chat_link}',
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS
            )
            return None
        BotCallbackText.DOWNLOAD_CHAT_ID = str(chat_id)
        self.download_chat_filter[BotCallbackText.DOWNLOAD_CHAT_ID] = {
            'date_range':
                {
                    'start_date': None,
                    'end_date': None,
                    'adjust_step': 1
                },
            'download_type':
                {
                    'video': True,
                    'photo': True,
                    'document': True,
                    'audio': True,
                    'voice': True,
                    'animation': True,
                    'video_note': True,
                    'live_photo': True
                },
            'keyword': {},
            'title': {},
            'comment': False
        }
        log.info(f'"{BotCallbackText.DOWNLOAD_CHAT_ID}"已添加至:{self.download_chat_filter}。')
        format_dtype = ','.join([_t(_) for _ in DownloadType()])
        include_comment = self.download_chat_filter[BotCallbackText.DOWNLOAD_CHAT_ID]['comment']
        comment: str = '開' if include_comment else '關'
        await client.send_message(
            chat_id=message.from_user.id,
            reply_parameters=ReplyParameters(message_id=message.id),
            text=f'💬下載頻道:`{chat_id}`\n'
                 f'⏮️目前選擇的起始日期為:未定義\n'
                 f'⏭️目前選擇的結束日期為:未定義\n'
                 f'📝目前選擇的下載類型為:{format_dtype}\n'
                 f'🔑目前匹配的關鍵詞為:未定義\n'
                 f'👥包含評論區:{comment}',
            reply_markup=KeyboardButton.download_chat_filter_button(include_comment),
            link_preview_options=Bot.LINK_PREVIEW_OPTIONS
        )

    @staticmethod
    async def safe_process_message(
            client: pyrogram.Client,
            message: pyrogram.types.Message,
            text: list, last_message_id: int = -1,
            reply_markup: Union[pyrogram.types.InlineKeyboardMarkup, None] = None
    ) -> pyrogram.types.Message:
        if len(text) == 1 and last_message_id != -1:
            last_bot_message = await client.edit_message_text(
                chat_id=message.from_user.id,
                message_id=last_message_id,
                text=text[0],
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS,
                reply_markup=reply_markup
            )
            return last_bot_message

        last_bot_messages: list = []
        for t in text:
            last_bot_message: pyrogram.types.Message = await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text=t, link_preview_options=Bot.LINK_PREVIEW_OPTIONS
            )
            if last_bot_message not in last_bot_messages:
                last_bot_messages.append(last_bot_message)
        return last_bot_messages[-1]

    async def help(
            self,
            client: Union[pyrogram.Client, None] = None,
            message: Union[pyrogram.types.Message, None] = None
    ) -> Union[None, dict]:  # client與message都為None時,返回keyboard與text。
        web = getattr(self, 'web', None)  # 網頁面板實例,用於展示認證資訊。
        web_auth: str = ''
        if web is not None:
            web_auth = (
                f'🌐 Web設定:\n'
                f'🔌 連接埠: {web.port}\n'
                f'👤 帳號: ||{web.username}||\n'
                f'🔑 密碼: ||{web.password}||\n'
                f'🔗 連結: {web.protocol}://{web.LOCAL_IP}:{web.port}\n\n'
            )
        config: dict = rc.cached_config()
        update_version: str = check_update(  # 遠端版本更高時返回該版本號,用於提示可更新。
            remote_version=config.get('version', __version__),
            local_version=__version__
        )
        version: str = f'{VERSION_SEMVER}({update_version}⬆)' if update_version else VERSION_SEMVER
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        BotButton.GITHUB,
                        url=config.get('github', rc.DEFAULT_GITHUB) + '/releases'
                    ),
                    InlineKeyboardButton(
                        BotButton.SUBSCRIBE_CHANNEL,
                        url=config.get('subscribe_channel', rc.DEFAULT_SUBSCRIBE_CHANNEL)
                    )
                ],
                [
                    InlineKeyboardButton(
                        BotButton.VIDEO_TUTORIAL,
                        url=config.get('video_tutorial', rc.DEFAULT_VIDEO_TUTORIAL)
                    )
                ],
                [
                    InlineKeyboardButton(
                        BotButton.SETTING,
                        callback_data=BotCallbackText.SETTING
                    )
                ]
            ]
        )

        text = (
            f'`\n💎 {SOFTWARE_SHORT_NAME} {version} 💎\n'
            f'©️ {__copyright__.replace(" <https://github.com/Gentlesprite>", ".")}\n'
            f'📖 Licensed under the terms of the {__license__}.`\n\n'
            f'🎮️ 可用命令:\n'
            f'🛎️ {BotCommandText.with_description(BotCommandText.HELP)}\n'
            f'📁 {BotCommandText.with_description(BotCommandText.DOWNLOAD)}\n'
            f'📝 {BotCommandText.with_description(BotCommandText.TABLE)}\n'
            f'↗️ {BotCommandText.with_description(BotCommandText.FORWARD)}\n'
            f'❌ {BotCommandText.with_description(BotCommandText.EXIT)}\n'
            f'🕵️ {BotCommandText.with_description(BotCommandText.LISTEN_DOWNLOAD)}\n'
            f'📲 {BotCommandText.with_description(BotCommandText.LISTEN_FORWARD)}\n'
            f'🔍 {BotCommandText.with_description(BotCommandText.LISTEN_INFO)}\n'
            f'📤 {BotCommandText.with_description(BotCommandText.UPLOAD)}\n'
            f'🌳 {BotCommandText.with_description(BotCommandText.UPLOAD_R)}\n'
            f'💬 {BotCommandText.with_description(BotCommandText.DOWNLOAD_CHAT)}\n\n'
            f'{web_auth}'
            f'✨ 其他功能:\n'
            f'📨 轉發`影片`、`圖片`、`音訊`、`語音`、`GIF`、`檔案`、`影片筆記`、`實況圖片`類型的訊息給我,即可建立下載任務。\n'
        )
        if not all([client, message]):
            return {
                'keyboard': keyboard,
                'text': text
            }
        await client.send_message(
            chat_id=message.from_user.id,
            text=text,
            link_preview_options=Bot.LINK_PREVIEW_OPTIONS,
            reply_markup=keyboard
        )

    async def start(
            self,
            client: pyrogram.Client,
            message: pyrogram.types.Message
    ):
        await self.help(client, message)

    @staticmethod
    async def callback_data(client: pyrogram.Client, callback_query: CallbackQuery) -> Union[str, None]:
        await callback_query.answer()
        data = callback_query.data
        if not data:
            return None
        if isinstance(data, str):
            return data

    @staticmethod
    async def table(
            client: Union[pyrogram.Client, None] = None,
            message: Union[pyrogram.types.Message, None] = None
    ) -> Union[None, dict]:
        keyboard = InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        BotButton.LINK_TABLE,
                        callback_data=BotCallbackText.LINK_TABLE
                    ),
                    InlineKeyboardButton(
                        BotButton.COUNT_TABLE,
                        callback_data=BotCallbackText.COUNT_TABLE
                    )
                ],
                [
                    InlineKeyboardButton(
                        BotButton.UPLOAD_TABLE,
                        callback_data=BotCallbackText.UPLOAD_TABLE
                    )
                ],
                [
                    InlineKeyboardButton(
                        BotButton.HELP_PAGE,
                        callback_data=BotCallbackText.BACK_HELP
                    )
                ]
            ]
        )
        text: str = '🧐🧐🧐請選擇輸出「統計表」的類型:'
        if not all([client, message]):
            return {
                'keyboard': keyboard,
                'text': text
            }
        await client.send_message(
            chat_id=message.from_user.id,
            text=text,
            link_preview_options=Bot.LINK_PREVIEW_OPTIONS,
            reply_markup=keyboard
        )

    async def get_forward_link_from_bot(
            self,
            client: pyrogram.Client,
            message: pyrogram.types.Message
    ) -> Union[Dict[str, Union[list, str]], None]:

        text: str = message.text
        args: list = text.split(maxsplit=5)
        if text == '/forward':
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text='❌❌❌命令語法無效❌❌❌\n'
                     '⬇️⬇️⬇️語法如下⬇️⬇️⬇️\n'
                     '`/forward 原始頻道 目標頻道 起始ID 結束ID`\n'
                     '⬇️⬇️⬇️請使用⬇️⬇️⬇️\n'
                     '`/forward https://t.me/A https://t.me/B 1 100`\n'
            )
            return None
        try:
            start_id: int = int(safe_index(args, 3, -1))
            end_id: int = int(safe_index(args, 4, -1))
            if not await self.check_download_range(
                    start_id=start_id,
                    end_id=end_id,
                    client=client,
                    message=message):
                return None
        except Exception as e:
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text=f'❌❌❌命令錯誤❌❌❌\n{e}\n請使用`/forward https://t.me/A https://t.me/B 1 100`'
            )
            return None
        return {
            'origin_link': args[1],
            'target_link': args[2],
            'message_range': [start_id, end_id]
        }

    async def get_upload_link_from_bot(
            self,
            client: pyrogram.Client,
            message: pyrogram.types.Message,
            delete: bool = False,
            save_directory: str = None,
            recursion: bool = False,
            valid_link_cache: dict = None
    ):
        if not recursion:
            valid_link_cache = {}

        text: str = message.text
        if text == '/upload' or text == '/upload_r':
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text='⚠️⚠️⚠️請提供參數⚠️⚠️⚠️語法:\n`/upload 本機檔案 目標頻道`或`/upload_r 本機資料夾 目標頻道`',
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS
            )
            return None

        if text.startswith('/upload '):
            remaining_text = text[len('/upload '):].strip()
            command = '/upload'
        elif text.startswith('/upload_r '):
            remaining_text = text[len('/upload_r '):].strip()
            command = '/upload_r'
        else:
            return None

        parts = remaining_text.rsplit(maxsplit=1)

        if len(parts) == 2:
            file_path = parts[0]  # 檔案名稱部分（可能包含空格）。
            target_link = parts[1]  # URL部分。
            if not recursion:
                if target_link not in valid_link_cache:
                    valid_link_cache[target_link] = await get_valid_chat_id(
                        link=target_link,
                        user_client=self.user,
                        bot_client=self.bot,
                        bot_message=self.last_message,
                        error_msg=f'⬇️⬇️⬇️目標頻道不存在⬇️⬇️⬇️\n{target_link}'
                    )
                if not valid_link_cache[target_link]:
                    return None
            if os.path.isdir(file_path):
                upload_folder = []
                if command == '/upload_r':
                    upload_files = [os.path.join(root, filename) for root, dirs, files in os.walk(file_path) for
                                    filename in files]
                else:
                    upload_files = safe_scan_directory_file(file_path)
                for file_name in upload_files:
                    new_message = copy.copy(message)
                    new_message.text = f'/upload {os.path.join(file_path, file_name)} {target_link}'
                    upload_folder.append(
                        self.get_upload_link_from_bot(
                            client=client,
                            message=new_message,
                            delete=delete,
                            save_directory=save_directory,
                            recursion=True,
                            valid_link_cache=valid_link_cache
                        )
                    )
                if upload_folder:
                    await client.send_message(
                        chat_id=message.from_user.id,
                        reply_parameters=ReplyParameters(message_id=message.id),
                        text=f'📤📤📤上載任務已建立,請耐心等待📤📤📤\n`{file_path}`',
                        link_preview_options=Bot.LINK_PREVIEW_OPTIONS
                    )
                    await asyncio.gather(*upload_folder)
                else:
                    await client.send_message(
                        chat_id=message.from_user.id,
                        reply_parameters=ReplyParameters(message_id=message.id),
                        text=f'⚠️⚠️⚠️資料夾為空⚠️⚠️⚠️\n`{file_path}`',
                        link_preview_options=Bot.LINK_PREVIEW_OPTIONS
                    )
                return None
            if not os.path.isfile(file_path):
                log.error(f'上載出錯,{_t(KeyWord.REASON)}:"{file_path}"不存在。')
                await client.send_message(
                    chat_id=message.from_user.id,
                    reply_parameters=ReplyParameters(message_id=message.id),
                    text=f'⚠️⚠️⚠️上載檔案不存在⚠️⚠️⚠️\n`{file_path}`',
                    link_preview_options=Bot.LINK_PREVIEW_OPTIONS
                )
                return None
            file_size = os.path.getsize(file_path)
            if file_size == 0:
                await client.send_message(
                    chat_id=message.from_user.id,
                    reply_parameters=ReplyParameters(message_id=message.id),
                    text=f'⚠️⚠️⚠️上載檔案大小為0⚠️⚠️⚠️\n`{file_path}`',
                    link_preview_options=Bot.LINK_PREVIEW_OPTIONS
                )

            if not is_allow_upload(file_size=file_size, is_premium=self.user.me.is_premium):
                format_file_size: str = MetaData.suitable_units_display(file_size, unit='MiB', mebibyte=True)
                await client.send_message(
                    chat_id=message.from_user.id,
                    reply_parameters=ReplyParameters(message_id=message.id),
                    text=f'⚠️⚠️⚠️上載大小超過限制({format_file_size})⚠️⚠️⚠️\n'
                         f'`{file_path}`\n'
                         f'(普通用戶2000MiB,會員用戶4000MiB)',
                    link_preview_options=Bot.LINK_PREVIEW_OPTIONS
                )
            if not recursion:
                await client.send_message(
                    chat_id=message.from_user.id,
                    reply_parameters=ReplyParameters(message_id=message.id),
                    text=f'📤📤📤上載任務已建立,請耐心等待📤📤📤\n`{file_path}`',
                    link_preview_options=Bot.LINK_PREVIEW_OPTIONS
                )
            log.info(f'上載檔案:"{file_path}",上載頻道:"{target_link}"。')
            if target_link.startswith('https://t.me/') or target_link in ('me', 'self'):  # 驗證目標連結格式。
                return {
                    'target_link': target_link,
                    'valid_link_cache': valid_link_cache,
                    'upload_task': UploadTask(
                        chat_id=None,
                        file_path=file_path,
                        file_id=self.user.rnd_id(),
                        file_size=os.path.getsize(file_path),
                        file_part=[],
                        status=UploadStatus.PENDING
                    )
                }
        if not recursion:
            await self.help(client, message)
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                text='❌❌❌命令錯誤❌❌❌\n請查看說明後重試。',
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS
            )
            return None

    async def exit(
            self,
            client: pyrogram.Client,
            message: pyrogram.types.Message
    ) -> None:
        last_message = await client.send_message(
            chat_id=message.from_user.id,
            text='🚧已收到退出命令。',
            reply_parameters=ReplyParameters(message_id=message.id),
            link_preview_options=Bot.LINK_PREVIEW_OPTIONS
        )
        self.is_bot_running = False
        await self.safe_edit_message(
            client=client,
            message=message,
            last_message_id=last_message.id,
            text='✅退出成功。'
        )
        raise SystemExit(0)

    async def on_listen(
            self,
            client: pyrogram.Client,
            message: pyrogram.types.Message
    ) -> Union[Dict[str, list], None]:
        text: str = message.text
        args: list = text.split()
        command: str = args[0]
        links: list = args[1:]
        if text.startswith('/listen_download'):
            if len(args) == 1:
                await client.send_message(
                    chat_id=message.from_user.id,
                    reply_parameters=ReplyParameters(message_id=message.id),
                    text='❌❌❌命令語法錯誤❌❌❌\n'
                         '⬇️⬇️⬇️語法如下⬇️⬇️⬇️\n'
                         f'`/listen_download 監聽頻道1 監聽頻道2 監聽頻道n`\n'
                         '⬇️⬇️⬇️請使用⬇️⬇️⬇️\n'
                         f'`/listen_download https://t.me/A https://t.me/B https://t.me/n`\n'
                )
                return None
            last_message: Union[pyrogram.types.Message, str, None] = None
            invalid_links: list = []
            for link in links:
                if not link.startswith('https://t.me/'):
                    invalid_links.append(link)
                    if not last_message:
                        last_message = await client.send_message(
                            chat_id=message.from_user.id,
                            reply_parameters=ReplyParameters(message_id=message.id),
                            text=BotMessage.INVALID
                        )
                    last_message: Union[pyrogram.types.Message, str, None] = await self.safe_edit_message(
                        client=client,
                        message=message,
                        last_message_id=last_message.id,
                        text=safe_message(f'{last_message.text}\n{link}')
                    )
                for meta in self.listen_forward_chat:
                    listen_link, target_link = meta.split()
                    if listen_link == link:
                        invalid_links.append(listen_link)
                        if not last_message:
                            last_message = await client.send_message(
                                chat_id=message.from_user.id,
                                reply_parameters=ReplyParameters(message_id=message.id),
                                text='❌同一頻道不能同時存在兩個監聽\n(您已使用`/listen_forward`建立了以下連結的監聽轉發)'
                            )
                        last_message: Union[pyrogram.types.Message, str, None] = await self.safe_edit_message(
                            client=client,
                            message=message,
                            last_message_id=last_message.id,
                            text=safe_message(f'{last_message.text}\n{listen_link}')
                        )

            if invalid_links:
                for ivl in invalid_links:
                    if ivl in links:
                        links.remove(ivl)
                if not links:
                    await self.safe_edit_message(
                        client=client,
                        message=message,
                        last_message_id=last_message.id,
                        text='❌❌❌沒有找到有效的連結❌❌❌'
                    )
                    return None
            links: list = list(set(links))

        elif text.startswith('/listen_forward'):
            e: str = ''
            len_args: int = len(args)
            if len_args != 3:
                if len_args == 1:
                    e: str = '命令缺少監聽頻道與轉發頻道'
                elif len_args == 2:
                    e: str = '命令缺少轉發頻道'
                await client.send_message(
                    chat_id=message.from_user.id,
                    reply_parameters=ReplyParameters(message_id=message.id),
                    text=f'❌❌❌{e}❌❌❌\n'
                         '⬇️⬇️⬇️語法如下⬇️⬇️⬇️\n'
                         f'`/listen_forward 監聽頻道 轉發頻道`\n'
                         '⬇️⬇️⬇️請使用⬇️⬇️⬇️\n'
                         f'`/listen_forward https://t.me/A https://t.me/B`\n'
                )
                return None
            listen_link: str = args[1]
            target_link: str = args[2]
            if listen_link in self.listen_download_chat:
                await client.send_message(
                    chat_id=message.from_user.id,
                    reply_parameters=ReplyParameters(message_id=message.id),
                    text='❌同一頻道不能同時存在兩個監聽\n(您已使用`/listen_download`建立了以下連結的監聽下載)\n'
                         f'{listen_link}'
                )
                return None
            if not listen_link.startswith('https://t.me/'):
                e = '監聽頻道連結錯誤'
            if not target_link.startswith('https://t.me/'):
                e = '轉發頻道連結錯誤'
            if e != '':
                await client.send_message(
                    chat_id=message.from_user.id,
                    reply_parameters=ReplyParameters(message_id=message.id),
                    text=f'❌❌❌{e}❌❌❌\n'
                         '⬇️⬇️⬇️語法如下⬇️⬇️⬇️\n'
                         f'`/listen_forward 監聽頻道 轉發頻道`\n'
                         '⬇️⬇️⬇️請使用⬇️⬇️⬇️\n'
                         f'`/listen_forward https://t.me/A https://t.me/B`\n'
                )
                return None
        return {'command': command, 'links': links}

    @staticmethod
    async def listen_download(
            client: pyrogram.Client,
            message: pyrogram.types.Message
    ):
        pass

    @staticmethod
    async def listen_forward(
            client: pyrogram.Client,
            message: pyrogram.types.Message
    ):
        pass

    async def cancel_listen(
            self,
            client: pyrogram.Client,
            message: pyrogram.types.Message,
            link: str,
            command: str,
            from_web: bool = False
    ):
        pass

    async def listen_info(
            self,
            client: pyrogram.Client,
            message: pyrogram.types.Message
    ):
        async def __listen_info(_listen_chat: dict, _text: str):
            last_message = await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS,
                text=_text
            )
            for link in _listen_chat:
                args: list = link.split()
                len_args: int = len(args)
                if len_args == 1:
                    last_message = await self.safe_edit_message(
                        client=client,
                        message=message,
                        last_message_id=last_message.id,
                        text=safe_message(f'{last_message.text}\n{link}')
                    )
                elif len_args == 2:
                    forward_emoji = ' ➡️ '
                    last_message = await self.safe_edit_message(
                        client=client,
                        message=message,
                        last_message_id=last_message.id,
                        text=safe_message(f'{last_message.text}\n{args[0]}{forward_emoji}{args[1]}')
                    )

        if not self.listen_forward_chat and not self.listen_download_chat:
            await client.send_message(
                chat_id=message.from_user.id,
                reply_parameters=ReplyParameters(message_id=message.id),
                link_preview_options=Bot.LINK_PREVIEW_OPTIONS,
                text='😲目前沒有正在監聽的頻道。'
            )
        else:
            if self.listen_download_chat:
                await __listen_info(self.listen_download_chat, '🕵️以下連結為已建立的`監聽下載`頻道:\n')
            if self.listen_forward_chat:
                await __listen_info(self.listen_forward_chat, '📲以下連結為已建立的`監聽轉發`頻道:\n')

    async def handle_forwarded_media(
            self,
            user_client: pyrogram.Client,
            user_message: pyrogram.types.Message
    ):
        pass

    async def done_notice(
            self,
            text
    ):
        if self.gc.get_config(BotCallbackText.NOTICE):
            if all([self.last_client, self.last_message]):
                while True:
                    try:
                        await self.last_client.send_message(
                            chat_id=self.last_message.from_user.id,
                            text=f'{BotMessage.NOTICE}{text}',
                            link_preview_options=Bot.LINK_PREVIEW_OPTIONS
                        )
                        break
                    except (FloodWait, FloodPremiumWait) as e:
                        amount = e.value
                        console.log(
                            f'[{self.bot.name}]發送訊息請求頻繁,要求等待{amount}秒後繼續執行。',
                            style='#FF4689'
                        )
                        await asyncio.sleep(amount)
                    except Exception as e:
                        log.error(f'無法發送通知,{_t(KeyWord.REASON)}:"{e}"')

    async def start_bot(
            self,
            application,
            user_client_obj: pyrogram.Client,
            bot_client_obj: pyrogram.Client,
    ) -> str:
        """啟動機械人。"""
        try:
            self.application = application
            self.bot = bot_client_obj
            self.user = user_client_obj
            root = await self.user.get_me()
            self.root.clear()
            self.root.append(root.id)
            await bot_client_obj.start()
            await self.bot.set_bot_commands(self.COMMANDS)
            bot = await self.bot.get_me()
            bot_username = getattr(bot, 'username', None)

            self.bot.add_handler(
                MessageHandler(
                    self.start,
                    filters=pyrogram.filters.command(['start']) & pyrogram.filters.user(self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.help,
                    filters=pyrogram.filters.command(['help']) & pyrogram.filters.user(self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.get_download_link_from_bot,
                    filters=pyrogram.filters.command(['download']) & pyrogram.filters.user(self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.get_download_chat_link_from_bot,
                    filters=pyrogram.filters.command(['download_chat']) & pyrogram.filters.user(self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.get_upload_link_from_bot,
                    filters=pyrogram.filters.command(['upload']) & pyrogram.filters.user(self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.get_upload_link_from_bot,
                    filters=pyrogram.filters.command(['upload_r']) & pyrogram.filters.user(self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.table,
                    filters=pyrogram.filters.command(['table']) & pyrogram.filters.user(self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.get_forward_link_from_bot,
                    filters=pyrogram.filters.command(['forward']) & pyrogram.filters.user(self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.exit,
                    filters=pyrogram.filters.command(['exit']) & pyrogram.filters.user(self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.on_listen,
                    filters=pyrogram.filters.command(['listen_download', 'listen_forward']) & pyrogram.filters.user(
                        self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.listen_info,
                    filters=pyrogram.filters.command(['listen_info']) & pyrogram.filters.user(self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.get_download_link_from_bot,
                    filters=pyrogram.filters.regex(r'^https://t.me.*') & pyrogram.filters.user(self.root)
                )
            )
            if self.forwarded_media_handler is not None:
                self.user.remove_handler(self.forwarded_media_handler)
            self.forwarded_media_handler = MessageHandler(
                self.handle_forwarded_media,
                filters=pyrogram.filters.user(self.root) & pyrogram.filters.forwarded & pyrogram.filters.chat(
                    bot_username) & (
                                pyrogram.filters.video
                                | pyrogram.filters.photo
                                | pyrogram.filters.audio
                                | pyrogram.filters.voice
                                | pyrogram.filters.animation
                                | pyrogram.filters.document
                                | pyrogram.filters.video_note
                        )
            )
            self.user.add_handler(self.forwarded_media_handler)
            self.bot.add_handler(
                CallbackQueryHandler(
                    self.callback_data,
                    filters=pyrogram.filters.user(self.root)
                )
            )
            self.bot.add_handler(
                MessageHandler(
                    self.process_error_message,
                    filters=pyrogram.filters.user(self.root) & ~(
                            pyrogram.filters.video
                            | pyrogram.filters.photo
                            | pyrogram.filters.audio
                            | pyrogram.filters.voice
                            | pyrogram.filters.animation
                            | pyrogram.filters.document
                            | pyrogram.filters.video_note
                    )
                )
            )
            self.is_bot_running: bool = True
            await self.send_message_to_bot(text='/start')
            return f'🤖「機械人」啟動成功 ({BotButton.OPEN_NOTICE if self.gc.config.get(BotCallbackText.NOTICE) else BotButton.CLOSE_NOTICE})。'
        except AccessTokenInvalid as e:
            self.is_bot_running: bool = False
            return f'🤖「機械人」啟動失敗,「bot_token」錯誤,{_t(KeyWord.REASON)}:"{e}"'
        except Exception as e:
            self.is_bot_running: bool = False
            return f'🤖「機械人」啟動失敗,{_t(KeyWord.REASON)}:"{e}"'

    async def send_message_to_bot(self, text: str, catch: bool = False):
        try:
            bot_username = getattr(await self.bot.get_me(), 'username', None)
            if bot_username:
                return await self.user.send_message(
                    chat_id=bot_username,
                    text=text,
                    link_preview_options=Bot.LINK_PREVIEW_OPTIONS
                )
        except Exception as e:
            if catch:
                raise Exception(str(e))
            else:
                return e

    @staticmethod
    def update_text(
            right_link: set,
            invalid_link: set
    ) -> list:
        n = '\n'
        right_msg = f'{BotMessage.RIGHT}{n.join(sorted(right_link))}' if right_link else ''
        invalid_msg = f'{BotMessage.INVALID}{n.join(sorted(invalid_link))}{n}(具體原因請前往終端機查看報錯資訊)' if invalid_link else ''
        return safe_message(f'{right_msg}{n}{invalid_msg}')

    async def safe_edit_message(
            self, client: pyrogram.Client,
            message: pyrogram.types.Message,
            last_message_id: int,
            text: Union[str, List[str]],
            reply_markup: Union[pyrogram.types.InlineKeyboardMarkup, None] = None
    ) -> Union[pyrogram.types.Message, None]:
        while True:
            try:
                if isinstance(text, list):
                    last_message: pyrogram.types.Message = await self.safe_process_message(
                        client=client,
                        message=message,
                        last_message_id=last_message_id,
                        text=text,
                        reply_markup=reply_markup
                    )
                    return last_message
                elif isinstance(text, str):
                    await client.edit_message_text(
                        chat_id=message.from_user.id,
                        message_id=last_message_id,
                        text=text,
                        link_preview_options=Bot.LINK_PREVIEW_OPTIONS,
                        reply_markup=reply_markup
                    )
                    return None
            except MessageNotModified:
                return None
            except (FloodWait, FloodPremiumWait) as e:
                amount = e.value
                console.log(
                    f'[{self.bot.name}]編輯訊息請求頻繁,要求等待{amount}秒後繼續執行。',
                    style='#FF4689'
                )
                await asyncio.sleep(amount)
            except Exception:
                raise

    async def send_rich_table(self, message: pyrogram.types.Message, chunks: list) -> None:
        """通過機械人將統計表的 Markdown 分片以富文字訊息發送給用戶。

        ``chunks`` 為 Markdown 字串列表:首片編輯原訊息(以便鍵盤掛接),
        其餘分片作為新訊息發送,規避單條富文字訊息的長度上限。
        """
        if self.bot is None or not chunks:
            return None
        chat_id: int = message.chat.id
        first, *rest = chunks
        try:
            await self.bot.edit_message_text(
                chat_id=chat_id,
                message_id=message.id,
                rich_message=pyrogram.types.InputRichMessage(markdown=first)
            )
        except Exception as e:
            log.error(f'通過機械人發送統計表(首片)失敗,{_t(KeyWord.REASON)}:"{e}"')
        for index, chunk in enumerate(rest, start=2):
            try:
                await self.bot.send_rich_message(
                    chat_id=chat_id,
                    rich_message=pyrogram.types.InputRichMessage(markdown=chunk)
                )
            except Exception as e:
                log.error(f'通過機械人發送統計表(第{index}片)失敗,{_t(KeyWord.REASON)}:"{e}"')


class KeyboardButton:
    def __init__(self, callback_query: pyrogram.types.CallbackQuery):
        self.callback_query = callback_query

    async def choice_export_table_button(
            self,
            choice: Union[BotCallbackText, str]
    ) -> None:
        export_callback_data: str = ''
        if choice == BotCallbackText.EXPORT_LINK_TABLE:
            export_callback_data = BotCallbackText.EXPORT_LINK_TABLE
        elif choice == BotCallbackText.EXPORT_COUNT_TABLE:
            export_callback_data = BotCallbackText.EXPORT_COUNT_TABLE
        elif choice == BotCallbackText.EXPORT_UPLOAD_TABLE:
            export_callback_data = BotCallbackText.EXPORT_UPLOAD_TABLE
        try:
            await self.callback_query.message.edit_reply_markup(InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            text=BotButton.EXPORT_TABLE,
                            callback_data=export_callback_data
                        ),
                        InlineKeyboardButton(
                            text=BotButton.RESELECT,
                            callback_data=BotCallbackText.BACK_TABLE
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=BotButton.HELP_PAGE,
                            callback_data=BotCallbackText.BACK_HELP
                        )
                    ]
                ]
            )
            )
        except MessageNotModified:
            pass

    async def toggle_setting_button(
            self,
            global_config: dict,
            user_config: dict
    ) -> None:
        try:
            await self.callback_query.message.edit_reply_markup(
                InlineKeyboardMarkup([
                    [
                        InlineKeyboardButton(
                            text=BotButton.CLOSE_NOTICE if global_config.get(
                                BotCallbackText.NOTICE) else BotButton.OPEN_NOTICE,
                            callback_data=BotCallbackText.NOTICE
                        ),
                        InlineKeyboardButton(
                            text=BotButton.EXPORT_TABLE,
                            callback_data=BotCallbackText.EXPORT_TABLE
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=BotButton.CLOSE_EXIT_SHUTDOWN if user_config.get(
                                'is_shutdown') else BotButton.OPEN_EXIT_SHUTDOWN,
                            callback_data=BotCallbackText.SHUTDOWN
                        ),
                        InlineKeyboardButton(
                            text=BotButton.FORWARD_SETTING,
                            callback_data=BotCallbackText.FORWARD_SETTING
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=BotButton.DOWNLOAD_SETTING,
                            callback_data=BotCallbackText.DOWNLOAD_SETTING
                        ),
                        InlineKeyboardButton(
                            text=BotButton.UPLOAD_SETTING,
                            callback_data=BotCallbackText.UPLOAD_SETTING
                        )
                    ],
                    [
                        InlineKeyboardButton(
                            text=BotButton.HELP_PAGE,
                            callback_data=BotCallbackText.BACK_HELP
                        )
                    ]
                ])
            )
        except MessageNotModified:
            pass
        except Exception as e:
            await self.callback_query.message.reply_text('切換按鈕狀態失敗\n(具體原因請前往終端機查看報錯資訊)')
            log.error(f'切換按鈕狀態失敗,{_t(KeyWord.REASON)}:"{e}"')

    async def toggle_upload_setting_button(
            self,
            global_config: dict
    ):
        try:
            await self.callback_query.message.edit_reply_markup(
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=BotButton.CLOSE_UPLOAD_DOWNLOAD if global_config.get('upload').get(
                                    'download_upload') else BotButton.OPEN_UPLOAD_DOWNLOAD,
                                callback_data=BotCallbackText.UPLOAD_DOWNLOAD
                            ),
                            InlineKeyboardButton(
                                text=BotButton.CLOSE_UPLOAD_DOWNLOAD_DELETE if global_config.get('upload').get(
                                    'delete') else BotButton.OPEN_UPLOAD_DOWNLOAD_DELETE,
                                callback_data=BotCallbackText.UPLOAD_DOWNLOAD_DELETE
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.RETURN,
                                callback_data=BotCallbackText.SETTING
                            )
                        ]
                    ]
                )
            )
        except MessageNotModified:
            pass

    async def toggle_download_setting_button(
            self,
            user_config: dict
    ):
        try:
            await self.callback_query.message.edit_reply_markup(
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=BotButton.VIDEO_ON if DownloadType.VIDEO in user_config.get(
                                    'download_type') else BotButton.VIDEO_OFF,
                                callback_data=BotCallbackText.TOGGLE_DOWNLOAD_VIDEO
                            ),
                            InlineKeyboardButton(
                                text=BotButton.PHOTO_ON if DownloadType.PHOTO in user_config.get(
                                    'download_type') else BotButton.PHOTO_OFF,
                                callback_data=BotCallbackText.TOGGLE_DOWNLOAD_PHOTO
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.AUDIO_ON if DownloadType.AUDIO in user_config.get(
                                    'download_type') else BotButton.AUDIO_OFF,
                                callback_data=BotCallbackText.TOGGLE_DOWNLOAD_AUDIO
                            ),
                            InlineKeyboardButton(
                                text=BotButton.VOICE_ON if DownloadType.VOICE in user_config.get(
                                    'download_type') else BotButton.VOICE_OFF,
                                callback_data=BotCallbackText.TOGGLE_DOWNLOAD_VOICE
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.ANIMATION_ON if DownloadType.ANIMATION in user_config.get(
                                    'download_type') else BotButton.ANIMATION_OFF,
                                callback_data=BotCallbackText.TOGGLE_DOWNLOAD_ANIMATION
                            ),
                            InlineKeyboardButton(
                                text=BotButton.DOCUMENT_ON if DownloadType.DOCUMENT in user_config.get(
                                    'download_type') else BotButton.DOCUMENT_OFF,
                                callback_data=BotCallbackText.TOGGLE_DOWNLOAD_DOCUMENT
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.VIDEO_NOTE_ON if DownloadType.VIDEO_NOTE in user_config.get(
                                    'download_type') else BotButton.VIDEO_NOTE_OFF,
                                callback_data=BotCallbackText.TOGGLE_DOWNLOAD_VIDEO_NOTE
                            ),
                            InlineKeyboardButton(
                                text=BotButton.LIVE_PHOTO_ON if DownloadType.LIVE_PHOTO in user_config.get(
                                    'download_type') else BotButton.LIVE_PHOTO_OFF,
                                callback_data=BotCallbackText.TOGGLE_DOWNLOAD_LIVE_PHOTO
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.RETURN,
                                callback_data=BotCallbackText.SETTING
                            )
                        ]
                    ]
                )
            )
        except MessageNotModified:
            pass

    async def toggle_forward_setting_button(
            self,
            global_config: dict
    ):
        try:
            await self.callback_query.message.edit_reply_markup(
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=BotButton.VIDEO_ON if global_config.get('forward_type').get(
                                    'video') else BotButton.VIDEO_OFF,
                                callback_data=BotCallbackText.TOGGLE_FORWARD_VIDEO
                            ),
                            InlineKeyboardButton(
                                text=BotButton.PHOTO_ON if global_config.get('forward_type').get(
                                    'photo') else BotButton.PHOTO_OFF,
                                callback_data=BotCallbackText.TOGGLE_FORWARD_PHOTO
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.AUDIO_ON if global_config.get('forward_type').get(
                                    'audio') else BotButton.AUDIO_OFF,
                                callback_data=BotCallbackText.TOGGLE_FORWARD_AUDIO
                            ),
                            InlineKeyboardButton(
                                text=BotButton.VOICE_ON if global_config.get('forward_type').get(
                                    'voice') else BotButton.VOICE_OFF,
                                callback_data=BotCallbackText.TOGGLE_FORWARD_VOICE
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.ANIMATION_ON if global_config.get('forward_type').get(
                                    'animation') else BotButton.ANIMATION_OFF,
                                callback_data=BotCallbackText.TOGGLE_FORWARD_ANIMATION
                            ),
                            InlineKeyboardButton(
                                text=BotButton.DOCUMENT_ON if global_config.get('forward_type').get(
                                    'document') else BotButton.DOCUMENT_OFF,
                                callback_data=BotCallbackText.TOGGLE_FORWARD_DOCUMENT
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.TEXT_ON if global_config.get('forward_type').get(
                                    'text') else BotButton.TEXT_OFF,
                                callback_data=BotCallbackText.TOGGLE_FORWARD_TEXT
                            ),
                            InlineKeyboardButton(
                                text=BotButton.VIDEO_NOTE_ON if global_config.get('forward_type').get(
                                    'video_note') else BotButton.VIDEO_NOTE_OFF,
                                callback_data=BotCallbackText.TOGGLE_FORWARD_VIDEO_NOTE
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.LIVE_PHOTO_ON if global_config.get('forward_type').get(
                                    'live_photo') else BotButton.LIVE_PHOTO_OFF,
                                callback_data=BotCallbackText.TOGGLE_FORWARD_LIVE_PHOTO
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.RETURN,
                                callback_data=BotCallbackText.SETTING
                            )
                        ]
                    ]
                )
            )
        except MessageNotModified:
            pass

    @staticmethod
    def toggle_download_chat_type_filter_button(
            download_chat_filter: dict
    ):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=BotButton.VIDEO_ON if
                        download_chat_filter[BotCallbackText.DOWNLOAD_CHAT_ID]['download_type'][
                            DownloadType.VIDEO] else BotButton.VIDEO_OFF,
                        callback_data=BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VIDEO
                    ),
                    InlineKeyboardButton(
                        text=BotButton.PHOTO_ON if
                        download_chat_filter[BotCallbackText.DOWNLOAD_CHAT_ID]['download_type'][
                            DownloadType.PHOTO] else BotButton.PHOTO_OFF,
                        callback_data=BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_PHOTO
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=BotButton.AUDIO_ON if
                        download_chat_filter[BotCallbackText.DOWNLOAD_CHAT_ID]['download_type'][
                            DownloadType.AUDIO] else BotButton.AUDIO_OFF,
                        callback_data=BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_AUDIO
                    ),
                    InlineKeyboardButton(
                        text=BotButton.VOICE_ON if
                        download_chat_filter[BotCallbackText.DOWNLOAD_CHAT_ID]['download_type'][
                            DownloadType.VOICE] else BotButton.VOICE_OFF,
                        callback_data=BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VOICE
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=BotButton.ANIMATION_ON if
                        download_chat_filter[BotCallbackText.DOWNLOAD_CHAT_ID]['download_type'][
                            DownloadType.ANIMATION] else BotButton.ANIMATION_OFF,
                        callback_data=BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_ANIMATION
                    ),
                    InlineKeyboardButton(
                        text=BotButton.DOCUMENT_ON if
                        download_chat_filter[BotCallbackText.DOWNLOAD_CHAT_ID]['download_type'][
                            DownloadType.DOCUMENT] else BotButton.DOCUMENT_OFF,
                        callback_data=BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_DOCUMENT
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=BotButton.VIDEO_NOTE_ON if
                        download_chat_filter[BotCallbackText.DOWNLOAD_CHAT_ID]['download_type'][
                            DownloadType.VIDEO_NOTE] else BotButton.VIDEO_NOTE_OFF,
                        callback_data=BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VIDEO_NOTE
                    ),
                    InlineKeyboardButton(
                        text=BotButton.LIVE_PHOTO_ON if
                        download_chat_filter[BotCallbackText.DOWNLOAD_CHAT_ID]['download_type'][
                            DownloadType.LIVE_PHOTO] else BotButton.LIVE_PHOTO_OFF,
                        callback_data=BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_LIVE_PHOTO
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=BotButton.RETURN,
                        callback_data=BotCallbackText.DOWNLOAD_CHAT_FILTER
                    )
                ]
            ]
        )

    async def toggle_table_button(
            self,
            config: dict,
            choice: Union[str, None] = None
    ) -> None:
        try:
            await self.callback_query.message.edit_reply_markup(
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=BotButton.CLOSE_LINK_TABLE if config.get(
                                    'export_table').get('link') else BotButton.OPEN_LINK_TABLE,
                                callback_data=BotCallbackText.TOGGLE_LINK_TABLE
                            ),
                            InlineKeyboardButton(
                                text=BotButton.CLOSE_COUNT_TABLE if config.get(
                                    'export_table').get('count') else BotButton.OPEN_COUNT_TABLE,
                                callback_data=BotCallbackText.TOGGLE_COUNT_TABLE
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.CLOSE_UPLOAD_TABLE if config.get(
                                    'export_table').get('upload') else BotButton.OPEN_UPLOAD_TABLE,
                                callback_data=BotCallbackText.TOGGLE_UPLOAD_TABLE
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.RETURN,
                                callback_data=BotCallbackText.SETTING
                            )
                        ]
                    ]
                )
            )
        except MessageNotModified:
            pass
        except Exception as _e:
            if choice:
                if choice == 'link':
                    prompt: str = '連結'
                elif choice == 'count':
                    prompt: str = '計數'
                elif choice == 'upload':
                    prompt: str = '上載'
                else:
                    prompt: str = ''
                await self.callback_query.message.reply_text(
                    f'設定啟用或禁用匯出{prompt}統計表失敗\n(具體原因請前往終端機查看報錯資訊)'
                )
                log.error(f'設定啟用或禁用匯出{prompt}統計表失敗,{_t(KeyWord.REASON)}:"{_e}"')
            else:
                log.error(f'設定啟用或禁用匯出統計表失敗,{_t(KeyWord.REASON)}:"{_e}"')

    async def back_table_button(self):
        try:
            await self.callback_query.message.edit_reply_markup(
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=BotButton.RESELECT,
                                callback_data=BotCallbackText.BACK_TABLE
                            )
                        ],
                        [
                            InlineKeyboardButton(
                                text=BotButton.HELP_PAGE,
                                callback_data=BotCallbackText.BACK_HELP
                            )
                        ]
                    ]
                ))
        except MessageNotModified:
            pass

    async def task_assign_button(self):
        try:
            await self.callback_query.message.edit_reply_markup(
                InlineKeyboardMarkup(
                    [
                        [
                            InlineKeyboardButton(
                                text=BotButton.TASK_ASSIGN,
                                callback_data=BotCallbackText.NULL
                            )
                        ]
                    ]
                )
            )
        except MessageNotModified:
            pass

    @staticmethod
    def restrict_forward_button():
        return (
            InlineKeyboardMarkup(
                [
                    [
                        InlineKeyboardButton(
                            BotButton.DOWNLOAD,
                            callback_data=BotCallbackText.DOWNLOAD
                        ),
                        InlineKeyboardButton(
                            BotButton.DOWNLOAD_UPLOAD,
                            callback_data=BotCallbackText.DOWNLOAD_UPLOAD
                        ),
                    ]
                ]
            )
        )

    @staticmethod
    def single_button(text: str, callback_data: str):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=text,
                        callback_data=callback_data
                    )
                ]
            ]
        )

    @staticmethod
    def download_chat_filter_button(
            include_comment: bool
    ):
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=BotButton.DATE_RANGE_SETTING,
                        callback_data=BotCallbackText.DOWNLOAD_CHAT_DATE_FILTER
                    ),
                    InlineKeyboardButton(
                        text=BotButton.DOWNLOAD_DTYPE_SETTING,
                        callback_data=BotCallbackText.DOWNLOAD_CHAT_DTYPE_FILTER
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=BotButton.KEYWORD_FILTER_SETTING,
                        callback_data=BotCallbackText.DOWNLOAD_CHAT_KEYWORD_FILTER
                    ),
                    InlineKeyboardButton(
                        text=BotButton.INCLUDE_COMMENT if include_comment else BotButton.IGNORE_COMMENT,
                        callback_data=BotCallbackText.TOGGLE_DOWNLOAD_CHAT_COMMENT
                    ),
                ],
                [
                    InlineKeyboardButton(
                        text=BotButton.EXECUTE_TASK,
                        callback_data=BotCallbackText.DOWNLOAD_CHAT_ID
                    ),
                    InlineKeyboardButton(
                        text=BotButton.CANCEL_TASK,
                        callback_data=BotCallbackText.DOWNLOAD_CHAT_ID_CANCEL
                    )
                ]
            ]
        )

    @staticmethod
    def filter_date_range_button():
        return InlineKeyboardMarkup(
            [
                [
                    InlineKeyboardButton(
                        text=BotButton.SELECT_START_DATE,
                        callback_data=BotCallbackText.FILTER_START_DATE
                    ),
                    InlineKeyboardButton(
                        text=BotButton.SELECT_END_DATE,
                        callback_data=BotCallbackText.FILTER_END_DATE
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=BotButton.RETURN,
                        callback_data=BotCallbackText.DOWNLOAD_CHAT_FILTER
                    )
                ]
            ]
        )

    async def calendar_keyboard(
            self,
            dtype: Union[CalenderKeyboard, str],
            year: Optional[int] = datetime.datetime.now().year,
            month: Optional[int] = datetime.datetime.now().month
    ):
        keyboard: list = []
        prev_month: int = month - 1 if month > 1 else 12
        prev_year: int = year if month > 1 else year - 1
        next_month: int = month + 1 if month < 12 else 1
        next_year: int = year if month < 12 else year + 1
        if dtype == CalenderKeyboard.START_TIME_BUTTON:
            _dtype = 'start'
        elif dtype == CalenderKeyboard.END_TIME_BUTTON:
            _dtype = 'end'
        else:
            return None
        nav_row = [
            InlineKeyboardButton('◀️', callback_data=f'time_dec_month_{_dtype}_{prev_year}_{prev_month}'),
            InlineKeyboardButton(f'{year}-{month:02d}', callback_data=BotCallbackText.NULL),
            InlineKeyboardButton('▶️', callback_data=f'time_inc_month_{_dtype}_{next_year}_{next_month}')
        ]
        keyboard.append(nav_row)

        week_days = ['一', '二', '三', '四', '五', '六', '日']
        week_row = [InlineKeyboardButton(day, callback_data=BotCallbackText.NULL) for day in week_days]
        keyboard.append(week_row)

        cal = calendar.monthcalendar(year, month)
        for week in cal:
            row = []
            for day in week:
                if day == 0:
                    row.append(InlineKeyboardButton(' ', callback_data=BotCallbackText.NULL))
                else:
                    date_str = f'{year}-{month:02d}-{day:02d} 00:00:00'
                    row.append(InlineKeyboardButton(str(day), callback_data=f'set_specific_time_{_dtype}_{date_str}'))
            keyboard.append(row)

        keyboard.append(
            [
                InlineKeyboardButton(
                    text=BotButton.CONFIRM_AND_RETURN,
                    callback_data=BotCallbackText.DOWNLOAD_CHAT_DATE_FILTER
                ),
                InlineKeyboardButton(
                    text=BotButton.CANCEL_TASK,
                    callback_data=BotCallbackText.DOWNLOAD_CHAT_ID_CANCEL
                )
            ]
        )
        try:
            await self.callback_query.message.edit_reply_markup(InlineKeyboardMarkup(keyboard))
        except MessageNotModified:
            pass

    @staticmethod
    def time_keyboard(
            dtype: Union[CalenderKeyboard, str],
            date: str,
            adjust_step: Optional[int] = 1
    ):
        dt = datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S')
        _dtype = dtype if isinstance(dtype, str) else 'start' if dtype == CalenderKeyboard.START_TIME_BUTTON else 'end'
        hour, minute, second = 'hour', 'minute', 'second'

        def _get_updated_time(field: str, delta: int) -> str:
            new_dt = dt.replace(
                hour=(dt.hour + delta) % 24 if field == hour else dt.hour,
                minute=(dt.minute + delta) % 60 if field == minute else dt.minute,
                second=(dt.second + delta) % 60 if field == second else dt.second
            )
            return new_dt.strftime('%Y-%m-%d %H:%M:%S')

        time_keyboard = [
            [
                InlineKeyboardButton(
                    text=f'步進值:{adjust_step}',
                    callback_data=f'adjust_step_{dtype}_{adjust_step}'
                )
            ],
            [
                InlineKeyboardButton(
                    text='◀️',
                    callback_data=f'set_time_{_dtype}_{_get_updated_time(hour, -adjust_step)}'
                ),
                InlineKeyboardButton(
                    text='時', callback_data=BotCallbackText.NULL
                ),
                InlineKeyboardButton(
                    text='▶️',
                    callback_data=f'set_time_{_dtype}_{_get_updated_time(hour, adjust_step)}'
                )
            ],
            [
                InlineKeyboardButton(
                    text='◀️',
                    callback_data=f'set_time_{_dtype}_{_get_updated_time(minute, -adjust_step)}'
                ),
                InlineKeyboardButton(
                    text='分', callback_data=BotCallbackText.NULL
                ),
                InlineKeyboardButton(
                    text='▶️',
                    callback_data=f'set_time_{_dtype}_{_get_updated_time(minute, adjust_step)}'
                )
            ],
            [
                InlineKeyboardButton(
                    text='◀️',
                    callback_data=f'set_time_{_dtype}_{_get_updated_time(second, -adjust_step)}'
                ),
                InlineKeyboardButton(
                    text='秒', callback_data=BotCallbackText.NULL
                ),
                InlineKeyboardButton(
                    text='▶️',
                    callback_data=f'set_time_{_dtype}_{_get_updated_time(second, adjust_step)}'
                )
            ],
            [
                InlineKeyboardButton(
                    text=BotButton.CONFIRM_AND_RETURN,
                    callback_data=BotCallbackText.DOWNLOAD_CHAT_DATE_FILTER
                ),
                InlineKeyboardButton(
                    text=BotButton.CANCEL_TASK,
                    callback_data=BotCallbackText.DOWNLOAD_CHAT_ID_CANCEL
                )
            ]
        ]

        return InlineKeyboardMarkup(time_keyboard)

    @staticmethod
    def keyword_filter_button(
            adding_keywords: Optional[list] = None
    ):
        """關鍵詞過濾設定按鈕。"""
        if adding_keywords:
            keyword_buttons = [
                [
                    InlineKeyboardButton(
                        text=BotButton.INPUT_KEYWORD,
                        callback_data=BotCallbackText.NULL
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=BotButton.CONFIRM_KEYWORD,
                        callback_data=BotCallbackText.CONFIRM_KEYWORD
                    ),
                    InlineKeyboardButton(
                        text=BotButton.CANCEL,
                        callback_data=BotCallbackText.CANCEL_KEYWORD_INPUT
                    )
                ]
            ]
        else:
            keyword_buttons = [
                [
                    InlineKeyboardButton(
                        text=BotButton.INPUT_KEYWORD,
                        callback_data=BotCallbackText.NULL
                    )
                ],
                [
                    InlineKeyboardButton(
                        text=BotButton.RETURN,
                        callback_data=BotCallbackText.CANCEL_KEYWORD_INPUT
                    )
                ]
            ]
        return InlineKeyboardMarkup(keyword_buttons)


class CallbackData:
    def __init__(self, data: Union[dict, None] = None):
        self.data: Union[dict, None] = data


@dataclass
class CallbackContext:
    """回調處理上下文,聚合handler需要存取的對象,避免閉包捕獲。"""
    downloader: 'TelegramRestrictedMediaDownloader'  # noqa.
    client: pyrogram.Client
    query: CallbackQuery
    kb: KeyboardButton
    data: str


class CallbackHandler(ABC):
    """回調處理器基類,子類聲明exact/prefixes匹配集合並實handle。"""
    exact: tuple = ()
    prefixes: tuple = ()

    def match(self, data: str) -> bool:
        return data in self.exact or data.startswith(self.prefixes)

    @abstractmethod
    async def handle(self, ctx: CallbackContext) -> None:
        ...


class NoticeHandler(CallbackHandler):
    exact = (BotCallbackText.NOTICE,)

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        query = ctx.query
        kb = ctx.kb
        try:
            downloader.gc.config[BotCallbackText.NOTICE] = not downloader.gc.config.get(BotCallbackText.NOTICE)
            downloader.gc.save_config(downloader.gc.config)
            n_s = '啟用' if downloader.gc.config.get(BotCallbackText.NOTICE) else '禁用'
            n_p = f'機械人訊息通知已{n_s}。'
            log.info(n_p)
            console.log(n_p, style='#FF4689')
            await kb.toggle_setting_button(global_config=downloader.gc.config, user_config=downloader.app.config)
        except Exception as e:
            await query.message.reply_text('啟用或禁用機械人訊息通知失敗\n(具體原因請前往終端機查看報錯資訊)')
            log.error(f'啟用或禁用機械人訊息通知失敗,{_t(KeyWord.REASON)}:"{e}"')


class BackHandler(CallbackHandler):
    exact = (BotCallbackText.BACK_HELP, BotCallbackText.BACK_TABLE)

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        query = ctx.query
        if ctx.data == BotCallbackText.BACK_HELP:
            meta = await downloader.help()
            await query.message.edit_text(meta.get('text'))
            await query.message.edit_reply_markup(meta.get('keyboard'))
        elif ctx.data == BotCallbackText.BACK_TABLE:
            meta = await downloader.table()
            await query.message.edit_text(meta.get('text'))
            await query.message.edit_reply_markup(meta.get('keyboard'))


class TaskAssignHandler(CallbackHandler):
    exact = (BotCallbackText.DOWNLOAD, BotCallbackText.DOWNLOAD_UPLOAD)

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        kb = ctx.kb
        if not isinstance(downloader.cd.data, dict):
            return None
        meta = downloader.cd.data.copy()
        downloader.cd.data = None
        origin_link = meta.get('origin_link')
        target_link = meta.get('target_link')
        start_id = meta.get('start_id')
        end_id = meta.get('end_id')
        if ctx.data == BotCallbackText.DOWNLOAD:
            downloader.last_message.text = f'/download {origin_link} {start_id} {end_id}'
            await downloader.get_download_link_from_bot(client=downloader.last_client, message=downloader.last_message)
        elif ctx.data == BotCallbackText.DOWNLOAD_UPLOAD:
            downloader.last_message.text = f'/download {origin_link} {start_id} {end_id}'
            await downloader.get_download_link_from_bot(
                client=downloader.last_client,
                message=downloader.last_message,
                with_upload={
                    'link': target_link,
                    'file_name': None,
                    'with_delete': downloader.gc.upload_delete,
                    'send_as_media_group': True
                }
            )
        await kb.task_assign_button()


class ListenInfoHandler(CallbackHandler):
    exact = (BotCallbackText.LOOKUP_LISTEN_INFO,)

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        query = ctx.query
        # 監聽資訊由機械人命令查詢,需用登入帳號向機械人發送命令,直接發給用戶自己會落入收藏夾。
        result = await downloader.send_message_to_bot(text='/listen_info')
        if isinstance(result, Exception) or result is None:
            await query.message.reply_text('查看監聽資訊失敗\n(具體原因請前往終端機查看報錯資訊)')
            log.error(f'發送查看監聽資訊命令失敗,{_t(KeyWord.REASON)}:"{result}"')


class ShutdownHandler(CallbackHandler):
    exact = (BotCallbackText.SHUTDOWN,)

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        query = ctx.query
        kb = ctx.kb
        try:
            downloader.app.config['is_shutdown'] = not downloader.app.config.get('is_shutdown')
            downloader.app.save_config(downloader.app.config)
            s_s = '啟用' if downloader.app.config.get('is_shutdown') else '禁用'
            s_p = f'退出後關機已{s_s}。'
            log.info(s_p)
            console.log(s_p, style='#FF4689')
            await kb.toggle_setting_button(global_config=downloader.gc.config, user_config=downloader.app.config)
        except Exception as e:
            await query.message.reply_text('啟用或禁用自動關機失敗\n(具體原因請前往終端機查看報錯資訊)')
            log.error(f'啟用或禁用自動關機失敗,{_t(KeyWord.REASON)}:"{e}"')


class SettingsHandler(CallbackHandler):
    exact = (
        BotCallbackText.SETTING,
        BotCallbackText.EXPORT_TABLE,
        BotCallbackText.DOWNLOAD_SETTING,
        BotCallbackText.UPLOAD_SETTING,
        BotCallbackText.FORWARD_SETTING
    )

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        kb = ctx.kb
        if ctx.data == BotCallbackText.SETTING:
            await kb.toggle_setting_button(global_config=downloader.gc.config, user_config=downloader.app.config)
        elif ctx.data == BotCallbackText.EXPORT_TABLE:
            await kb.toggle_table_button(config=downloader.gc.config)
        elif ctx.data == BotCallbackText.DOWNLOAD_SETTING:
            await kb.toggle_download_setting_button(user_config=downloader.app.config)
        elif ctx.data == BotCallbackText.UPLOAD_SETTING:
            await kb.toggle_upload_setting_button(global_config=downloader.gc.config)
        elif ctx.data == BotCallbackText.FORWARD_SETTING:
            await kb.toggle_forward_setting_button(global_config=downloader.gc.config)


class TableHandler(CallbackHandler):
    exact = (
        BotCallbackText.LINK_TABLE,
        BotCallbackText.COUNT_TABLE,
        BotCallbackText.UPLOAD_TABLE,
        BotCallbackText.TOGGLE_LINK_TABLE,
        BotCallbackText.TOGGLE_COUNT_TABLE,
        BotCallbackText.TOGGLE_UPLOAD_TABLE,
        BotCallbackText.EXPORT_LINK_TABLE,
        BotCallbackText.EXPORT_COUNT_TABLE,
        BotCallbackText.EXPORT_UPLOAD_TABLE
    )

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        query = ctx.query
        kb = ctx.kb
        data = ctx.data
        if data in (BotCallbackText.LINK_TABLE, BotCallbackText.COUNT_TABLE, BotCallbackText.UPLOAD_TABLE):
            prompt_string = ''
            false_text = ''
            choice = ''
            res = None
            if data == BotCallbackText.LINK_TABLE:
                prompt_string = '連結統計表'
                false_text = '😵😵😵沒有連結需要統計。'
                choice = BotCallbackText.EXPORT_LINK_TABLE
                res = downloader.app.print_link_table(DownloadTask.TASKS)
            elif data == BotCallbackText.COUNT_TABLE:
                prompt_string = '計數統計表'
                false_text = '😵😵😵目前沒有任何下載。'
                choice = BotCallbackText.EXPORT_COUNT_TABLE
                res = downloader.app.print_count_table()
            elif data == BotCallbackText.UPLOAD_TABLE:
                prompt_string = '上載統計表'
                false_text = '😵😵😵目前沒有任何上載。'
                choice = BotCallbackText.EXPORT_UPLOAD_TABLE
                res = downloader.app.print_upload_table(UploadTask.TASKS)
            if res:
                await downloader.send_rich_table(message=query.message, chunks=res)
                await kb.choice_export_table_button(choice=choice)
                return None
            elif res is False:
                await query.message.edit_text(false_text)
            else:
                await query.message.edit_text(
                    f'😵‍💫😵‍💫😵‍💫`{prompt_string}`列印失敗。\n(具體原因請前往終端機查看報錯資訊)')
            await kb.back_table_button()
        elif data in (
                BotCallbackText.TOGGLE_LINK_TABLE,
                BotCallbackText.TOGGLE_COUNT_TABLE,
                BotCallbackText.TOGGLE_UPLOAD_TABLE
        ):
            if data == BotCallbackText.TOGGLE_LINK_TABLE:
                await self.__toggle_export_table(ctx, 'link')
            elif data == BotCallbackText.TOGGLE_COUNT_TABLE:
                await self.__toggle_export_table(ctx, 'count')
            elif data == BotCallbackText.TOGGLE_UPLOAD_TABLE:
                await self.__toggle_export_table(ctx, 'upload')
        elif data in (
                BotCallbackText.EXPORT_LINK_TABLE,
                BotCallbackText.EXPORT_COUNT_TABLE,
                BotCallbackText.EXPORT_UPLOAD_TABLE
        ):
            prompt_string = ''
            folder = ''
            res = False
            if data == BotCallbackText.EXPORT_LINK_TABLE:
                prompt_string = '連結統計表'
                folder = 'DownloadRecordForm'
                res = downloader.app.print_link_table(link_tasks=DownloadTask.TASKS, export=True, only_export=True)
            elif data == BotCallbackText.EXPORT_COUNT_TABLE:
                prompt_string = '計數統計表'
                folder = 'DownloadRecordForm'
                res = downloader.app.print_count_table(export=True, only_export=True)
            elif data == BotCallbackText.EXPORT_UPLOAD_TABLE:
                prompt_string = '上載統計表'
                folder = 'UploadRecordForm'
                res = downloader.app.print_upload_table(upload_tasks=UploadTask.TASKS, export=True, only_export=True)
            if res:
                folder = 'form' if is_docker() else folder
                await query.message.edit_text(
                    f'✅✅✅`{prompt_string}`已發送至您的「終端機」並已「匯出」為表格請注意查收。\n(請查看軟件目錄下`{folder}`資料夾)')
            elif res is False:
                await query.message.edit_text('😵😵😵沒有連結需要統計。')
            else:
                await query.message.edit_text(
                    f'😵‍💫😵‍💫😵‍💫`{prompt_string}`匯出失敗。\n(具體原因請前往終端機查看報錯資訊)')
            await kb.back_table_button()

    @staticmethod
    async def __toggle_export_table(ctx: CallbackContext, table_type: str) -> None:
        downloader = ctx.downloader
        kb = ctx.kb
        export_config = downloader.gc.config.get('export_table')
        export_config[table_type] = not export_config.get(table_type)
        if table_type == 'link':
            t_t = '連結統計表'
        elif table_type == 'count':
            t_t = '計數統計表'
        elif table_type == 'upload':
            t_t = '上載統計表'
        else:
            t_t = '統計表'
        s_t = '啟用' if export_config.get(table_type) else '禁用'
        t_p = f'退出後匯出{t_t}已{s_t}。'
        console.log(t_p, style='#FF4689')
        log.info(t_p)
        downloader.gc.save_config(downloader.gc.config)
        await kb.toggle_table_button(config=downloader.gc.config, choice=table_type)


class UploadDownloadSettingHandler(CallbackHandler):
    exact = (BotCallbackText.UPLOAD_DOWNLOAD, BotCallbackText.UPLOAD_DOWNLOAD_DELETE)

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        query = ctx.query
        kb = ctx.kb
        try:
            if ctx.data == BotCallbackText.UPLOAD_DOWNLOAD:
                self.__toggle_upload_param(downloader, 'download_upload')
            elif ctx.data == BotCallbackText.UPLOAD_DOWNLOAD_DELETE:
                self.__toggle_upload_param(downloader, 'delete')
            downloader.gc.save_config(downloader.gc.config)
            await kb.toggle_upload_setting_button(global_config=downloader.gc.config)
        except Exception as e:
            await query.message.reply_text('上載設定失敗\n(具體原因請前往終端機查看報錯資訊)')
            log.error(f'上載設定失敗,{_t(KeyWord.REASON)}:"{e}"')

    @staticmethod
    def __toggle_upload_param(downloader, param):
        current = downloader.gc.get_nesting_config(
            default_nesting=downloader.gc.default_upload_nesting, param='upload', nesting_param=param)
        downloader.gc.config.get('upload', downloader.gc.default_upload_nesting)[param] = not current
        u_s = '禁用' if current else '開啟'
        u_p = ''
        if param == 'delete':
            u_p = f'遇到"受限轉發"時,下載後上載並"刪除上載完成的本機檔案"的行為已{u_s}。'
        elif param == 'download_upload':
            u_p = f'遇到"受限轉發"時,下載後上載已{u_s}。'
        console.log(u_p, style='#FF4689')
        log.info(u_p)


class DownloadTypeHandler(CallbackHandler):
    exact = (
        BotCallbackText.TOGGLE_DOWNLOAD_VIDEO,
        BotCallbackText.TOGGLE_DOWNLOAD_PHOTO,
        BotCallbackText.TOGGLE_DOWNLOAD_AUDIO,
        BotCallbackText.TOGGLE_DOWNLOAD_VOICE,
        BotCallbackText.TOGGLE_DOWNLOAD_ANIMATION,
        BotCallbackText.TOGGLE_DOWNLOAD_DOCUMENT,
        BotCallbackText.TOGGLE_DOWNLOAD_VIDEO_NOTE,
        BotCallbackText.TOGGLE_DOWNLOAD_LIVE_PHOTO
    )

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        query = ctx.query
        kb = ctx.kb
        try:
            if ctx.data == BotCallbackText.TOGGLE_DOWNLOAD_VIDEO:
                self.__toggle_download_type(downloader, 'video')
            elif ctx.data == BotCallbackText.TOGGLE_DOWNLOAD_PHOTO:
                self.__toggle_download_type(downloader, 'photo')
            elif ctx.data == BotCallbackText.TOGGLE_DOWNLOAD_AUDIO:
                self.__toggle_download_type(downloader, 'audio')
            elif ctx.data == BotCallbackText.TOGGLE_DOWNLOAD_VOICE:
                self.__toggle_download_type(downloader, 'voice')
            elif ctx.data == BotCallbackText.TOGGLE_DOWNLOAD_ANIMATION:
                self.__toggle_download_type(downloader, 'animation')
            elif ctx.data == BotCallbackText.TOGGLE_DOWNLOAD_DOCUMENT:
                self.__toggle_download_type(downloader, 'document')
            elif ctx.data == BotCallbackText.TOGGLE_DOWNLOAD_VIDEO_NOTE:
                self.__toggle_download_type(downloader, 'video_note')
            elif ctx.data == BotCallbackText.TOGGLE_DOWNLOAD_LIVE_PHOTO:
                self.__toggle_download_type(downloader, 'live_photo')
            downloader.app.config['download_type'] = downloader.app.download_type
            downloader.app.save_config(downloader.app.config)
            await kb.toggle_download_setting_button(downloader.app.config)
        except ValueError:
            await query.message.reply_text('⚠️⚠️⚠️至少需要選擇一個下載類型⚠️⚠️⚠️')
        except Exception as e:
            await query.message.reply_text('下載類型設定失敗\n(具體原因請前往終端機查看報錯資訊)')
            log.error(f'下載類型設定失敗,{_t(KeyWord.REASON)}:"{e}"')

    @staticmethod
    def __toggle_download_type(downloader, param):
        if param in downloader.app.download_type:
            if len(downloader.app.download_type) == 1:
                raise ValueError
            f_s = '禁用'
            downloader.app.download_type.remove(param)
        else:
            f_s = '啟用'
            downloader.app.download_type.append(param)
        f_p = f'已{f_s}"{param}"類型的下載。'
        console.log(f_p, style='#FF4689')
        log.info(f_p)


class ForwardTypeHandler(CallbackHandler):
    exact = (
        BotCallbackText.TOGGLE_FORWARD_VIDEO,
        BotCallbackText.TOGGLE_FORWARD_PHOTO,
        BotCallbackText.TOGGLE_FORWARD_AUDIO,
        BotCallbackText.TOGGLE_FORWARD_VOICE,
        BotCallbackText.TOGGLE_FORWARD_ANIMATION,
        BotCallbackText.TOGGLE_FORWARD_DOCUMENT,
        BotCallbackText.TOGGLE_FORWARD_TEXT,
        BotCallbackText.TOGGLE_FORWARD_VIDEO_NOTE,
        BotCallbackText.TOGGLE_FORWARD_LIVE_PHOTO
    )

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        query = ctx.query
        kb = ctx.kb
        try:
            if ctx.data == BotCallbackText.TOGGLE_FORWARD_VIDEO:
                self.__toggle_forward_type(downloader, 'video')
            elif ctx.data == BotCallbackText.TOGGLE_FORWARD_PHOTO:
                self.__toggle_forward_type(downloader, 'photo')
            elif ctx.data == BotCallbackText.TOGGLE_FORWARD_AUDIO:
                self.__toggle_forward_type(downloader, 'audio')
            elif ctx.data == BotCallbackText.TOGGLE_FORWARD_VOICE:
                self.__toggle_forward_type(downloader, 'voice')
            elif ctx.data == BotCallbackText.TOGGLE_FORWARD_ANIMATION:
                self.__toggle_forward_type(downloader, 'animation')
            elif ctx.data == BotCallbackText.TOGGLE_FORWARD_DOCUMENT:
                self.__toggle_forward_type(downloader, 'document')
            elif ctx.data == BotCallbackText.TOGGLE_FORWARD_TEXT:
                self.__toggle_forward_type(downloader, 'text')
            elif ctx.data == BotCallbackText.TOGGLE_FORWARD_VIDEO_NOTE:
                self.__toggle_forward_type(downloader, 'video_note')
            elif ctx.data == BotCallbackText.TOGGLE_FORWARD_LIVE_PHOTO:
                self.__toggle_forward_type(downloader, 'live_photo')
            downloader.gc.save_config(downloader.gc.config)
            await kb.toggle_forward_setting_button(downloader.gc.config)
        except ValueError:
            await query.message.reply_text('⚠️⚠️⚠️至少需要選擇一個轉發類型⚠️⚠️⚠️')
        except Exception as e:
            await query.message.reply_text('轉發設定失敗\n(具體原因請前往終端機查看報錯資訊)')
            log.error(f'轉發設定失敗,{_t(KeyWord.REASON)}:"{e}"')

    @staticmethod
    def __toggle_forward_type(downloader, param):
        forward_type = downloader.gc.config.get('forward_type', downloader.gc.default_forward_type_nesting)
        status = downloader.gc.get_nesting_config(
            default_nesting=downloader.gc.default_forward_type_nesting, param='forward_type', nesting_param=param)
        if list(forward_type.values()).count(True) == 1 and status:
            raise ValueError
        forward_type[param] = not status
        f_s = '禁用' if status else '啟用'
        f_p = f'已{f_s}"{param}"類型的轉發。'
        console.log(f_p, style='#FF4689')
        log.info(f_p)


class ListenRemoveHandler(CallbackHandler):
    exact = (BotCallbackText.REMOVE_LISTEN_FORWARD,)
    prefixes = (BotCallbackText.REMOVE_LISTEN_DOWNLOAD,)

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        query = ctx.query
        data = ctx.data
        if data.startswith(BotCallbackText.REMOVE_LISTEN_DOWNLOAD):
            args = data.split()
            link = args[1]
            downloader.app.client.remove_handler(downloader.listen_download_chat.get(link))
            downloader.listen_download_chat.pop(link)
            await query.message.edit_text(link)
            await query.message.edit_reply_markup(
                KeyboardButton.single_button(text=BotButton.ALREADY_REMOVE, callback_data=BotCallbackText.NULL))
            p = f'已刪除監聽下載,頻道連結:"{link}"。'
            console.log(p, style='#FF4689')
            log.info(f'{p}目前的監聽下載資訊:{downloader.listen_download_chat}')
            return None
        if not isinstance(downloader.cd.data, dict):
            return None
        meta = downloader.cd.data.copy()
        downloader.cd.data = None
        link = meta.get('link')
        downloader.app.client.remove_handler(downloader.listen_forward_chat.get(link))
        downloader.listen_forward_chat.pop(link)
        m = link.split()
        joined = ' -> '.join(m)
        p = f'已刪除監聽轉發,轉發規則:"{joined}"。'
        await query.message.edit_text(' ➡️ '.join(m))
        await query.message.edit_reply_markup(
            KeyboardButton.single_button(text=BotButton.ALREADY_REMOVE, callback_data=BotCallbackText.NULL))
        console.log(p, style='#FF4689')
        log.info(f'{p}目前的監聽轉發資訊:{downloader.listen_forward_chat}')


class DownloadChatHandler(CallbackHandler):
    exact = (
        BotCallbackText.DOWNLOAD_CHAT_FILTER,
        BotCallbackText.DOWNLOAD_CHAT_DATE_FILTER,
        BotCallbackText.DOWNLOAD_CHAT_DTYPE_FILTER,
        BotCallbackText.DOWNLOAD_CHAT_KEYWORD_FILTER,
        BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VIDEO,
        BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_PHOTO,
        BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_AUDIO,
        BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VOICE,
        BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_ANIMATION,
        BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_DOCUMENT,
        BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VIDEO_NOTE,
        BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_LIVE_PHOTO,
        BotCallbackText.TOGGLE_DOWNLOAD_CHAT_COMMENT,
        BotCallbackText.DOWNLOAD_CHAT_ID,
        BotCallbackText.DOWNLOAD_CHAT_ID_CANCEL,
        BotCallbackText.FILTER_START_DATE,
        BotCallbackText.FILTER_END_DATE,
        BotCallbackText.CONFIRM_KEYWORD,
        BotCallbackText.CANCEL_KEYWORD_INPUT
    )
    prefixes = (
        'time_inc_',
        'time_dec_',
        'set_time_',
        'set_specific_time_',
        'adjust_step_',
        'drop_keyword_',
        'ignore_keyword'
    )

    def match(self, data: str) -> bool:
        # DOWNLOAD_CHAT_ID在download_chat啟動時被執行時改寫為真實chat_id,
        # 因此執行任務的回調資料就是該真實chat_id,必須動態讀取此常量來匹配。
        return (
                data in self.exact
                or data.startswith(self.prefixes)
                or data == BotCallbackText.DOWNLOAD_CHAT_ID
        )

    async def handle(self, ctx: CallbackContext) -> None:
        downloader = ctx.downloader
        query = ctx.query
        kb = ctx.kb
        data = ctx.data
        # 先捕獲真實chat_id到局部變量,此時BotCallbackText.DOWNLOAD_CHAT_ID仍為執行時改寫值。
        chat_id = BotCallbackText.DOWNLOAD_CHAT_ID
        if data in (BotCallbackText.DOWNLOAD_CHAT_ID, BotCallbackText.DOWNLOAD_CHAT_ID_CANCEL):
            # 任務結束後將常量重置回字面量,作為"無進行中download_chat"的狀態位。
            BotCallbackText.DOWNLOAD_CHAT_ID = 'download_chat_id'
            downloader.adding_keywords.clear()
            downloader.add_keyword_mode_handler(
                chat_id=chat_id,
                callback_query=query,
                callback_prompt=partial(self.__filter_prompt, downloader, chat_id),
                enable=False
            )
            if data == chat_id:
                await downloader.download_chat(chat_id=chat_id, callback_query=query)
                self.__remove_chat_id(downloader, chat_id)
            elif data == BotCallbackText.DOWNLOAD_CHAT_ID_CANCEL:
                self.__remove_chat_id(downloader, chat_id)
                await query.message.edit_text(
                    text=query.message.text,
                    reply_markup=kb.single_button(
                        text=BotButton.TASK_CANCEL,
                        callback_data=BotCallbackText.NULL
                    )
                )
        elif data in (BotCallbackText.DOWNLOAD_CHAT_FILTER, BotCallbackText.DOWNLOAD_CHAT_DATE_FILTER):
            if data == BotCallbackText.DOWNLOAD_CHAT_DATE_FILTER:
                start_time, end_time = self.__get_update_time(downloader, chat_id)
                if not await self.__verification_time(query, start_time, end_time):
                    return None
            await query.message.edit_text(
                text=self.__filter_prompt(downloader, chat_id),
                reply_markup=kb.download_chat_filter_button(
                    downloader.download_chat_filter[chat_id][
                        'comment']) if data == BotCallbackText.DOWNLOAD_CHAT_FILTER else kb.filter_date_range_button()
            )
        elif data in (BotCallbackText.FILTER_START_DATE, BotCallbackText.FILTER_END_DATE):
            dtype = None
            p_s_d = ''
            if data == BotCallbackText.FILTER_START_DATE:
                dtype = CalenderKeyboard.START_TIME_BUTTON
                p_s_d = '起始'
            elif data == BotCallbackText.FILTER_END_DATE:
                dtype = CalenderKeyboard.END_TIME_BUTTON
                p_s_d = '結束'
            await query.message.edit_text(text=f'📅選擇{p_s_d}日期:\n{self.__filter_prompt(downloader, chat_id)}')
            await kb.calendar_keyboard(dtype=dtype)
        elif data.startswith('adjust_step_'):
            parts = data.split('_')
            dtype = parts[-2]
            current_step = int(parts[-1])
            step_sequence = [1, 2, 5, 10, 15, 20]
            current_index = step_sequence.index(current_step)
            next_index = (current_index + 1) % len(step_sequence)
            new_step = step_sequence[next_index]
            downloader.download_chat_filter[chat_id]['date_range']['adjust_step'] = new_step
            current_date = datetime.datetime.fromtimestamp(
                downloader.download_chat_filter[chat_id]['date_range'][f'{dtype}_date']
            ).strftime('%Y-%m-%d %H:%M:%S')
            await query.message.edit_reply_markup(
                reply_markup=kb.time_keyboard(
                    dtype=dtype,
                    date=current_date,
                    adjust_step=new_step
                )
            )
        elif data.startswith(('time_inc_', 'time_dec_')):
            parts = data.split('_')
            dtype = None
            if 'start' in data:
                dtype = CalenderKeyboard.START_TIME_BUTTON
            elif 'end' in data:
                dtype = CalenderKeyboard.END_TIME_BUTTON
            if 'month' in data:
                year = int(parts[-2])
                month = int(parts[-1])
                await kb.calendar_keyboard(year=year, month=month, dtype=dtype)
                log.info(f'日期切換為{year}年,{month}月。')
        elif data.startswith(('set_time_', 'set_specific_time_')):
            parts = data.split('_')
            date = parts[-1]
            dtype = parts[-2]
            date_type = ''
            p_s_d = ''
            timestamp = datetime.datetime.timestamp(datetime.datetime.strptime(date, '%Y-%m-%d %H:%M:%S'))
            if 'start' in data:
                date_type = 'start_date'
                p_s_d = '起始'
            elif 'end' in data:
                date_type = 'end_date'
                p_s_d = '結束'
            downloader.download_chat_filter[chat_id]['date_range'][date_type] = timestamp
            await query.message.edit_text(
                text=f'📅選擇{p_s_d}日期:\n{self.__filter_prompt(downloader, chat_id)}',
                reply_markup=kb.time_keyboard(
                    dtype=dtype,
                    date=date,
                    adjust_step=downloader.download_chat_filter[chat_id]['date_range']['adjust_step']
                )
            )
            log.info(
                f'日期設定,起始日期:{self.__get_update_time(downloader, chat_id)[0]},結束日期:{self.__get_update_time(downloader, chat_id)[1]}。')
        elif data.startswith(('drop_keyword_', 'ignore_keyword')):
            if data.startswith('drop_keyword_'):
                parts = data.split('_')
                keyword = parts[-1]
                keyword_dict = downloader.download_chat_filter.get(chat_id, {}).get('keyword', {})
                keyword_dict.pop(keyword)
                downloader.adding_keywords.remove(keyword)
            await query.message.edit_text(
                text=self.__filter_prompt(downloader, chat_id),
                reply_markup=KeyboardButton.keyword_filter_button(downloader.adding_keywords)
            )
        elif data in (
                BotCallbackText.DOWNLOAD_CHAT_DTYPE_FILTER,
                BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VIDEO,
                BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_PHOTO,
                BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_AUDIO,
                BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VOICE,
                BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_ANIMATION,
                BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_DOCUMENT,
                BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VIDEO_NOTE,
                BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_LIVE_PHOTO
        ):
            try:
                if data == BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VIDEO:
                    self.__toggle_download_chat_dtype(downloader, chat_id, 'video')
                elif data == BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_PHOTO:
                    self.__toggle_download_chat_dtype(downloader, chat_id, 'photo')
                elif data == BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_AUDIO:
                    self.__toggle_download_chat_dtype(downloader, chat_id, 'audio')
                elif data == BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VOICE:
                    self.__toggle_download_chat_dtype(downloader, chat_id, 'voice')
                elif data == BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_ANIMATION:
                    self.__toggle_download_chat_dtype(downloader, chat_id, 'animation')
                elif data == BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_DOCUMENT:
                    self.__toggle_download_chat_dtype(downloader, chat_id, 'document')
                elif data == BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_VIDEO_NOTE:
                    self.__toggle_download_chat_dtype(downloader, chat_id, 'video_note')
                elif data == BotCallbackText.TOGGLE_DOWNLOAD_CHAT_DTYPE_LIVE_PHOTO:
                    self.__toggle_download_chat_dtype(downloader, chat_id, 'live_photo')
                await query.message.edit_text(
                    text=self.__filter_prompt(downloader, chat_id),
                    reply_markup=kb.toggle_download_chat_type_filter_button(downloader.download_chat_filter)
                )
            except ValueError:
                await query.message.reply_text('⚠️⚠️⚠️至少需要選擇一個下載類型⚠️⚠️⚠️')
            except Exception as e:
                await query.message.reply_text('下載類型設定失敗\n(具體原因請前往終端機查看報錯資訊)')
                log.error(f'下載類型設定失敗,{_t(KeyWord.REASON)}:"{e}"', exc_info=True)
        elif data in (
                BotCallbackText.DOWNLOAD_CHAT_KEYWORD_FILTER,
                BotCallbackText.CONFIRM_KEYWORD,
                BotCallbackText.CANCEL_KEYWORD_INPUT
        ):
            if data == BotCallbackText.DOWNLOAD_CHAT_KEYWORD_FILTER:
                try:
                    await query.message.edit_text(
                        text=self.__filter_prompt(downloader, chat_id),
                        reply_markup=kb.keyword_filter_button(downloader.adding_keywords)
                    )
                except MessageNotModified:
                    pass
                downloader.add_keyword_mode_handler(
                    enable=True,
                    chat_id=chat_id,
                    callback_query=query,
                    callback_prompt=partial(self.__filter_prompt, downloader, chat_id)
                )
            elif data == BotCallbackText.CONFIRM_KEYWORD:
                downloader.add_keyword_mode_handler(
                    enable=False,
                    chat_id=chat_id,
                    callback_query=query,
                    callback_prompt=partial(self.__filter_prompt, downloader, chat_id)
                )
                await query.message.edit_text(
                    text=self.__filter_prompt(downloader, chat_id),
                    reply_markup=kb.download_chat_filter_button(downloader.download_chat_filter[chat_id]['comment'])
                )
            elif data == BotCallbackText.CANCEL_KEYWORD_INPUT:
                downloader.adding_keywords.clear()
                downloader.add_keyword_mode_handler(
                    enable=False,
                    chat_id=chat_id,
                    callback_query=query,
                    callback_prompt=partial(self.__filter_prompt, downloader, chat_id)
                )
                downloader.download_chat_filter[chat_id]['keyword'] = {}
                await query.message.edit_text(
                    text=self.__filter_prompt(downloader, chat_id),
                    reply_markup=kb.download_chat_filter_button(downloader.download_chat_filter[chat_id]['comment'])
                )
        elif data == BotCallbackText.TOGGLE_DOWNLOAD_CHAT_COMMENT:
            status = downloader.download_chat_filter[chat_id]['comment']
            downloader.download_chat_filter[chat_id]['comment'] = not status
            await query.message.edit_text(
                text=self.__filter_prompt(downloader, chat_id),
                reply_markup=kb.download_chat_filter_button(downloader.download_chat_filter[chat_id]['comment'])
            )

    @staticmethod
    def __get_update_time(downloader, chat_id):
        start_timestamp = downloader.download_chat_filter[chat_id]['date_range']['start_date']
        end_timestamp = downloader.download_chat_filter[chat_id]['date_range']['end_date']
        start_time = datetime.datetime.fromtimestamp(start_timestamp) if start_timestamp else '未定義'
        end_time = datetime.datetime.fromtimestamp(end_timestamp) if end_timestamp else '未定義'
        return start_time, end_time

    @staticmethod
    def __get_format_dtype(downloader, chat_id):
        download_type = []
        for dtype, status in downloader.download_chat_filter[chat_id]['download_type'].items():
            if status:
                download_type.append(_t(dtype))
        return ','.join(download_type)

    @staticmethod
    def __get_format_keywords(downloader, chat_id):
        keywords = downloader.download_chat_filter[chat_id]['keyword']
        if not keywords:
            return '未定義'
        return ','.join(keywords.keys())

    @staticmethod
    def __get_format_comment_status(downloader, chat_id):
        status = downloader.download_chat_filter[chat_id]['comment']
        return '開' if status else '關'

    @staticmethod
    def __remove_chat_id(downloader, chat_id):
        if chat_id in downloader.download_chat_filter:
            downloader.download_chat_filter.pop(chat_id)
            log.info(f'"{chat_id}"已從{downloader.download_chat_filter}中移除。')

    def __filter_prompt(self, downloader, chat_id):
        start_time, end_time = self.__get_update_time(downloader, chat_id)
        return (
            f'💬下載頻道:`{chat_id}`\n'
            f'⏮️目前選擇的起始日期為:{start_time}\n'
            f'⏭️目前選擇的結束日期為:{end_time}\n'
            f'📝目前選擇的下載類型為:{self.__get_format_dtype(downloader, chat_id)}\n'
            f'🔑目前匹配的關鍵詞為:{self.__get_format_keywords(downloader, chat_id)}\n'
            f'👥包含評論區:{self.__get_format_comment_status(downloader, chat_id)}'
        )

    @staticmethod
    async def __verification_time(query, start_time, end_time) -> bool:
        if isinstance(start_time, datetime.datetime) and isinstance(end_time, datetime.datetime):
            if start_time > end_time:
                await query.message.reply_text(
                    text=f'❌❌❌日期設定失敗❌❌❌\n'
                         f'`起始日期({start_time})`>`結束日期({end_time})`\n'
                )
                return False
            elif start_time == end_time:
                await query.message.reply_text(
                    text=f'❌❌❌日期設定失敗❌❌❌\n'
                         f'`起始日期({start_time})`=`結束日期({end_time})`\n'
                )
                return False
        return True

    @staticmethod
    def __toggle_download_chat_dtype(downloader, chat_id, param):
        dtype = downloader.download_chat_filter[chat_id]['download_type']
        status = dtype[param]
        if list(dtype.values()).count(True) == 1 and status:
            raise ValueError
        dtype[param] = not status
        f_s = '禁用' if status else '啟用'
        f_p = f'已{f_s}"{param}"類型用於/download_chat命令的下載。'
        log.info(f'{f_p}目前的/download_chat下載類型設定:{dtype}')


CALLBACK_HANDLERS: tuple = (
    NoticeHandler(),
    BackHandler(),
    TaskAssignHandler(),
    ListenInfoHandler(),
    ShutdownHandler(),
    SettingsHandler(),
    TableHandler(),
    UploadDownloadSettingHandler(),
    DownloadTypeHandler(),
    ForwardTypeHandler(),
    ListenRemoveHandler(),
    DownloadChatHandler()
)


async def dispatch_callback_data(ctx: CallbackContext) -> None:
    """按註冊表順序分發回調,首個匹配的處理器負責處理。"""
    for handler in CALLBACK_HANDLERS:
        if handler.match(ctx.data):
            await handler.handle(ctx)
            return None
