# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2025/2/25 1:11
# File:stdio.py
import os
import sys
import csv
import datetime

from typing import (
    List,
    Union,
)

from rich.style import Style
from rich.table import Table
from rich.markdown import Markdown
from rich.progress import (
    Progress,
    BarColumn,
    TextColumn,
    SpinnerColumn,
    TimeRemainingColumn,
    TransferSpeedColumn
)
from enum import Enum
from pyrogram import __version__ as pyrogram_version  # noqa.

from module import (
    log,
    console,
    README,
    __version__,
    __license__,
    __copyright__,
    VERSION_WITH_COMMIT
)
from module.remote import rc
from module.language import _t
from module.util import (
    is_docker,
    check_update,
    get_terminal_width
)
from module.enums import (
    Banner,
    KeyWord,
    DownloadType,
    UploadStatus,
    ProcessConfig,
    GradientColor
)


class StatisticalTable:
    def __init__(self):
        self.skip_video, self.skip_photo, self.skip_document, self.skip_audio, self.skip_voice, self.skip_animation, self.skip_video_note, self.skip_live_photo = set(), set(), set(), set(), set(), set(), set(), set()
        self.success_video, self.success_photo, self.success_document, self.success_audio, self.success_voice, self.success_animation, self.success_video_note, self.success_live_photo = set(), set(), set(), set(), set(), set(), set(), set()
        self.failure_video, self.failure_photo, self.failure_document, self.failure_audio, self.failure_voice, self.failure_animation, self.failure_video_note, self.failure_live_photo = set(), set(), set(), set(), set(), set(), set(), set()

    def print_count_table(
            self,
            export: bool = False,
            only_export: bool = False,
            export_directory: str = os.path.join(
                os.path.dirname(os.path.abspath(sys.argv[0])),
                'DownloadRecordForm',
                'CountForm'
            )
    ) -> Union[bool, None, List[str]]:
        """列印統計的下載資訊的表格。"""
        success_video: int = len(self.success_video)
        failure_video: int = len(self.failure_video)
        skip_video: int = len(self.skip_video)
        success_photo: int = len(self.success_photo)
        failure_photo: int = len(self.failure_photo)
        skip_photo: int = len(self.skip_photo)
        success_document: int = len(self.success_document)
        failure_document: int = len(self.failure_document)
        skip_document: int = len(self.skip_document)
        success_audio: int = len(self.success_audio)
        failure_audio: int = len(self.failure_audio)
        skip_audio: int = len(self.skip_audio)
        success_voice: int = len(self.success_voice)
        failure_voice: int = len(self.failure_voice)
        skip_voice: int = len(self.skip_voice)
        success_animation: int = len(self.success_animation)
        failure_animation: int = len(self.failure_animation)
        skip_animation: int = len(self.skip_animation)
        success_video_note: int = len(self.success_video_note)
        failure_video_note: int = len(self.failure_video_note)
        skip_video_note: int = len(self.skip_video_note)
        success_live_photo: int = len(self.success_live_photo)
        failure_live_photo: int = len(self.failure_live_photo)
        skip_live_photo: int = len(self.skip_live_photo)
        total_video: int = sum([success_video, failure_video, skip_video])
        total_photo: int = sum([success_photo, failure_photo, skip_photo])
        total_document: int = sum([success_document, failure_document, skip_document])
        total_audio: int = sum([success_audio, failure_audio, skip_audio])
        total_voice: int = sum([success_voice, failure_voice, skip_voice])
        total_animation: int = sum([success_animation, failure_animation, skip_animation])
        total_video_note: int = sum([success_video_note, failure_video_note, skip_video_note])
        total_live_photo: int = sum([success_live_photo, failure_live_photo, skip_live_photo])
        table_data = [
            [_t(DownloadType.VIDEO), success_video, failure_video, skip_video, total_video],
            [_t(DownloadType.PHOTO), success_photo, failure_photo, skip_photo, total_photo],
            [_t(DownloadType.DOCUMENT), success_document, failure_document, skip_document, total_document],
            [_t(DownloadType.AUDIO), success_audio, failure_audio, skip_audio, total_audio],
            [_t(DownloadType.VOICE), success_voice, failure_voice, skip_voice, total_voice],
            [_t(DownloadType.ANIMATION), success_animation, failure_animation, skip_animation, total_animation],
            [_t(DownloadType.VIDEO_NOTE), success_video_note, failure_video_note, skip_video_note, total_video_note],
            [_t(DownloadType.LIVE_PHOTO), success_live_photo, failure_live_photo, skip_live_photo, total_live_photo],
            ['合計',
             sum([success_video, success_photo, success_document, success_audio, success_voice, success_animation,
                  success_video_note, success_live_photo]),
             sum([failure_video, failure_photo, failure_document, failure_audio, failure_voice, failure_animation,
                  failure_video_note, failure_live_photo]),
             sum([skip_video, skip_photo, skip_document, skip_audio, skip_voice, skip_animation, skip_video_note,
                  skip_live_photo]),
             sum([total_video, total_photo, total_document, total_audio, total_voice, total_animation,
                  total_video_note, total_live_photo]),
             ]
        ]
        if len(table_data) < 3:
            log.error(f'無法輸出計數表格,{_t(KeyWord.REASON)}:"表格資料非法"')
            return False
        check_count: int = 0
        for row in table_data:
            for count in row:
                if isinstance(count, int):
                    check_count += count
        if check_count == 0:
            log.info(f'無法生成計數統計表,{_t(KeyWord.REASON)}:"沒有任何下載"')
            return False
        title: str = '媒體下載統計'
        header: tuple = ('類型&狀態', '成功下載', '失敗下載', '跳過下載', '合計')
        if export:
            try:
                export_directory: str = '/app/form/CountForm' if is_docker() else export_directory
                os.makedirs(export_directory, exist_ok=True)
                with open(
                        file=os.path.join(
                            export_directory,
                            f'{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_媒體下載統計表.csv'
                        ),
                        mode='w',
                        newline='',
                        encoding='utf-8-sig'
                ) as f:
                    writer = csv.writer(f)
                    writer.writerow(header)
                    writer.writerows(table_data)
            except Exception as e:
                log.error(f'匯出媒體計數統計表時出錯,{_t(KeyWord.REASON)}:"{e}"')
                if only_export:
                    return None
        try:
            result: Union[bool, None, List[str]] = True
            if only_export is False:  # noqa.
                panel = PanelTable(
                    title=title,
                    header=header,
                    data=table_data
                )
                panel.print_meta()
                result = panel.to_markdown_chunks()
            return result
        except Exception as e:
            log.error(f'列印媒體計數統計表時出錯,{_t(KeyWord.REASON)}:"{e}"')
            return None

    @staticmethod
    def print_link_table(
            link_tasks: dict,
            export: bool = False,
            only_export: bool = False,
            export_directory: str = os.path.join(
                os.path.dirname(os.path.abspath(sys.argv[0])),
                'DownloadRecordForm',
                'LinkForm'
            )
    ) -> Union[bool, None, List[str]]:
        """列印統計的下載連結資訊的表格。"""
        try:
            data: list = []
            for index, (link, task) in enumerate(link_tasks.items(), start=1):
                complete_num = int(task.complete_num)
                member_num = int(task.member_num)
                try:
                    rate = round(complete_num / member_num * 100, 2)
                except ZeroDivisionError:
                    rate = 0
                complete_rate = f'{complete_num}/{member_num}[{rate}%]'
                file_names: Union[set, str] = task.file_name
                error_msg = task.error_msg
                if not error_msg:
                    error_info = ''
                elif 'all_member' in error_msg:
                    error_info = str(error_msg.get('all_member'))
                else:
                    for fn in error_msg.keys():
                        file_names.add(fn)
                    error_info = '\n'.join([f'{fn}: {err}' for fn, err in error_msg.items()])
                file_names = '\n'.join(sorted(file_names))
                data.append([index, link, file_names, complete_rate, error_info])

            if not data:
                log.info(f'無法生成下載連結統計表,{_t(KeyWord.REASON)}:"沒有任何下載"')
                return False
            title: str = '下載連結統計'
            header: tuple = ('編號', '連結', '檔案名稱', '完成率', '錯誤資訊')
            if export:
                try:
                    export_directory: str = '/app/form/LinkForm' if is_docker() else export_directory
                    os.makedirs(export_directory, exist_ok=True)
                    with open(file=os.path.join(
                            export_directory,
                            f'{datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")}_下載連結統計表.csv'
                    ),
                            mode='w',
                            newline='',
                            encoding='utf-8-sig'
                    ) as f:
                        writer = csv.writer(f)
                        writer.writerow(header)
                        writer.writerows(data)
                except Exception as e:
                    log.error(f'匯出下載連結統計表時出錯,{_t(KeyWord.REASON)}:"{e}"')
                    if only_export:
                        return None
            result: Union[bool, None, List[str]] = True
            if only_export is False:  # noqa.
                panel = PanelTable(
                    title=title,
                    header=header,
                    data=data,
                    show_lines=True
                )
                panel.print_meta()
                result = panel.to_markdown_chunks()
            return result
        except Exception as e:
            log.error(f'列印下載連結統計表時出錯,{_t(KeyWord.REASON)}:"{e}"')
            return None

    @staticmethod
    def print_upload_table(
            upload_tasks: set,
            export: bool = False,
            only_export: bool = False,
            export_directory: str = os.path.join(
                os.path.dirname(os.path.abspath(sys.argv[0])),
                'UploadRecordForm',
                'Normal'
            )
    ) -> Union[bool, None, List[str]]:
        """列印統計的上載資訊的表格。"""
        tasks = list(upload_tasks)
        if not tasks:
            log.info(f'無法生成上載統計表,{_t(KeyWord.REASON)}:"沒有任何上載"')
            return False
        meta_table_title: str = '上載任務統計'
        meta_table_header: tuple = (
            '編號',
            '頻道',
            '檔案',
            '檔案大小',
            '狀態',
            '上載後自動刪除',
            '錯誤資訊'
        )
        meta_table_data = []
        for index, task in enumerate(tasks, start=1):
            if isinstance(task.status, Enum):
                status = _t(str(task.status.value))
            else:
                status = _t(str(task.status))
            delete = '是' if getattr(task, 'with_delete', False) else '否'
            error_msg = getattr(task, 'error_msg', False) or ''
            row = [
                index,
                str(task.chat_id) if task.chat_id else '未知',
                task.file_path,
                MetaData.suitable_units_display(task.file_size),
                status,
                delete,
                error_msg
            ]
            meta_table_data.append(row)

        # 檢查資料有效性。
        if len(meta_table_data) < 1:
            return False
        count_table_title = '媒體上載統計'
        count_table_header: tuple = ('狀態', '數量')
        pending_tasks = len([t for t in tasks if t.status == UploadStatus.PENDING])
        uploading_tasks = len([t for t in tasks if t.status == UploadStatus.UPLOADING])
        success_tasks = len([t for t in tasks if t.status == UploadStatus.SUCCESS])
        failure_tasks = len([t for t in tasks if t.status == UploadStatus.FAILURE])
        sent_tasks = len([t for t in tasks if t.status == UploadStatus.SENT])
        delete_tasks = len([t for t in tasks if getattr(t, 'with_delete', False)])
        total_tasks = len(tasks)
        total_size = sum(task.file_size for task in tasks)
        count_table_data = [
            [_t(UploadStatus.PENDING), pending_tasks],
            [_t(UploadStatus.UPLOADING), uploading_tasks],
            [_t(UploadStatus.SUCCESS), success_tasks],
            [_t(UploadStatus.FAILURE), failure_tasks],
            [_t(UploadStatus.SENT), sent_tasks],
            ['自動刪除', delete_tasks],
            ['合計', total_tasks]
        ]

        if export:
            try:
                export_directory: str = '/app/form/Normal' if is_docker() else export_directory
                os.makedirs(export_directory, exist_ok=True)
                timestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')
                filename = f'{timestamp}_上載任務統計表.csv'

                with open(
                        file=os.path.join(export_directory, filename),
                        mode='w',
                        newline='',
                        encoding='utf-8-sig'
                ) as f:
                    writer = csv.writer(f)
                    writer.writerow([meta_table_title])
                    writer.writerow(meta_table_header)
                    for row in meta_table_data:
                        writer.writerow(row)

                    writer.writerow([])
                    writer.writerow([count_table_title])
                    for row in count_table_data:
                        writer.writerow(row)

                    writer.writerow([])
                    writer.writerow(
                        ['平均大小', MetaData.suitable_units_display(
                            total_size / total_tasks if total_tasks > 0 else 0)]
                    )
                    writer.writerow(
                        ['總大小', MetaData.suitable_units_display(
                            total_size)]
                    )

                log.info(f'上載任務統計表已匯出:{os.path.join(export_directory, filename)}')

            except Exception as e:
                log.error(f'匯出上載任務統計表時出錯,{_t(KeyWord.REASON)}:"{e}"')
                if only_export:
                    return None

        try:
            result: Union[bool, None, List[str]] = True
            if only_export is False:  # noqa.
                meta_panel = PanelTable(
                    title=meta_table_title,
                    header=meta_table_header,
                    data=meta_table_data,
                    show_lines=True
                )
                count_panel = PanelTable(
                    title=count_table_title,
                    header=count_table_header,
                    data=count_table_data,
                    show_lines=False
                )
                # 終端機與訊息均按"媒體上載統計在上、上載任務統計在下"的順序展示。
                count_panel.print_meta()
                meta_panel.print_meta()
                # 兩張表合併為一條訊息發送:計數表很短,直接拼在元資訊表首個分片之前,
                # 這樣首片即含兩表,不會再多出一條無鍵盤的訊息(元資訊表超長時後續分片仍逐條追加)。
                meta_chunks = meta_panel.to_markdown_chunks()
                meta_chunks[0] = f'{count_panel.to_markdown()}\n\n{meta_chunks[0]}'
                result = meta_chunks
            return result

        except Exception as e:
            log.error(f'列印上載任務統計表時出錯,{_t(KeyWord.REASON)}:"{e}"')
            return None

    @staticmethod
    def print_config_table(app) -> None:
        """列印用戶所填寫設定檔的表格。"""
        try:
            if app.enable_proxy:
                proxy_key: list = []
                proxy_value: list = []
                for i in app.proxy.items():
                    if i[0] not in ['enable_proxy', 'username', 'password']:
                        key, value = i
                        proxy_key.append(key)
                        proxy_value.append(value)
                proxy_table = PanelTable(title='代理設定', header=tuple(proxy_key), data=[proxy_value])
                proxy_table.print_meta()
        except Exception as e:
            log.error(f'列印代理設定表時出錯,{_t(KeyWord.REASON)}:"{e}"')
        try:
            if app.links and os.path.isdir(app.links):
                log.warning(f'"{app.links}"是一個資料夾,並非.txt文字,請重新填寫媒體連結文字檔案的路徑。')
            else:
                with open(file=app.links, mode='r', encoding='UTF-8') as _:
                    res: list = [content.strip() for content in _.readlines() if content.strip()]
                if res:
                    format_res: list = []
                    for i in enumerate(res, start=1):
                        format_res.append(list(i))
                    link_table = PanelTable(
                        title='連結內容',
                        header=('編號', '連結'),
                        data=format_res
                    )
                    link_table.print_meta()
        except FileNotFoundError:
            log.warning('無法讀取媒體連結檔案,可能已被刪除。')
        except (PermissionError, AttributeError) as e:  # v1.1.3 用戶錯誤填寫路徑提示。
            log.error(f'讀取"{app.links}"時出錯,{_t(KeyWord.REASON)}:"{e}"')
        except Exception as e:
            log.error(f'列印連結內容統計表時出錯,{_t(KeyWord.REASON)}:"{e}"')
        try:
            _dtype: list = app.download_type.copy()  # 淺拷貝賦值給_dtype,避免傳入函數後改變原資料。
            data: list = [
                [_t(DownloadType.VIDEO),
                 ProcessConfig.get_dtype(_dtype).get('video', False)
                 ],
                [_t(DownloadType.PHOTO),
                 ProcessConfig.get_dtype(_dtype).get('photo', False)
                 ],
                [_t(DownloadType.DOCUMENT),
                 ProcessConfig.get_dtype(_dtype).get('document', False)
                 ],
                [_t(DownloadType.AUDIO),
                 ProcessConfig.get_dtype(_dtype).get('audio', False)
                 ],
                [_t(DownloadType.VOICE),
                 ProcessConfig.get_dtype(_dtype).get('voice', False)
                 ],
                [_t(DownloadType.ANIMATION),
                 ProcessConfig.get_dtype(_dtype).get('animation', False)
                 ],
                [_t(DownloadType.VIDEO_NOTE),
                 ProcessConfig.get_dtype(_dtype).get('video_note', False)
                 ],
                [_t(DownloadType.LIVE_PHOTO),
                 ProcessConfig.get_dtype(_dtype).get('live_photo', False)
                 ]
            ]
            download_type_table = PanelTable(title='下載類型', header=('類型', '是否下載'), data=data)
            download_type_table.print_meta()
        except Exception as e:
            log.error(f'列印下載類型統計表時出錯,{_t(KeyWord.REASON)}:"{e}"')

    @staticmethod
    def print_env_table(app):
        update_version: str = check_update(
            remote_version=rc.cached_config().get('version', __version__),
            local_version=__version__
        )
        log.debug(
            {
                'platform': app.platform,
                'python_version': sys.version.split()[0],
                'TRMD_version': VERSION_WITH_COMMIT,
                'update_version': update_version,
                'pyrogram_version': pyrogram_version,
                'user_config_path': app.config_path,
                'session_directory': app.work_directory,
                'temp_directory': app.temp_directory,
                'enable_proxy': app.enable_proxy
            }
        )
        PanelTable(
            title='執行環境',
            header=('名稱', '值'),
            data=[
                ['平台', app.platform],
                ['Python版本', sys.version.split()[0]],
                ['TRMD版本', f'{VERSION_WITH_COMMIT}({update_version}⬆)' if update_version else VERSION_WITH_COMMIT],
                ['Pyrogram版本', pyrogram_version],
                ['用戶設定檔', app.config_path],
                ['儲存目錄', app.save_directory],
                ['會話目錄', app.work_directory],
                ['快取目錄', app.temp_directory],
                ['使用系統代理', app.enable_proxy]
            ],
            show_lines=True
        ).print_meta()


