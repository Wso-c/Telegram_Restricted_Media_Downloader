import asyncio
import logging
import os
import platform
import shutil
import sqlite3
import threading
import time
import uuid
from collections import deque

from module.task import DownloadTask


class EventHub(logging.Handler):
    """Bounded, process-local event feed shared by HTTP and service adapters."""

    def __init__(self, capacity: int = 500):
        super().__init__()
        self._events = deque(maxlen=capacity)
        self._condition = threading.Condition()
        self._next_id = 1
        self.setFormatter(logging.Formatter('%(asctime)s %(levelname)s %(message)s'))
        logging.getLogger().addHandler(self)

    def emit(self, record: logging.LogRecord) -> None:
        try:
            self.publish('log', {'level': record.levelname, 'message': self.format(record)})
        except Exception:
            self.handleError(record)

    def publish(self, event: str, data: dict) -> None:
        with self._condition:
            item = {'id': self._next_id, 'event': event, 'data': data}
            self._next_id += 1
            self._events.append(item)
            self._condition.notify_all()

    def read_after(self, event_id: int, timeout: float = 15.0) -> list:
        with self._condition:
            events = [item for item in self._events if item['id'] > event_id]
            if events:
                return events
            self._condition.wait(timeout)
            return [item for item in self._events if item['id'] > event_id]

    def close(self) -> None:
        logging.getLogger().removeHandler(self)
        super().close()


