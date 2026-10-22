# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026/9/10 12:00
# File:web.py
import os
import re
import sys
import json
import base64
import socket
import asyncio
import mimetypes
import threading
import tempfile
import copy

from typing import Union
from asyncio import AbstractEventLoop
from concurrent.futures import TimeoutError as FutureTimeoutError
from urllib.parse import parse_qs, unquote, urlsplit
from http.server import (
    ThreadingHTTPServer,
    BaseHTTPRequestHandler
)

from pyrogram import __version__ as pyrogram_version  # noqa.
import yaml

from module import (
    log,
    VERSION_WITH_COMMIT
)
from module.remote import rc
from module.language import _t
from module.parser import PARSE_ARGS
from module.path_tool import split_path
from module.stdio import (
    MetaData,
    PanelTable
)
from module.task import (
    ChatInfo,
    UploadTask,
    DownloadTask
)
from module.util import (
    is_frozen,
    get_local_ip,
    get_web_session,
    reset_web_session,
    get_message_dtype,
    get_work_directory,
    gen_random_credential
)
from module.enums import (
    WebMeta,
    KeyWord,
    UploadStatus,
    DownloadStatus,
    DownloadType
)
from module.app_core import AppCore
from module.bot_controller import BotController
from module.web_api import WebAPI


class WebHandler(BaseHTTPRequestHandler):
    """處理網頁面板的請求。"""
    server_version: str = 'TRMDWeb'
    remember_session: bool = False  # 本次響應是否需要下發Cookie。
    expire_session: bool = False  # 本次響應是否需要清除Cookie(登出)。
    # 首頁<body>起始標籤,用正則匹配,模板給<body>新增屬性後替換依然生效。
    BODY_TAG_PATTERN: bytes = rb'<body\b[^>]*>'
    # data-auth 表示已啟用密碼認證,前端據此顯示"登出"入口。
    # 已設定帳號密碼時注入:首屏先隱藏頁面內容,避免F5重新整理時閃現一瞬間的已登入介面。
    LOGIN_BODY: bytes = b'<body data-auth="1" class="logged-out" data-bot="__HAS_BOT__">'
    VERSION_PLACEHOLDER: bytes = b'__VERSION__'  # 首頁模板中的TRMD版本佔位符,返回頁面時替換為實際版本號。
    # 首頁模板中的Pyrogram版本佔位符,返回頁面時替換為實際版本號。
    PYROGRAM_PLACEHOLDER: bytes = b'__PYROGRAM_VERSION__'
    HAS_BOT_PLACEHOLDER: bytes = b'__HAS_BOT__'  # 是否設定了機械人(bot_token),前端據此隱藏上載與監聽側邊欄。

    def do_GET(self) -> None:  # noqa.
        if self.path.startswith('/api/'):
            # 介面需要認證;頁面與靜態資源放行,否則登入卡片自身無法載入。
            if self.__check_auth() is False:  # noqa.
                return
            if self.path.startswith('/api/progress'):
                self.__response_progress()
            elif self.path == '/api/events':
                self.__response_events()
            elif self.path == '/api/settings':
                web: Union[Web, None] = getattr(self.server, 'web', None)
                self.__response_json(
                    web.get_settings() if web else {'status': False, 'e_code': '網頁面板尚未就緒。'}
                )
            elif self.path.startswith('/api/admin/'):
                web = getattr(self.server, 'web', None)
                parsed_path = urlsplit(self.path)
                result = web.api.get(parsed_path.path, parse_qs(parsed_path.query)) if web else {
                    'status': False, 'e_code': '網頁面板尚未就緒。'
                }
                self.__response_json(result, status=200 if result.get('status') else 400)
            elif self.path == '/api/status':
                web = getattr(self.server, 'web', None)
                self.__response_json(
                    web.get_service_status() if web else {'status': False, 'e_code': '網頁面板尚未就緒。'}
                )
            else:
                self.send_error(404)
            return
        self.__response_static()

    def do_POST(self) -> None:  # noqa.
        if self.path.startswith('/api/login'):
            self.__response_login()  # 登入介面本身不能被認證攔截。
            return
        if self.path.startswith('/api/logout'):
            self.__response_logout()  # 登出同樣不能被認證攔截。
            return
        if self.__check_auth() is False:  # noqa.
            return
        if self.path.startswith('/api/listener/remove'):
            self.__response_remove_listener()
        elif self.path.startswith('/api/admin/'):
            self.__response_admin()
        else:
            self.send_error(404)

    @staticmethod
    def replace_body_tag(body: bytes, tag: bytes) -> bytes:
        """替換首頁的<body>起始標籤,注入認證標記與機械人標記。
        模板的<body>可能攜帶屬性,直接按固定字串替換會漏掉,故用正則匹配起始標籤本身。"""
        return re.sub(WebHandler.BODY_TAG_PATTERN, tag, body, count=1)

    def log_message(self, fmt, *args) -> None:
        """屏蔽預設的請求日誌,避免污染終端機輸出。"""

    def __check_auth(self) -> bool:
        """校驗認證:優先Cookie免密,其次前端持有的臨時令牌,最後回退到Basic認證。"""
        self.remember_session = False
        web: Union[Web, None] = getattr(self.server, 'web', None)
        if web is None or not web.username:
            return True
        if web.check_session(self.__get_cookie()):
            return True  # 瀏覽器已被記住,無需重複輸入密碼。
        authorization: str = self.headers.get('Authorization', '')
        if authorization.startswith('Bearer '):
            # 未勾選"30天內免登入"時不發Cookie,前端把令牌存sessionStorage並隨請求帶來,關閉標籤頁即失效。
            if web.check_session(authorization.split(' ', 1)[1].strip()):
                return True
        if not authorization.startswith('Basic '):
            self.__response_unauthorized()
            return False
        try:
            credential: str = base64.b64decode(authorization.split(' ', 1)[1]).decode('UTF-8')
        except Exception:  # noqa.
            self.__response_unauthorized()
            return False
        if credential != f'{web.username}:{web.password}':
            self.__response_unauthorized()
            return False
        self.remember_session = True  # 首次認證成功,響應時下發Cookie。
        return True

    def __get_cookie(self) -> str:
        """讀取請求頭中指定名稱的Cookie。"""
        for item in self.headers.get('Cookie', '').split(';'):
            name, _, value = item.strip().partition('=')
            if name == WebMeta.COOKIE_NAME:
                return value
        return ''

    def __response_unauthorized(self) -> None:
        """返回需要認證的響應。
        不下發 WWW-Authenticate:否則瀏覽器會彈出系統自帶的帳號密碼框,
        無法套用頁面風格;改由前端展示毛玻璃登入卡片。"""
        self.send_response(401)
        self.send_header('Content-Length', '0')
        self.end_headers()

    def __response_login(self) -> None:
        """校驗登入卡片提交的帳號密碼。
        勾選"30天內免登入"才下發長期Cookie;未勾選時不下發Cookie,
        改為把令牌返回給前端存放在sessionStorage,關閉標籤頁即需重新登入。"""
        web: Union[Web, None] = getattr(self.server, 'web', None)
        payload: dict = self.__read_json()
        ok: bool = False
        if web is not None:
            if not web.username:  # 未設定帳號密碼時直接放行。
                ok = True
            else:
                username: str = str(payload.get('username') or '')
                password: str = str(payload.get('password') or '')
                ok = username == web.username and password == web.password
        if ok:
            # 未勾選時不置 remember_session,即不下發任何Cookie。
            self.remember_session = bool(payload.get('remember'))
        self.__response_body(
            body=json.dumps(
                {
                    'status': ok,
                    'token': web.token if (ok and web is not None) else ''
                },
                ensure_ascii=False
            ).encode('UTF-8'),
            content_type='application/json; charset=utf-8',
            status=200 if ok else 401
        )

    def __response_session_cookie(self) -> None:
        """下發或清除Cookie。
        登入勾選"30天內免登入"時下發長期Cookie;登出時下發一個立即過期的Cookie以清除它。"""
        web: Union[Web, None] = getattr(self.server, 'web', None)
        if web is None:
            return
        if self.remember_session:
            cookie: str = (
                f'{WebMeta.COOKIE_NAME}={web.token}; '
                f'Max-Age={Web.REMEMBER_COOKIE_MAX_AGE}; Path=/; HttpOnly; SameSite=Lax'
            )
        elif self.expire_session:
            # Max-Age=0 讓瀏覽器立即丟棄該Cookie(HttpOnly 無法由前端 JS 刪除)。
            cookie = f'{WebMeta.COOKIE_NAME}=; Max-Age=0; Path=/; HttpOnly; SameSite=Lax'
        else:
            return
        self.send_header('Set-Cookie', cookie)

    def __response_logout(self) -> None:
        """登出:輪換令牌使所有已下發的Cookie失效,並清除本瀏覽器的Cookie。"""
        web: Union[Web, None] = getattr(self.server, 'web', None)
        if web is not None:
            web.logout()
        self.expire_session = True
        self.__response_body(
            body=json.dumps({'status': True}, ensure_ascii=False).encode('UTF-8'),
            content_type='application/json; charset=utf-8'
        )

    def __response_body(self, body: bytes, content_type: str, status: int = 200) -> None:
        """返回指定內容的響應,status 用於登入失敗時返回401。"""
        self.send_response(status)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Cache-Control', 'no-store')  # 禁用快取,避免瀏覽器沿用舊頁面。
        self.__response_session_cookie()
        self.end_headers()
        self.wfile.write(body)

    def __response_progress(self) -> None:
        """返回進度資料的JSON。"""
        web: Union[Web, None] = getattr(self.server, 'web', None)
        data: dict = web.run_on_loop(web.async_snapshot()) if web else {}
        self.__response_body(
            body=json.dumps(data, ensure_ascii=False).encode('UTF-8'),
            content_type='application/json; charset=utf-8'
        )

    def __response_events(self) -> None:
        web = getattr(self.server, 'web', None)
        if web is None:
            self.__response_json({'status': False, 'e_code': '網頁面板尚未就緒。'}, status=503)
            return
        try:
            cursor = max(0, int(self.headers.get('Last-Event-ID', '0')))
        except ValueError:
            cursor = 0
        self.send_response(200)
        self.send_header('Content-Type', 'text/event-stream; charset=utf-8')
        self.send_header('Cache-Control', 'no-cache, no-transform')
        self.send_header('X-Accel-Buffering', 'no')
        self.end_headers()
        try:
            while True:
                events = web.core.events.read_after(cursor)
                if not events:
                    self.wfile.write(b': keep-alive\n\n')
                    self.wfile.flush()
                    continue
                for item in events:
                    payload = json.dumps(item['data'], ensure_ascii=False)
                    block = (
                        f"id: {item['id']}\nevent: {item['event']}\n"
                        f"data: {payload}\n\n"
                    ).encode('UTF-8')
                    self.wfile.write(block)
                    self.wfile.flush()
                    cursor = item['id']
        except (BrokenPipeError, ConnectionResetError, OSError):
            return

    def __read_json(self) -> dict:
        """讀取請求體中的JSON資料,解析失敗時返回空字典。"""
        try:
            length: int = int(self.headers.get('Content-Length') or 0)
        except (TypeError, ValueError):
            return {}
        if length <= 0:
            return {}
        try:
            return json.loads(self.rfile.read(length).decode('UTF-8'))
        except Exception as e:
            log.debug(f'解析請求資料失敗,{_t(KeyWord.REASON)}:"{e}"')
            return {}

    def __response_remove_listener(self) -> None:
        """處理移除監聽下載與監聽轉發的請求。"""
        web: Union[Web, None] = getattr(self.server, 'web', None)
        payload: dict = self.__read_json()
        if web is None:
            body: dict = {'status': False, 'e_code': '網頁面板未就緒。'}
        else:
            body: dict = web.remove_listener(
                kind=str(payload.get('kind') or ''),
                link=str(payload.get('link') or '')
            )
        self.__response_body(
            body=json.dumps(body, ensure_ascii=False).encode('UTF-8'),
            content_type='application/json; charset=utf-8'
        )

    def __response_admin(self) -> None:
        web: Union[Web, None] = getattr(self.server, 'web', None)
        if web is None:
            self.__response_json({'status': False, 'e_code': '網頁面板尚未就緒。'}, status=503)
            return
        result: dict = web.admin_action(self.path, self.__read_json())
        self.__response_json(result, status=200 if result.get('status') else 400)

    def __response_json(self, data: dict, status: int = 200) -> None:
        self.__response_body(
            body=json.dumps(data, ensure_ascii=False).encode('UTF-8'),
            content_type='application/json; charset=utf-8',
            status=status
        )

    def __response_static(self) -> None:
        """返回網頁模板與靜態目錄下的檔案。"""
        web: Union[Web, None] = getattr(self.server, 'web', None)
        if web is None:
            self.send_error(404)
            return
        name: str = unquote(self.path.split('?')[0].lstrip('/'))
        if not name or name in Web.TEMPLATE_FILES:  # 根路徑返回首頁,登記的模板名稱從模板目錄取。
            root: str = os.path.abspath(web.template_directory)
            file_path: str = os.path.join(root, name or Web.INDEX_FILE)
        else:
            root = os.path.abspath(web.static_directory)
            file_path = os.path.abspath(os.path.join(root, name))
        if os.path.commonpath([root, file_path]) != root:  # 禁止存取網頁目錄之外的檔案。
            self.send_error(403)
            return
        if not os.path.isfile(file_path):
            self.send_error(404)
            return
        body: bytes = b''
        try:
            with open(file=file_path, mode='rb') as f:
                body = f.read()
        except OSError as e:
            log.warning(f'讀取網頁檔案"{file_path}"失敗,{_t(KeyWord.REASON)}:"{e}"')
            self.send_error(404)
            return
        if os.path.basename(file_path) == Web.INDEX_FILE:  # 首頁需要替換標記與版本號。
            # body 在此處已確定賦值(正常路徑來自檔案讀取,異常路徑已在上方 return)。
            # 先取出基準內容到 page,後續替換均基於 page,避免在分支內回頭讀取 try 賦值的 body。
            page: bytes = body  # type: ignore[reportPossiblyUnboundVariable]
            if web and web.username:
                page = WebHandler.replace_body_tag(
                    page,
                    WebHandler.LOGIN_BODY
                )  # 需要認證:首屏即隱藏頁面內容,認證通過後由前端移除該類,避免重新整理時閃現已登入介面。
            page = page.replace(
                WebHandler.VERSION_PLACEHOLDER,
                f'{VERSION_WITH_COMMIT}'.encode('UTF-8')
            )
            page = page.replace(
                WebHandler.PYROGRAM_PLACEHOLDER,
                f'{pyrogram_version}'.encode('UTF-8')
            )
            page = page.replace(  # 注入是否設定機械人,前端據此隱藏上載與監聽側邊欄。
                WebHandler.HAS_BOT_PLACEHOLDER,
                b'1' if (web and web.has_bot) else b'0'
            )
            body = page
        content_type: str = mimetypes.guess_type(file_path)[0] or 'application/octet-stream'
        if content_type.startswith('text/'):
            content_type: str = f'{content_type}; charset=utf-8'
        self.__response_body(body=body, content_type=content_type)