class PanelTable:
    def __init__(self, title: str, header: tuple, data: list, styles: dict = None, show_lines: bool = False):
        self.title: str = title
        self.header: tuple = header
        self.data: list = data
        self.table = Table(title=title, highlight=True, show_lines=show_lines)
        self.table.title_style = Style(color='white', bold=True)
        # 添加列。
        for _, col in enumerate(header):
            style = styles.get(col, {}) if styles else {}
            self.table.add_column(col, **style)

        # 添加資料行。
        for row in data:
            self.table.add_row(*map(str, row))  # 確保資料項是字串類型，防止類型錯誤。

    def print_meta(self):
        console.print(self.table, justify='center')

    def to_markdown(self) -> str:
        """將表格轉換為 GitHub 風格的 Markdown 表格字串(不分片)。"""
        return '\n'.join(self.to_markdown_chunks(max_len=1 << 30))

    def to_markdown_chunks(self, max_len: int = 30000) -> List[str]:
        """將表格轉換為若干 GitHub 風格 Markdown 表格字串。

        每個分片長度不超過 ``max_len``,且各自帶有表頭,以便單獨發送時仍可閱讀。
        用於規避 Telegram 富文字訊息的長度上限(約 32768 字元)。
        """

        def _cell(value) -> str:
            text: str = str(value)
            # 去除換行,避免破壞 Markdown 表格結構,並轉義管道符。
            text = text.replace('\n', ' ').replace('\r', ' ').replace('|', '\\|')
            return text

        header_cells: list = [_cell(h) for h in self.header]
        header_line: str = '| ' + ' | '.join(header_cells) + ' |'
        sep_line: str = '| ' + ' | '.join(['---'] * len(header_cells)) + ' |'
        title_lines: list = [f'## {self.title}', ''] if self.title else []

        # 每個分片都要額外承載:標題 + 表頭 + 分隔行,預留這部分開銷。
        overhead: int = len('\n'.join(title_lines + [header_line, sep_line])) + 2
        budget: int = max(max_len - overhead, 200)  # 至少保證能放入一行資料。

        chunks: List[str] = []
        current_rows: List[str] = []
        current_len: int = 0

        def _flush() -> None:
            nonlocal current_rows, current_len
            if current_rows:
                parts: list = title_lines + [header_line, sep_line] + current_rows
                chunks.append('\n'.join(parts))
                current_rows = []
                current_len = 0

        for row in self.data:
            row_line: str = '| ' + ' | '.join(_cell(c) for c in row) + ' |'
            row_len: int = len(row_line) + 1  # +1 代表行尾換行符。
            # 已有資料且追加本行會超預算,則先將已有行成片。
            if current_rows and current_len + row_len > budget:
                _flush()
            current_rows.append(row_line)
            current_len += row_len
            # 本片已達預算(含單行超限的情況),立即成片,避免後續行擠爆。
            if current_len >= budget:
                _flush()
        _flush()
        return chunks


