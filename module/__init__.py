# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2023/11/18 12:28:18
# File:__init__.py
import os
import sys
import atexit
import logging
import platform

from logging.handlers import RotatingFileHandler

import yaml

from rich.console import Console
from rich.logging import RichHandler


def read_input_history(history_path: str, max_record_len: int, **kwargs) -> None:
    if kwargs.get('platform') == 'Windows':
        # 嘗試讀取歷史記錄檔案。
        import readline
        readline.backend = 'readline'
        try:
            readline.read_history_file(history_path)
        except FileNotFoundError:
            pass
        # 設定歷史記錄的最大長度。
        readline.set_history_length(max_record_len)
        # 註冊退出時儲存歷史記錄。
        atexit.register(readline.write_history_file, history_path)


def via_log_level(log_level: str, param_name: str, default_level: int = logging.INFO) -> bool:
    if log_level not in ['CRITICAL', 'FATAL', 'ERROR', 'WARN', 'WARNING', 'INFO', 'DEBUG', 'NOTSET']:
        with open(file=GLOBAL_CONFIG_PATH, mode='w', encoding='UTF-8') as file:
            global_config[param_name] = logging.getLevelName(default_level)
            yaml.dump(global_config, file)
        return False
    return True


class CustomDumper(yaml.Dumper):

    def represent_none(self, data):
        """自訂將yaml檔案中None表示為~。"""
        return self.represent_scalar('tag:yaml.org,2002:null', '~')


class CallerFilter(logging.Filter):
    PROJECT_PATH = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    """為日誌記錄補充上層調用者資訊,格式為"模塊名.函數名"。"""

    def filter(self, record: logging.LogRecord) -> bool:
        frame = sys._getframe(1)
        # 回溯到實際調用日誌的幀(record的pathname與lineno即為其位置)。
        while frame is not None:
            if frame.f_code.co_filename == record.pathname and frame.f_lineno == record.lineno:
                break
            frame = frame.f_back
        caller_frame = frame.f_back if frame is not None else None
        if caller_frame is None:
            record.caller_name = '-'
            return True
        func_name: str = caller_frame.f_code.co_name
        # 項目內的調用者顯示完整模塊名,第三方與標準庫僅顯示函數名,避免名稱過長導致換行。
        if caller_frame.f_code.co_filename.startswith(CallerFilter.PROJECT_PATH):
            record.caller_name = f'{caller_frame.f_globals.get("__name__", "")}.{func_name}'
        else:
            record.caller_name = func_name
        return True


LOG_TIME_FORMAT = '[%Y-%m-%d %H:%M:%S]'
console = Console(log_path=False, log_time_format=LOG_TIME_FORMAT)
FORWARD_LIMIT = 33  # 每分鐘允許的最大轉發次數。
SLEEP_THRESHOLD = 60
AUTHOR = 'Gentlesprite'
__version__ = '2.0.9'
__license__ = 'GPL-3.0-or-later'
__update_date__ = '2026/10/06 12:51:07'
__copyright__ = f'Copyright (C) 2024-{__update_date__[:4]} {AUTHOR} <https://github.com/{AUTHOR}>'
SOFTWARE_FULL_NAME = 'Telegram Restricted Media Downloader'
SOFTWARE_SHORT_NAME = 'TRMD'
APPDATA_PATH = os.path.join(
    os.environ.get('APPDATA') or os.environ.get('XDG_CONFIG_HOME', os.path.expanduser('~/.config')),
    SOFTWARE_SHORT_NAME)
GLOBAL_CONFIG_NAME = '.CONFIG.yaml'
GLOBAL_CONFIG_PATH = os.path.join(APPDATA_PATH, GLOBAL_CONFIG_NAME)
PLATFORM = platform.system()
os.makedirs(APPDATA_PATH, exist_ok=True)  # v1.2.6修復初次執行開啟報錯問題。
INPUT_HISTORY_PATH = os.path.join(APPDATA_PATH, f'.{SOFTWARE_SHORT_NAME}_HISTORY')
MAX_RECORD_LENGTH = 1000
read_input_history(history_path=INPUT_HISTORY_PATH, max_record_len=MAX_RECORD_LENGTH, platform=PLATFORM)
LOG_PATH = os.path.join(APPDATA_PATH, f'{SOFTWARE_SHORT_NAME}_LOG.log')
MAX_LOG_SIZE = 200 * 1024 * 1024  # 200MB
BACKUP_COUNT = 0  # 不保留日誌檔案。
LOG_FORMAT = '%(name)s:%(caller_name)s:%(funcName)s:%(lineno)d - %(message)s'
FILE_LOG_LEVEL: int = logging.INFO
CONSOLE_LOG_LEVEL: int = logging.WARNING
REFERRAL_RECORD_PATH: str = os.path.join(APPDATA_PATH, f'.{SOFTWARE_SHORT_NAME}_REFERRAL')
TRMD_WEB_SESSION: str = os.path.join(APPDATA_PATH, f'.{SOFTWARE_SHORT_NAME}_WEB_SESSION')
# 設定日誌檔案處理器(檔案記錄)
file_handler = RotatingFileHandler(
    filename=LOG_PATH,
    maxBytes=MAX_LOG_SIZE,
    backupCount=BACKUP_COUNT,
    encoding='UTF-8'
)
file_handler.setFormatter(logging.Formatter('%(asctime)s %(levelname)-8s' + ' ' + LOG_FORMAT, datefmt=LOG_TIME_FORMAT))