class Web:
    # 網頁面板資源的目錄約定。
    # templates:存放HTML頁面,新增頁面時需在此登記模板名稱以便路由。
    # static:存放靜態資源,按類型分子目錄(css、js、img、fonts、vendor),
    # 頁面裏用相對於站點根的路徑引用,如"css/style.css"。
    TEMPLATE_DIRECTORY: str = os.path.join('module', 'templates')
    STATIC_DIRECTORY: str = os.path.join('module', 'static')
    INDEX_FILE: str = 'index.html'
    TEMPLATE_FILES: tuple = ('index.html',)  # 模板目錄提供的頁面,其餘請求一律按靜態資源處理。
    UNGROUPED: str = '未分組'
    REMOVE_LISTEN_TIMEOUT: int = 10  # 等待事件循環移除監聽的超時時間,單位為秒。
    REMEMBER_COOKIE_MAX_AGE: int = 30 * 24 * 3600  # Cookie的有效期,單位為秒(30天)。
    UNFINISHED_STATE: tuple = (
        DownloadStatus.PENDING,
        DownloadStatus.DOWNLOADING,
        DownloadStatus.PAUSED
    )  # 尚未出結果的訊息狀態。
    LOCAL_IP: str = get_local_ip()

    def __init__(self, progress, app=None, downloader=None):
        self.progress = progress
        self.app = app
        self.downloader = downloader  # 下載器實例,用於讀取已註冊的監聽資訊。
        self.core = AppCore(downloader)
        self.api = WebAPI(self.core)
        self.bot_controller = BotController(self.core)
        # 是否設定了機械人,決定前端是否展示上載與監聽側邊欄(無機械人時只有下載可用)。
        self.has_bot = bool(app and getattr(app, 'bot_token', None))
        self.credential: dict = gen_random_credential()
        self.protocol: str = 'http'
        self.ip: str = PARSE_ARGS.host
        self.port: int = self.get_free_port(PARSE_ARGS.port, self.ip)
        self.username: str = self.credential.get(WebMeta.USERNAME)
        self.password: str = self.credential.get(WebMeta.PASSWORD)
        self.token: str = get_web_session()  # 令牌,使瀏覽器在軟件重啟後依然免密。
        self.template_directory, self.static_directory = self.get_web_directory()
        self.server: Union[ThreadingHTTPServer, None] = None
        self.thread: Union[threading.Thread, None] = None

    @staticmethod
    def __bind_port(port: int, host: str) -> int:
        """綁定指定連接埠,返回實際佔用的連接埠。"""
        # 不設定SO_REUSEADDR,否則Windows下會綁到已被佔用的連接埠,導致連線被其它進程接管。
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            s.bind((host, port))
            return s.getsockname()[1]

    @staticmethod
    def get_free_port(port: int, host: str = '127.0.0.1') -> int:
        """取得可用連接埠,指定連接埠被佔用時自動分配。"""
        try:
            return Web.__bind_port(port, host)
        except OSError as e:
            log.warning(f'無法使用{port}連接埠,已自動分配新的連接埠,{_t(KeyWord.REASON)}:"{e}"')
            return Web.__bind_port(0, host)

    @staticmethod
    def get_web_directory() -> tuple:
        """取得網頁模板目錄與靜態資源目錄,打包環境取資源解壓目錄。"""
        base_directory: str = get_work_directory()
        if is_frozen():
            base_directory = getattr(sys, '_MEIPASS', sys.prefix)  # noqa.
        template_directory: str = os.path.join(base_directory, Web.TEMPLATE_DIRECTORY)
        static_directory: str = os.path.join(base_directory, Web.STATIC_DIRECTORY)
        log.info(f'取得網頁模板目錄:"{template_directory}",靜態資源目錄:"{static_directory}"。')
        return template_directory, static_directory

    @staticmethod
    def format_seconds(seconds: Union[int, float, None]) -> str:
        """將秒數格式化為易於閱讀的剩餘時間。"""
        if seconds is None:
            return ''
        seconds: int = int(seconds)
        if seconds < 60:
            return f'{seconds}秒'
        if seconds < 3600:
            return f'{seconds // 60}分{seconds % 60}秒'
        return f'{seconds // 3600}時{seconds % 3600 // 60}分{seconds % 60}秒'

    def start(self) -> bool:
        """在後台執行緒啟動網頁面板。"""
        for directory in (self.template_directory, self.static_directory):
            if not os.path.isdir(directory):
                log.error(f'網頁面板啟動失敗,未找到網頁目錄:"{directory}"。')
                return False
        try:
            self.server = ThreadingHTTPServer((self.ip, self.port), WebHandler)  # type: ignore[arg-type]
            self.server.daemon_threads = True
        except OSError as e:
            log.error(f'網頁面板啟動失敗,{_t(KeyWord.REASON)}:"{e}"')
            return False
        self.server.web = self
        self.thread = threading.Thread(target=self.server.serve_forever, name='TRMDWeb', daemon=True)
        self.thread.start()
        log.info(f'網頁面板已啟動,連結:"{self.protocol}://{self.ip}:{self.port}"。')
        self.print_meta()
        return True

    def stop(self) -> None:
        """停止網頁面板。"""
        if self.server is None:
            return
        self.server.shutdown()
        self.server.server_close()
        self.core.events.close()
        log.info('網頁面板已停止。')

    def print_meta(self) -> None:
        """列印網頁面板的存取資訊。"""
        PanelTable(
            title='Web設定',
            header=('屬性', '內容'),
            data=[
                [_t(WebMeta.PORT), self.port],
                [_t(WebMeta.USERNAME), self.username],
                [_t(WebMeta.PASSWORD), self.password],
                ['綁定地址', self.ip],
                ['連結', f'{self.protocol}://{self.ip}:{self.port}']
            ],
            show_lines=True
        ).print_meta()

    def check_session(self, token: str) -> bool:
        """校驗瀏覽器提交的令牌是否有效,用於免密登入。"""
        return bool(token) and token == self.token

    def logout(self) -> None:
        """登出:重新生成令牌並持久化,使所有已下發的Cookie失效。"""
        self.token = reset_web_session()

    def get_settings(self) -> dict:
        if self.app is None:
            return {'status': False, 'e_code': '設定管理未就緒。'}
        config: dict = copy.deepcopy(self.app.config)
        secrets: dict = {
            key: bool(config.get(key))
            for key in ('api_hash', 'bot_token')
        }
        config.pop('api_hash', None)
        config.pop('bot_token', None)
        proxy: dict = config.get('proxy') or {}
        secrets['proxy_password'] = bool(proxy.get('password'))
        proxy.pop('password', None)
        return {'status': True, 'config': config, 'secrets': secrets}

    def get_service_status(self) -> dict:
        downloader = self.downloader
        if downloader is None:
            return {'status': False, 'e_code': '服務狀態無法取得。'}
        try:
            on_downloader_loop: bool = asyncio.get_running_loop() is downloader.loop
        except RuntimeError:
            on_downloader_loop = False
        status: dict = (
            downloader.web_service_status_snapshot()
            if on_downloader_loop else self.run_on_loop(downloader.web_get_service_status())
        )
        status.update({'bind_address': self.ip, 'port': self.port})
        return status

    def admin_action(self, path: str, payload: dict) -> dict:
        if not isinstance(payload, dict):
            return {'status': False, 'e_code': '管理操作資料格式無效。'}
        if path == '/api/admin/settings':
            return self.update_settings(payload.get('settings'))
        if path.startswith('/api/admin/config'):
            return self.run_on_loop(self.api.post('/api/admin/config', payload))
        if path.startswith('/api/admin/download/reorder'):
            return self.run_on_loop(self.api.post('/api/admin/download/reorder', payload))
        if path.startswith('/api/admin/forward'):
            return self.run_on_loop(self.api.post('/api/admin/forward', payload))
        if path == '/api/admin/download/add':
            if self.downloader is None:
                return {'status': False, 'e_code': '下載器未就緒。'}
            return self.run_on_loop(self.core.add_download(str(payload.get('link') or '')))
        if path == '/api/admin/download/control':
            if self.downloader is None:
                return {'status': False, 'e_code': '下載器未就緒。'}
            try:
                message_id: int = int(payload.get('message_id'))
            except (TypeError, ValueError):
                return {'status': False, 'e_code': '下載訊息編號無效。'}
            return self.run_on_loop(self.core.control_download(
                link=str(payload.get('link') or ''),
                message_id=message_id,
                action=str(payload.get('action') or '')
            ))
        if path == '/api/admin/upload/control':
            if self.downloader is None or self.downloader.uploader is None:
                return {'status': False, 'e_code': '上載服務尚未啟用。'}
            return self.run_on_loop(self.downloader.uploader.web_control_task(
                task_id=str(payload.get('task_id') or ''),
                action=str(payload.get('action') or '')
            ))
        if path == '/api/admin/service/shutdown':
            if self.downloader is None:
                return {'status': False, 'e_code': '下載器未就緒。'}
            return self.run_on_loop(self.downloader.web_request_shutdown())
        if path == '/api/admin/service/reconnect':
            if self.downloader is None:
                return {'status': False, 'e_code': '下載器未就緒。'}
            return self.run_on_loop(self.downloader.web_reconnect_bot())
        return {'status': False, 'e_code': '未知的管理操作。'}

    def run_on_loop(self, coroutine) -> dict:
        loop: Union[AbstractEventLoop, None] = getattr(self.downloader, 'loop', None)
        if loop is None or not loop.is_running():
            coroutine.close()
            return {'status': False, 'e_code': '下載器事件迴圈未執行。'}
        future = asyncio.run_coroutine_threadsafe(coroutine, loop)
        try:
            return future.result(timeout=30)
        except FutureTimeoutError:
            future.cancel()
            log.warning('網頁管理操作逾時。')
            return {'status': False, 'e_code': '操作逾時，請稍後確認狀態。'}
        except Exception as e:
            log.exception(f'網頁管理操作失敗:"{e}"')
            return {'status': False, 'e_code': str(e)}

    def update_settings(self, settings: dict) -> dict:
        if self.app is None or not isinstance(settings, dict):
            return {'status': False, 'e_code': '設定資料格式無效。'}
        allowed: set = set(self.app.config)
        unexpected: set = set(settings) - allowed
        if unexpected:
            return {'status': False, 'e_code': f'不支援的設定欄位:{", ".join(sorted(unexpected))}'}

        updated: dict = copy.deepcopy(self.app.config)
        for key, value in settings.items():
            if key in ('max_tasks', 'max_retries', 'proxy'):
                if not isinstance(value, dict):
                    return {'status': False, 'e_code': f'設定「{key}」必須是物件。'}
                current: dict = updated.get(key) or {}
                unknown: set = set(value) - set(current)
                if unknown:
                    return {'status': False, 'e_code': f'設定「{key}」包含不支援欄位。'}
                current.update(value)
                updated[key] = current
            else:
                updated[key] = value

        for secret in ('api_hash', 'bot_token'):
            if secret in settings and not settings[secret]:
                updated[secret] = self.app.config.get(secret)
        if 'proxy' in settings and 'password' in settings['proxy'] and not settings['proxy']['password']:
            updated['proxy']['password'] = (self.app.config.get('proxy') or {}).get('password')

        error: Union[str, None] = self.validate_settings(updated)
        if error:
            return {'status': False, 'e_code': error}

        restart_fields: tuple = ('api_id', 'api_hash', 'bot_token', 'session_directory', 'proxy', 'links')
        restart_required: list = [key for key in restart_fields if updated.get(key) != self.app.config.get(key)]
        path: str = self.app.config_path
        directory: str = os.path.dirname(os.path.abspath(path))
        temporary_path: Union[str, None] = None
        try:
            fd, temporary_path = tempfile.mkstemp(prefix='.trmd-config-', suffix='.yaml', dir=directory)
            with os.fdopen(fd, 'w', encoding='UTF-8') as stream:
                yaml.safe_dump(updated, stream, allow_unicode=True, sort_keys=False)
            os.replace(temporary_path, path)
        except (OSError, yaml.YAMLError) as e:
            if temporary_path and os.path.exists(temporary_path):
                try:
                    os.unlink(temporary_path)
                except OSError as cleanup_error:
                    log.warning(f'清理暫存設定檔失敗:"{cleanup_error}"')
            log.error(f'儲存 Web 設定失敗:"{e}"')
            return {'status': False, 'e_code': f'儲存設定失敗：{e}'}

        self.app.config = updated
        self.app.save_directory = updated['save_directory']
        self.app.temp_directory = updated['temp_directory']
        self.app.max_download_task = updated['max_tasks']['download']
        self.app.max_upload_task = updated['max_tasks']['upload']
        self.app.max_download_retries = updated['max_retries']['download']
        self.app.max_upload_retries = updated['max_retries']['upload']
        self.app.download_type = updated['download_type']
        if self.downloader and self.downloader.uploader:
            self.downloader.uploader.max_upload_task = self.app.max_upload_task
            self.downloader.uploader.max_upload_retries = self.app.max_upload_retries
        return {'status': True, 'restart_required': restart_required}

    @staticmethod
    def validate_settings(config: dict) -> Union[str, None]:
        for key in ('api_hash', 'bot_token', 'links', 'save_directory', 'temp_directory', 'session_directory'):
            value = config.get(key)
            if value is not None and not isinstance(value, str):
                return f'設定「{key}」必須是文字。'
        if not config.get('save_directory'):
            return '下載目錄不可為空。'
        if type(config.get('api_id')) not in (int, type(None)) or (
            config.get('api_id') is not None and config['api_id'] <= 0
        ):
            return 'API ID 必須是整數。'
        if not isinstance(config.get('download_type'), list) or not config['download_type']:
            return '至少要選擇一種下載媒體類型。'
        if any(dtype not in list(DownloadType()) for dtype in config['download_type']):
            return '下載媒體類型包含不支援的值。'
        for parent in ('max_tasks', 'max_retries'):
            values: dict = config.get(parent)
            if not isinstance(values, dict) or set(values) != {'download', 'upload'}:
                return f'設定「{parent}」格式無效。'
            lower: int = 1 if parent == 'max_tasks' else 0
            if any(type(value) is not int or not lower <= value <= 64 for value in values.values()):
                return f'設定「{parent}」數值超出允許範圍。'
        if type(config.get('is_shutdown')) is not bool:
            return '自動關機設定必須是布林值。'
        proxy: dict = config.get('proxy')
        if not isinstance(proxy, dict) or set(proxy) != {
            'enable_proxy', 'scheme', 'hostname', 'port', 'username', 'password'
        }:
            return '代理伺服器設定格式無效。'
        if type(proxy['enable_proxy']) is not bool:
            return '代理伺服器啟用設定必須是布林值。'
        if any(
            proxy[key] is not None and not isinstance(proxy[key], str)
            for key in ('scheme', 'hostname', 'username', 'password')
        ):
            return '代理伺服器欄位必須是文字。'
        if proxy['port'] is not None and (
            type(proxy['port']) is not int or not 1 <= proxy['port'] <= 65535
        ):
            return '代理伺服器連接埠必須介於 1 至 65535。'
        if proxy['enable_proxy'] and not all(proxy.get(key) for key in ('scheme', 'hostname', 'port')):
            return '啟用代理伺服器時，類型、主機與連接埠皆不可為空。'
        return None

    @staticmethod
    def get_outer_links() -> dict:
        """讀取頂欄選單使用的外部連結,遠端設定缺失時回退到內置預設值。"""
        config: dict = rc.cached_config()
        return {
            'github': config.get('github', rc.DEFAULT_GITHUB) + '/releases',
            'subscribe_channel': config.get('subscribe_channel', rc.DEFAULT_SUBSCRIBE_CHANNEL),
            'video_tutorial': config.get('video_tutorial', rc.DEFAULT_VIDEO_TUTORIAL)
        }

    def get_count(self) -> dict:
        """聚合下載任務的成功、失敗、跳過數量。"""
        count: dict = {'success': 0, 'failure': 0, 'skip': 0}
        if self.app is None:
            return count
        for name, value in list(vars(self.app).items()):
            if not isinstance(value, set):
                continue
            if name.startswith('success_'):
                count['success'] += len(value)
            elif name.startswith('failure_'):
                count['failure'] += len(value)
            elif name.startswith('skip_'):
                count['skip'] += len(value)
        return count

    def get_link_progress(self) -> list:
        """取得每個下載連結的進度與該連結下所有訊息成員(含已完成、跳過、失敗)。"""
        result: list = []
        try:
            for link, task in list(DownloadTask.TASKS.items()):
                member_num: int = int(task.member_num or 0)
                complete_num: int = int(task.complete_num or 0)
                fail_num: int = int(task.fail_num or 0)
                members: list = self.get_members(task=task)
                cancelled_num: int = sum(
                    1 for member in members if member.get('state') == DownloadStatus.CANCELLED
                )
                unfinished: int = len(
                    [i for i in members if i.get('state') in Web.UNFINISHED_STATE]
                )
                base_num: int = max(member_num - fail_num - cancelled_num, 0)
                result.append({
                    'link': str(link),
                    'channel': str(task.chat_id or ''),
                    'channel_name': Web.format_channel(str(task.chat_id or '')),
                    'complete': complete_num,
                    'member': member_num,
                    'failed': fail_num,
                    'cancelled': cancelled_num,
                    'remaining': max(member_num - complete_num - fail_num - cancelled_num, 0),
                    'queue': members,
                    'queue_total': unfinished,
                    'total': len(members),
                    'percent': round(complete_num / base_num * 100, 1) if base_num else 0.0
                })
        except Exception as e:
            log.debug(f'取得連結進度時出錯,{_t(KeyWord.REASON)}:"{e}"')
        return result

    def get_members(self, task: DownloadTask) -> list:
        """取得連結下所有訊息成員的展示資訊。

        仍在佇列中的訊息可以取到原始訊息,用於補全檔案名稱與大小;
        已完成或失敗的訊息已被移出佇列,使用登記時儲存的資訊。
        """
        result: list = []
        for message_id, member in list(task.member_info.items()):
            item: dict = task.items.get(message_id) or {}
            meta: dict = self.format_queue_message(item, member.get('state')) if item else {}
            result.append({
                'name': member.get('name') or meta.get('name') or f'訊息 {message_id}',
                'size': member.get('size') or meta.get('size') or '',
                'size_byte': int(member.get('size_byte') or 0),
                'date': member.get('date') or meta.get('date') or '',
                'state': member.get('state') or DownloadStatus.PENDING,
                'message_id': message_id,
                'pause_requested': bool(item.get('pause_requested', False)),
                'cancel_requested': bool(item.get('cancel_requested', False)),
                'task_id': member.get('task_id'),
                'note': member.get('note') or ''
            })
        return result

    def format_queue_message(self, item: dict, state: Union[str, None] = None) -> dict:
        """解析排隊訊息的展示資訊,首次解析後快取,避免每次輪詢重複解析。"""
        meta: Union[dict, None] = item.get('meta')
        if meta is None:
            meta = self.parse_queue_message(item)
            item['meta'] = meta
        meta['state'] = str(state or '')  # 排隊狀態會變化,不寫入快取。
        return meta

    def parse_queue_message(self, item: dict) -> dict:
        """解析排隊訊息的名稱、大小與日期。"""
        message = item.get('message')
        result: dict = {'name': '訊息 ' + str(getattr(message, 'id', '')), 'size': '', 'date': ''}
        try:
            result['date'] = str(getattr(message, 'date', '') or '')[:10]
            if self.app is None:
                return result
            dtype: Union[str, None] = get_message_dtype(message, self.app.download_type)
            if dtype:
                result['name'] = str(split_path(self.app.get_temp_file_path(message, dtype)).get('file_name'))
                result['size'] = MetaData.suitable_units_display(getattr(getattr(message, dtype), 'file_size', 0))
        except Exception as e:
            log.debug(f'解析排隊訊息時出錯,{_t(KeyWord.REASON)}:"{e}"')
        return result

    def get_listeners(self) -> dict:
        """取得已註冊的監聽下載與監聽轉發資訊。

        Returns:
            dict: download為監聽下載的頻道連結;forward為監聽轉發的監聽頻道與轉發頻道。
        """
        result: dict = {'download': [], 'forward': []}
        if self.downloader is None:
            return result
        try:
            result['download'] = [str(link) for link in list(self.downloader.listen_download_chat)]
            for rule in list(self.downloader.listen_forward_chat):
                args: list = str(rule).split()
                if len(args) != 2:
                    continue  # 轉發規則固定為"監聽頻道 轉發頻道"兩段,異常規則直接跳過。
                result['forward'].append({'source': args[0], 'target': args[1]})
        except Exception as e:
            log.debug(f'取得監聽資訊時出錯,{_t(KeyWord.REASON)}:"{e}"')
        return result

    def remove_listener(self, kind: str, link: str) -> dict:
        """按網頁面板的請求移除已註冊的監聽下載或監聽轉發。

        移除動作需要在下載器的事件循環中執行,才能安全地讓用戶端向機械人發送命令,
        而網頁面板執行在獨立的HTTP服務執行緒中,因此把協程投遞到事件循環並等待結果。

        Args:
            kind: 監聽類型,`download`為監聽下載,`forward`為監聽轉發。
            link: 監聽下載為頻道連結;監聽轉發為"監聽頻道 轉發頻道"。

        Returns:
            dict: status為是否移除成功,失敗時e_code為失敗原因。
        """
        if self.downloader is None:
            return {'status': False, 'e_code': '網頁面板未關聯下載器。'}
        loop: Union[AbstractEventLoop, None] = self.downloader.loop
        if loop is None or not loop.is_running():
            return {'status': False, 'e_code': '下載器未執行,無法移除監聽。'}
        future = asyncio.run_coroutine_threadsafe(
            self.downloader.cancel_listen_from_web(kind=kind, link=link),
            loop
        )
        try:
            return future.result(timeout=Web.REMOVE_LISTEN_TIMEOUT)
        except Exception as e:
            log.debug(f'移除監聽失敗,{_t(KeyWord.REASON)}:"{e}"')
            return {'status': False, 'e_code': '移除監聽超時,請稍後重試。'}

    def get_upload_tasks(self, tasks: Union[list, None] = None) -> list:
        """取得上載任務的概要資訊,並按進度列任務ID補全上載進度。"""
        result: list = []
        live: dict = {}
        for item in tasks if tasks is not None else self.get_tasks():
            live[item.get('id')] = item
        try:
            for task in list(UploadTask.TASKS):
                status = getattr(task.status, 'value', task.status)
                done: bool = status in (UploadStatus.SUCCESS, UploadStatus.SENT)
                progress: dict = live.get(getattr(task, 'task_id', None)) or {}
                size: str = MetaData.suitable_units_display(task.file_size)
                info: str = progress.get('info', '')
                if not info and done:
                    info = f'{size}/{size}'  # 進度列任務已在完成時移除,用檔案自身大小回填。
                result.append({
                    'control_id': task.control_id,
                    'file': task.file_name,
                    'path': task.file_path,
                    'chat': Web.format_channel(str(task.chat_id)) if task.chat_id else Web.UNGROUPED,
                    'channel': str(task.chat_id) if task.chat_id else Web.UNGROUPED,
                    'size': size,
                    'size_byte': int(task.file_size),
                    'status': _t(str(status)),
                    'state': str(status),  # 原始狀態,供網頁面板區分上載中、已完成、失敗。
                    'pause_requested': bool(getattr(task, 'pause_requested', False)),
                    'cancel_requested': bool(getattr(task, 'cancel_requested', False)),
                    'task_id': getattr(task, 'task_id', None),
                    'completed': progress.get('completed', task.file_size if done else 0),
                    'percent': progress.get('percent', 100.0 if done else 0.0),
                    'info': info,
                    'speed': progress.get('speed', ''),
                    'speed_value': progress.get('speed_value', 0),
                    'remaining': progress.get('remaining', ''),
                    'error': task.error_msg if task.error_msg else ''
                })
        except Exception as e:
            log.debug(f'取得上載任務時出錯,{_t(KeyWord.REASON)}:"{e}"')
        return result

    @staticmethod
    def get_summary(links: list, tasks: list) -> dict:
        """彙總所有任務的總體進度。

        總量取未失敗成員的位元組之和(包含排隊、已完成、跳過),
        而不是隻統計正在下載的任務,避免總進度隨着任務開始下載而不斷變大;
        徹底失敗(重試耗盡)的成員不再計入總量,避免進度被永久拉低。

        Args:
            links: get_link_progress返回的連結進度。
            tasks: 進度列中正在下載的任務。

        Returns:
            dict: 總體進度。
        """
        live: dict = {task.get('id'): task for task in tasks}
        completed: int = 0
        total: int = 0
        speed: float = 0.0
        for link in links:
            for member in link.get('queue') or []:
                state: str = str(member.get('state') or '')
                note: str = str(member.get('note') or '')
                if state == DownloadStatus.FAILURE:
                    continue  # 徹底失敗的成員不再計入總量與速度,避免進度被拉低或無法歸零。
                if state == DownloadStatus.CANCELLED:
                    continue
                if state == DownloadStatus.SKIP and note:
                    continue  # 不支援或被忽略的類型(已取消)的跳過成員不再計入總量,因為它們本就不會被下載;檔案已存在(已下載)的跳過不帶note,仍計入總量。
                size: int = int(member.get('size_byte') or 0)
                total += size
                if state in (DownloadStatus.SUCCESS, DownloadStatus.SKIP):
                    completed += size
                    continue
                if state == DownloadStatus.DOWNLOADING:
                    completed += int(live.get(member.get('task_id'), {}).get('completed') or 0)
        for task in tasks:
            speed += task.get('speed_value', 0)
        remaining: Union[float, None] = None
        if speed and total > completed:
            remaining: Union[float, None] = (total - completed) / speed
        return {
            'completed': completed,
            'total': total,
            'percent': round(completed / total * 100, 1) if total else 0.0,
            'info': f'{MetaData.suitable_units_display(completed)}/{MetaData.suitable_units_display(total)}',
            'speed': f'{MetaData.suitable_units_display(speed)}/s' if speed else '',
            'remaining': Web.format_seconds(remaining)
        }

    @staticmethod
    def format_channel(channel: str) -> str:
        """格式化頻道的顯示名稱,有標題時顯示為"標題(ID)"。"""
        if not channel or channel == Web.UNGROUPED:
            return Web.UNGROUPED
        title: str = ChatInfo.get(channel)
        return f'{title}({channel})' if title else channel

    def get_tasks(self) -> list:
        """讀取進度列中正在下載的任務。"""
        tasks: list = []
        for task in self.progress.tasks:
            item: dict = {
                'id': task.id,
                'type': str(task.description),
                'channel': str(task.fields.get('channel', '')) or Web.UNGROUPED,
                'channel_name': Web.format_channel(str(task.fields.get('channel', ''))),
                # 優先使用完整檔案名稱;filename是按終端機寬度截斷的終端機顯示名,僅在缺少完整名時兜底。
                'filename': str(task.fields.get('fullname') or task.fields.get('filename', '')),
                'info': str(task.fields.get('info', '')),
                'completed': int(task.completed),
                'total': int(task.total) if task.total else 0,
                'percent': round(task.percentage, 1),
                'speed': f'{MetaData.suitable_units_display(task.speed)}/s' if task.speed else '',
                'speed_value': task.speed if task.speed else 0,
                'remaining': self.format_seconds(task.time_remaining)
            }
            tasks.append(item)
        return tasks

    def snapshot(self) -> dict:
        """生成供網頁面板展示的進度資料。"""
        try:
            all_tasks: list = self.get_tasks()
            uploads: list = self.get_upload_tasks(tasks=all_tasks)
            upload_ids: set = {item.get('task_id') for item in uploads if item.get('task_id') is not None}
            tasks: list = [item for item in all_tasks if item.get('id') not in upload_ids]  # 上載進度列任務不納入下載統計。
            links: list = self.get_link_progress()
            return {
                'count': self.get_count(),
                'summary': self.get_summary(links=links, tasks=tasks),
                'queue': sum(link.get('remaining', 0) for link in links),  # 所有連結待下載的訊息總數。
                'tasks': tasks,
                'links': links,
                'uploads': uploads,
                'listeners': self.get_listeners(),
                'service': self.get_service_status(),
                'outer_links': self.get_outer_links()  # 頂欄選單使用的外部連結。
            }
        except Exception as e:
            log.debug(f'生成進度資料時出錯,{_t(KeyWord.REASON)}:"{e}"')
            return {
                'count': {'success': 0, 'failure': 0, 'skip': 0},
                'summary': self.get_summary(links=[], tasks=[]),
                'queue': 0,
                'tasks': [],
                'links': [],
                'uploads': [],
                'listeners': {'download': [], 'forward': []},
                'service': self.get_service_status(),
                'outer_links': self.get_outer_links()
            }

    async def async_snapshot(self) -> dict:
        return self.snapshot()