class MetaData:
    @staticmethod
    def print_current_task_num(
            prompt: str,
            num: int
    ) -> None:
        console.log(f'{prompt}:{num}。', justify='right', style='#B1DB74')

    @staticmethod
    def print_meta():
        console.print(
            GradientColor.gen_gradient_text(
                text=Banner.TRMD,
                gradient_color=GradientColor.generate_gradient(
                    start_color='#fa709a',
                    end_color='#fee140',
                    steps=10)),
            style='bold',
            highlight=False
        )
        MetaData.print_about()
        MetaData.print_disclaimer()

    @staticmethod
    def print_about():
        console.print(f'[i]{__copyright__}[/i]')
        console.print(f'Licensed under the terms of the {__license__}.', end='\n')

    @staticmethod
    def print_disclaimer():
        console.print(GradientColor.gen_gradient_text(
            '\t所有使用本軟件的行為及其後果均由使用者自行承擔全部法律責任，開發者不對任何使用行為及其後果負責。',
            gradient_color=GradientColor.BLUE2PURPLE_14)
        )

    @staticmethod
    def suitable_units_display(number: Union[int, float], unit=None, mebibyte=False) -> str:
        result: dict = MetaData.__determine_suitable_units(number, unit, mebibyte)
        return result.get('number') + result.get('unit')

    @staticmethod
    def __determine_suitable_units(number, unit=None, mebibyte=False) -> dict:
        if mebibyte:
            units = ['B', 'KiB', 'MiB', 'GiB', 'TiB', 'PiB']  # 二進制單位。
            base = 1024
        else:
            units = ['B', 'KB', 'MB', 'GB', 'TB', 'PB']  # 十進制單位。
            base = 1000

        if unit in units:  # 如果指定了單位,直接計算。
            index = units.index(unit)
            value = number / (base ** index)
            return {'number': '{:.2f}'.format(value), 'unit': unit}

        else:  # 否則自動計算最合適的單位。
            values = [number]
            for i in range(len(units) - 1):
                if values[i] >= base:
                    values.append(values[i] / base)
                else:
                    break
            return {
                'number': '{:.2f}'.format(values[-1]),
                'unit': units[len(values) - 1]
            }

    @staticmethod
    def print_helper():
        console.print(Markdown('# 設定檔說明'))
        console.print(Markdown(README))