class AppCore:
    """Application services bound to the existing downloader and Telegram clients."""

    def __init__(self, downloader):
        self.downloader = downloader
        self.events = EventHub()
        self.forward_jobs = {}
        app = getattr(downloader, 'app', None)
        config_path = getattr(app, 'config_path', None)
        database_directory = os.path.dirname(os.path.abspath(config_path)) if config_path else os.getcwd()
        self.queue_database = os.path.join(database_directory, 'trmd-control.sqlite3')
        database_fd = os.open(self.queue_database, os.O_CREAT | os.O_RDWR, 0o600)
        os.close(database_fd)
        os.chmod(self.queue_database, 0o600)
        with sqlite3.connect(self.queue_database) as database:
            database.execute(
                'CREATE TABLE IF NOT EXISTS queue_links ('
                'position INTEGER PRIMARY KEY, link TEXT NOT NULL UNIQUE)'
            )
        self._saved_order = self._read_saved_order()

    async def add_download(self, link: str) -> dict:
        result = await self.downloader.web_add_download(link)
        if result.get('status'):
            self._apply_saved_order()
        return result

    async def forward_messages(
        self,
        origin_link: str,
        target_link: str,
        start_id: int,
        end_id: int
    ) -> dict:
        return await self.downloader.web_forward_messages(
            origin_link=origin_link,
            target_link=target_link,
            start_id=start_id,
            end_id=end_id
        )

    async def start_forward_job(
        self,
        origin_link: str,
        target_link: str,
        start_id: int,
        end_id: int
    ) -> dict:
        if not origin_link.startswith('https://t.me/') or not target_link.startswith('https://t.me/'):
            return {'status': False, 'e_code': '來源及目標必須是有效的 Telegram 頻道連結。'}
        if start_id < 1 or end_id < start_id:
            return {'status': False, 'e_code': '訊息 ID 必須為正整數，且起始 ID 不可大於結束 ID。'}
        job_id = uuid.uuid4().hex
        self.forward_jobs[job_id] = {'state': 'pending', 'result': None}
        asyncio.create_task(self._run_forward_job(
            job_id=job_id,
            origin_link=origin_link,
            target_link=target_link,
            start_id=start_id,
            end_id=end_id
        ))
        self.events.publish('forward.started', {'job_id': job_id})
        return {'status': True, 'job_id': job_id, 'state': 'pending'}

    async def _run_forward_job(self, job_id: str, **params) -> None:
        self.forward_jobs[job_id]['state'] = 'running'
        try:
            result = await self.forward_messages(**params)
        except Exception as error:
            result = {'status': False, 'e_code': str(error)}
        self.forward_jobs[job_id] = {
            'state': 'completed' if result.get('status') else 'failed',
            'result': result
        }
        self.events.publish('forward.completed', {'job_id': job_id, **self.forward_jobs[job_id]})

    def get_forward_job(self, job_id: str) -> dict:
        job = self.forward_jobs.get(job_id)
        if job is None:
            return {'status': False, 'e_code': '找不到此轉發工作。'}
        return {'status': True, 'job_id': job_id, **job}

    async def control_download(self, link: str, message_id: int, action: str) -> dict:
        return await self.downloader.web_control_download(link, message_id, action)

    async def snapshot(self) -> dict:
        return await self.downloader.web.async_snapshot()

    async def reorder_download_queue(self, links: list) -> dict:
        if not isinstance(links, list) or not all(isinstance(link, str) for link in links):
            return {'status': False, 'e_code': '佇列順序必須是連結清單。'}

        pending_links = []
        for task in DownloadTask.ordered_tasks():
            if any(
                item.get('status') == 'pending'
                for item in task.items.values()
            ):
                pending_links.append(task.link)

        if len(links) != len(set(links)) or set(links) != set(pending_links):
            return {'status': False, 'e_code': '連結清單必須包含每個待處理佇列項目且不得重複。'}

        iterator = iter(links)
        DownloadTask.ORDER[:] = [
            next(iterator) if link in pending_links else link
            for link in DownloadTask.ORDER
        ]
        self._saved_order = list(links)
        with sqlite3.connect(self.queue_database) as database:
            database.execute('DELETE FROM queue_links')
            database.executemany(
                'INSERT INTO queue_links (position, link) VALUES (?, ?)',
                enumerate(links)
            )
        self.events.publish('queue.reordered', {'links': links})
        return {'status': True, 'links': links}

    def _read_saved_order(self) -> list:
        with sqlite3.connect(self.queue_database) as database:
            return [
                row[0] for row in database.execute(
                    'SELECT link FROM queue_links ORDER BY position'
                )
            ]

    def _apply_saved_order(self) -> None:
        if not self._saved_order:
            return
        pending_links = [
            task.link for task in DownloadTask.ordered_tasks()
            if any(item.get('status') == 'pending' for item in task.items.values())
        ]
        saved = [link for link in self._saved_order if link in pending_links]
        reordered = saved + [link for link in pending_links if link not in saved]
        iterator = iter(reordered)
        DownloadTask.ORDER[:] = [
            next(iterator) if link in pending_links else link
            for link in DownloadTask.ORDER
        ]

    def queue_order(self) -> list:
        self._apply_saved_order()
        return [
            task.link for task in DownloadTask.ordered_tasks()
            if any(item.get('status') == 'pending' for item in task.items.values())
        ]

    def session_inventory(self) -> dict:
        app = getattr(self.downloader, 'app', None)
        directory = getattr(app, 'work_directory', None)
        entries = []
        if directory and os.path.isdir(directory):
            for name in sorted(os.listdir(directory)):
                if name.endswith('.session') and os.path.isfile(os.path.join(directory, name)):
                    active_name = getattr(getattr(app, 'client', None), 'name', None)
                    entries.append({'name': name, 'active': bool(active_name and name == active_name + '.session')})
        client = getattr(app, 'client', None)
        me = getattr(client, 'me', None)
        return {
            'status': True,
            'directory': directory,
            'sessions': entries,
            'account': {
                'id': getattr(me, 'id', None),
                'username': getattr(me, 'username', None),
                'first_name': getattr(me, 'first_name', None),
                'connected': bool(client and getattr(client, 'is_connected', False))
            }
        }

    def system_status(self) -> dict:
        rss = None
        try:
            import resource
            rss = int(resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)
            if platform.system() != 'Darwin':
                rss *= 1024
        except ImportError:
            pass
        memory_total = None
        memory_percent = None
        try:
            page_size = os.sysconf('SC_PAGE_SIZE')
            pages = os.sysconf('SC_PHYS_PAGES')
            memory_total = page_size * pages
            memory_percent = round(rss / memory_total * 100, 2) if memory_total and rss is not None else None
        except (AttributeError, OSError, ValueError):
            pass
        app = getattr(self.downloader, 'app', None)
        download_dir = getattr(app, 'save_directory', None)
        disk = None
        if download_dir and os.path.isdir(download_dir):
            usage_disk = shutil.disk_usage(download_dir)
            disk = {'total': usage_disk.total, 'used': usage_disk.used, 'free': usage_disk.free}
        return {
            'status': True,
            'timestamp': time.time(),
            'platform': platform.platform(),
            'cpu_load_1m': os.getloadavg()[0] if hasattr(os, 'getloadavg') else None,
            'process_peak_rss': rss,
            'system_memory_total': memory_total,
            'process_peak_memory_percent': memory_percent,
            'disk': disk
        }

    def get_config_yaml(self) -> dict:
        app = getattr(self.downloader, 'app', None)
        if app is None:
            return {'status': False, 'e_code': '設定管理未就緒。'}
        import yaml
        return {
            'status': True,
            'config_yaml': yaml.safe_dump(app.config, allow_unicode=True, sort_keys=False)
        }

    def save_config_yaml(self, text: str) -> dict:
        import yaml

        if not isinstance(text, str):
            return {'status': False, 'e_code': '設定內容必須是 YAML 文字。'}
        try:
            config = yaml.safe_load(text)
        except yaml.YAMLError as error:
            return {'status': False, 'e_code': f'YAML 格式錯誤：{error}'}
        if not isinstance(config, dict):
            return {'status': False, 'e_code': '設定 YAML 根節點必須是物件。'}
        result = self.downloader.web.update_settings(config)
        if result.get('status'):
            self.events.publish('config.updated', {'restart_required': result.get('restart_required', [])})
        return result