if os.path.exists(GLOBAL_CONFIG_PATH):
    try:
        with open(file=GLOBAL_CONFIG_PATH, mode='r', encoding='UTF-8') as f:
            global_config = yaml.safe_load(f)
        file_log_level: str = global_config.get('file_log_level')
        console_log_level: str = global_config.get('console_log_level')
        if via_log_level(log_level=file_log_level, param_name='file_log_level', default_level=logging.INFO):
            FILE_LOG_LEVEL: int = logging.getLevelName(file_log_level)
        if via_log_level(log_level=console_log_level, param_name='console_log_level', default_level=logging.WARNING):
            CONSOLE_LOG_LEVEL: int = logging.getLevelName(console_log_level)
    except Exception:  # noqa.
        pass

file_handler.setLevel(logging.getLevelName(FILE_LOG_LEVEL))
file_handler.addFilter(CallerFilter())
# 設定日誌終端機記錄器(控制枱輸出)
console_handler = RichHandler(
    level=CONSOLE_LOG_LEVEL,  # 控制枱只顯示WARNING及以上級別。
    console=console,
    rich_tracebacks=True,
    show_path=False,
    omit_repeated_times=True,
    log_time_format=LOG_TIME_FORMAT
)
console_handler.addFilter(CallerFilter())
# 設定日誌記錄器(根記錄器設定為最低級別 DEBUG)
logging.basicConfig(
    level=logging.DEBUG,  # 根記錄器設定為DEBUG,允許所有日誌通過。
    format=LOG_FORMAT,
    datefmt=LOG_TIME_FORMAT,
    handlers=[
        console_handler,  # 控制枱:WARNING+
        file_handler  # 檔案:INFO+
    ]
)
log = logging.getLogger('rich')


def get_commit_hash():
    env_commit = os.environ.get('TRMD_COMMIT_HASH')
    if env_commit:
        log.debug(f'通過環境變量TRMD_COMMIT_HASH取得commit hash:{env_commit}。')
        return env_commit
    repo_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    if os.path.isdir(os.path.join(repo_root, '.git')):
        try:
            import subprocess
            completed = subprocess.run(
                ['git', 'rev-parse', '--short', 'HEAD'],
                cwd=repo_root,
                capture_output=True,
                text=True
            )
            if completed.returncode == 0 and completed.stdout.strip():
                commit_hash: str = completed.stdout.strip()
                log.debug(f'通過git取得commit hash:{commit_hash}。')
                return commit_hash
        except Exception as e:
            log.debug(f'無法取得commit hash,原因:"{e}"')
    return None


def get_build_time():
    env_build_time = os.environ.get('TRMD_BUILD_TIME')
    if env_build_time:
        log.debug(f'通過環境變量TRMD_BUILD_TIME取得build time:{env_build_time}。')
        return env_build_time
    return None


COMMIT = get_commit_hash()
BUILD_TIME = get_build_time()
BUILD_META: str = '.'.join(part for part in (COMMIT, BUILD_TIME) if part)
VERSION_SEMVER = f'{__version__}+{BUILD_META}' if BUILD_META else __version__
VERSION_WITH_COMMIT = f'{__version__}+{COMMIT}' if COMMIT else __version__
CustomDumper.add_representer(type(None), CustomDumper.represent_none)  # noqa.
README = r'''
```yaml
api_hash: xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx # 申請的api_hash。
api_id: 'xxxxxxxx' # 申請的api_id。
# bot_token（選填）如果不填，就不能使用機械人功能。可前往https://t.me/BotFather免費申請。
bot_token: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11
download_type: # 需要下載的類型。支援的參數:video,photo,document,audio,voice,animation。
- video # 影片。
- photo # 圖片。
- document # 檔案。
- audio # 音訊。
- voice # 語音。
- animation # GIF。
- video_note # 影片筆記。
- live_photo # 實況圖片（當不指定時，並且photo類型存在的情況下，live_photo類型將被視為photo類型）。
is_shutdown: true # 下載完成後是否自動關機。支援的參數：true,false。
links: D:\path\where\your\link\files\save\content.txt # 連結地址寫法如下:
# 新建txt文字，一個連結為一行，將路徑填入即可請不要加引號，在軟件執行前就準備好。
# D:\path\where\your\link\txt\save\content.txt 一個連結一行。
max_retries:
  download: 5 # 最大的下載任務的重試次數。
  upload: 3 # 最大的上載任務的重試次數。
max_tasks:
  download: 5 # 最大同時下載的任務數。
  upload: 3 # 最大同時上載的任務數。
proxy: # 代理部分，如不使用請全部填null注意冒號後面有空格，否則不生效導致報錯。
  enable_proxy: true # 是否開啟代理。支援的參數：true,false。
  hostname: 127.0.0.1 # 代理的ip地址。
  scheme: socks5 # 代理的類型。支援的參數：http,socks4,socks5。
  port: 10808 # 代理ip的連接埠。支援的參數：0~65535。
  username: null # 代理的帳號，沒有就填null。
  password: null # 代理的密碼，沒有就填null。
save_directory: F:\directory\media\where\you\save # 下載的媒體儲存的目錄（支援通配符）。
session_directory: F:\directory\session\where\you\save # 會話的儲存目錄（支援通配符）。
temp_directory: F:\directory\temp\where\you\save # 快取儲存的目錄（支援通配符）。
```
'''