class ProgressBar:
    def __init__(self):
        self.progress = Progress(
            SpinnerColumn(),
            TextColumn('[progress.description]{task.description} [bold blue]{task.fields[filename]}', justify='right'),
            BarColumn(bar_width=max(int(get_terminal_width() * 0.2), 1)),
            '[progress.percentage]{task.percentage:>3.1f}%',
            '•',
            '[bold green]{task.fields[info]}',
            '•',
            TransferSpeedColumn(),
            '•',
            TimeRemainingColumn(),
            console=console
        )

    @staticmethod
    def download(current, total, progress, task_id) -> None:
        progress.update(
            task_id,
            completed=current,
            info=f'{MetaData.suitable_units_display(current)}/{MetaData.suitable_units_display(total)}',
            total=total
        )

    @staticmethod
    def upload(current, total, progress, task_id, upload_manager) -> None:
        upload_manager.update_file_part(
            file_part=current // (512 * 1024)
        )
        progress.update(
            task_id,
            completed=current,
            info=f'{MetaData.suitable_units_display(current)}/{MetaData.suitable_units_display(total)}',
            total=total
        )

    @staticmethod
    def bot(completed, total, display_width=20):
        if total == 0:
            return '░' * display_width
        if completed > total:
            completed = total
        ratio = completed / total
        completed_bars = int(ratio * display_width)
        remaining_bars = display_width - completed_bars
        return '█' * completed_bars + '░' * remaining_bars
