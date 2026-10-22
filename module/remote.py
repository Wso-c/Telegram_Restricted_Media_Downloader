# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026/9/7 00:00:00
# File:remote.py
import os
import json
import time
import asyncio

from functools import partial
from urllib.request import (
    Request,
    urlopen
)

from module import (
    log,
    AUTHOR,
    __version__,
    APPDATA_PATH,
    SOFTWARE_SHORT_NAME
)


class RemoteConfig(object):
    """遠端設定,負責遠端設定的取得、校驗、快取與解析。"""

    BRANCH: str = 'main'
    URLS: tuple = (
        f'https://cdn.jsdelivr.net/gh/{AUTHOR}/{SOFTWARE_SHORT_NAME}_CONFIG@{BRANCH}/config.json',
        f'https://fastly.jsdelivr.net/gh/{AUTHOR}/{SOFTWARE_SHORT_NAME}_CONFIG@{BRANCH}/config.json',
    )
    HEADERS: dict = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) '
                      'Chrome/124.0.0.0 Safari/537.36'
    }
    TIMEOUT: int = 8  # 單個遠端地址的請求超時(秒)。
    TTL: int = 24 * 3600  # 本機快取的有效期,同時作為遠端取得失敗後的重試間隔(秒)。
    PATH: str = os.path.join(APPDATA_PATH, '.REMOTE_CONFIG')
    DEFAULT_VERSION: str = __version__
    DEFAULT_REFERRAL: str = ''
    DEFAULT_VIDEO_TUTORIAL: str = 'https://www.youtube.com/watch?v=ucwKJu-MrBw'
    DEFAULT_SUBSCRIBE_CHANNEL: str = 'https://t.me/RestrictedMediaDownloader'
    DEFAULT_GITHUB: str = 'https://github.com/Gentlesprite/Telegram_Restricted_Media_Downloader'
    CONFIG: dict = {
        'version': (DEFAULT_VERSION, str),
        'referral': (DEFAULT_REFERRAL, str),
        'video_tutorial': (DEFAULT_VIDEO_TUTORIAL, str),
        'subscribe_channel': (DEFAULT_SUBSCRIBE_CHANNEL, str),
        'github': (DEFAULT_GITHUB, str)
    }

    def default_config(self) -> dict:
        """按字段表生成一份內置預設設定,字段缺失或類型不符時都使用它。"""
        return {name: field[0] for name, field in self.CONFIG.items()}

    def verify(self, remote: dict) -> dict:
        """按字段表校驗設定並補充缺失字段,忽略未知字段,保證新舊版本設定互相相容。"""
        config: dict = {}
        for name, field in self.CONFIG.items():
            default, expected_type = field
            value = remote.get(name, default)
            # 字段缺失或類型不符時都退回預設值,避免單個髒字段導致整份設定失效。
            if not isinstance(value, expected_type):
                log.info(f'Unexpected field value: "{name}={value}", using default: "{default}"')
                value = default
            config[name] = value
        return config

    async def read(self) -> dict:
        """讀取設定,快取未過期時直接使用,否則請求遠端,失敗時回退到快取或內置預設值。"""
        default: dict = self.default_config()
        # 遠端設定不可用時退回本機快取,保證離線仍能使用上次的可用設定。
        cached: dict = self.cached_config()
        if cached:
            try:
                # 快取檔案在讀取後被刪除時視為已過期,直接請求遠端。
                remaining: float = self.TTL - (time.time() - os.path.getmtime(self.PATH))
            except OSError:
                remaining: float = 0
            if remaining > 0:
                log.info(f'Using cached remote config from "{self.PATH}", '
                         f'remaining valid time: {remaining / 3600:.1f} hours')
                return cached
        config: dict = await self.fetch()
        self.save(config or cached or default)  # 無論取得成功與否都寫入一次,以重新整理修改時間,避免遠端不可用時反覆重試。
        return config or cached or default

    def save(self, config: dict) -> None:
        """把設定寫入快取檔案,檔案的修改時間即為快取的生效時刻。"""
        try:
            with open(file=self.PATH, mode='w', encoding='UTF-8') as f:
                json.dump(config, f)
            log.info(f'Remote config cached successfully: {config}')
        except OSError as e:
            log.info(f'Failed to write to the remote config cache due to {e}')

    async def fetch(self) -> dict:
        """依次嘗試各個遠端地址取得設定,全部失敗時返回空字典。"""
        loop = asyncio.get_running_loop()
        for url in self.URLS:
            try:
                log.info(f'Getting remote config from "{url}".')
                request = Request(url=url, headers=self.HEADERS)
                response = await asyncio.wait_for(
                    loop.run_in_executor(None, partial(urlopen, request, timeout=self.TIMEOUT)),
                    timeout=self.TIMEOUT
                )
                with response:
                    remote: dict = json.loads(response.read().decode('UTF-8'))
                config: dict = self.verify(remote)
                log.info(f'Successfully obtained remote config from "{url}": {config}')
                return config
            except Exception as e:
                # 單個地址失敗時繼續嘗試下一個地址,全部失敗才回退本機設定。
                log.info(f'Failed to obtain remote config from "{url}" due to {e}')
        log.info(f'All remote addresses are unavailable, using local default config: {self.default_config()}')
        return {}

    def cached_config(self) -> dict:
        """讀取本機快取中的設定,快取不存在或不合法時返回空字典,不觸發遠端請求。"""
        try:
            if os.path.exists(self.PATH):
                with open(file=self.PATH, mode='r', encoding='UTF-8') as f:
                    return self.verify(json.load(f))
        except Exception as e:
            log.info(f'Failed to read the remote config cache due to {e}')
        return {}


rc = RemoteConfig()
