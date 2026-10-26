# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2025/2/25 1:32
# File:config.py
import os
import logging
import datetime

from typing import Union

from module import (
    log,
    console,
    yaml,
    CustomDumper,
    PLATFORM,
    FILE_LOG_LEVEL,
    CONSOLE_LOG_LEVEL,
    GLOBAL_CONFIG_NAME,
    GLOBAL_CONFIG_PATH
)
from module.language import _t
from module.parser import PARSE_ARGS
from module.path_tool import (
    gen_backup_config,
    safe_scan_directory_file
)
from module.enums import (
    KeyWord,
    ProcessConfig,
    GetStdioParams
)
from module.util import (
    ctrl_c,
    get_work_directory
)


class BaseConfig:
    FILE_NAME: str = 'base_config.yaml'
    PATH: str = os.path.join(get_work_directory(), FILE_NAME)
    TEMPLATE: dict = {}

    def __init__(self):
        self.config: dict = self.TEMPLATE.copy()
        self.config_path: str = self.PATH

    @staticmethod
    def add_missing_keys(target, template, log_message) -> None:
        """添加缺失的設定檔參數。"""
        for key, value in template.items():
            if key not in target:
                target[key] = value
                console.log(log_message.format(key))

    @staticmethod
    def remove_extra_keys(target, template, log_message) -> None:
        """刪除多餘的設定檔參數。"""
        keys_to_remove: list = [key for key in target.keys() if key not in template]
        for key in keys_to_remove:
            target.pop(key)
            console.log(log_message.format(key))

    def process_nesting(self, param_name: Union[str, dict], config):
        param_template = self.TEMPLATE.get(param_name)
        param_length = len(param_template)
        if param_name in config:
            param_template = self.TEMPLATE.get(param_name)
            param_config = config.get(param_name)
            if not isinstance(param_config, dict) or (
                    isinstance(param_config, dict) and len(param_config) != param_length):
                param_config: dict = {}
                config[param_name] = param_config
            self.add_missing_keys(
                target=param_config,
                template=param_template,
                log_message='"{}"'
                            f'不在{param_name}設定檔中,已添加。'
            )
            self.remove_extra_keys(
                target=param_config,
                template=param_template,
                log_message='"{}"'
                            f'不在{param_name}設定檔中,已刪除。'
            )

    def __check_params(self, config: dict) -> None:
        """檢查設定檔的參數是否完整。"""
        # 如果 config 為 None，初始化為一個空字典。
        if config is None:
            config = {}

        # 處理父級參數。
        self.add_missing_keys(target=config, template=self.TEMPLATE, log_message='"{}"不在全局設定檔中,已添加。')
        # 刪除父級模板中沒有的字段。
        self.remove_extra_keys(config, self.TEMPLATE, '"{}"不在模板中,已刪除。')

        if config != self.config:
            self.config = config
            self.save_config(self.config)

    def load_config(self) -> None:
        """載入全局設定檔。"""
        try:
            if not os.path.exists(self.PATH):
                with open(file=self.PATH, mode='w', encoding='UTF-8') as f:
                    yaml.dump(self.TEMPLATE, f, Dumper=CustomDumper)
                return
            with open(file=self.PATH, mode='r', encoding='UTF-8') as f:
                config = yaml.safe_load(f)
                if config:
                    self.config = config
                else:
                    raise ValueError('The file is empty or has invalid format.')
        except Exception as e:
            log.error(f'檢測到無效或損壞的全局設定檔。已生成新的模板檔案. . .{_t(KeyWord.REASON)}:"{e}"')
            self.config: dict = self.TEMPLATE.copy()
            self.save_config(self.config)

    def save_config(self, config: dict) -> None:
        """儲存設定檔。"""
        try:
            with open(file=self.config_path, mode='w', encoding='UTF-8') as f:
                yaml.dump(config, f)
            log.info('全局設定檔已儲存。')
        except Exception as e:
            log.error(f'儲存全局設定檔失敗,{_t(KeyWord.REASON)}:"{e}"')
        finally:
            self.config = config

    def get_config(self, param, error_param=None) -> Union[str, None]:
        """取得即時的設定檔。"""
        self.load_config()
        return self.config.get(param, error_param)


class UserConfig(BaseConfig):
    DIRECTORY_NAME: str = get_work_directory()  # 取得軟件工作絕對目錄。
    FILE_NAME: str = 'config.yaml'  # 設定檔名。
    PATH: str = os.path.join(DIRECTORY_NAME, FILE_NAME)
    TEMPLATE: dict = {
        'api_id': None,
        'api_hash': None,
        'bot_token': None,
        'session_directory': None,
        'proxy': {
            'enable_proxy': None,
            'scheme': None,
            'hostname': None,
            'port': None,
            'username': None,
            'password': None
        },
        'links': None,
        'save_directory': None,  # v1.3.0 將設定檔中save_path的參數名修改為save_directory。
        'temp_directory': None,
        'max_tasks': {
            'download': None,
            'upload': None
        },
        'is_shutdown': None,
        'download_type': None,
        'max_retries': {
            'download': None,
            'upload': None
        }
    }
    TEMP_DIRECTORY: str = os.path.join(os.getcwd(), 'temp')
    BACKUP_DIRECTORY: str = 'ConfigBackup'
    ABSOLUTE_BACKUP_DIRECTORY: str = os.path.join(DIRECTORY_NAME, BACKUP_DIRECTORY)
    WORK_DIRECTORY: str = os.path.join(os.getcwd(), 'sessions')

    def __init__(self):
        super().__init__()
        self.config_path: str = PARSE_ARGS.config if PARSE_ARGS.config.endswith('.yaml') else UserConfig.PATH
        self.platform: str = PLATFORM
        self.history_timestamp: dict = {}
        self.input_link: list = []
        self.last_record: dict = {}
        self.difference_timestamp: dict = {}
        self.download_type: list = []
        self.record_dtype: set = set()
        self.record_flag: bool = False
        self.modified: bool = False
        self.get_last_history_record()
        self.is_change_account: bool = True
        self.re_config: bool = False
        self.config_guide()
        self.config: dict = self.load_config()  # v1.3.0 修復重複詢問重新設定檔。
        self.api_hash = self.config.get('api_hash')
        self.api_id = self.config.get('api_id')
        self.bot_token = self.config.get('bot_token')
        self.download_type: list = self.config.get('download_type')
        self.is_shutdown: bool = self.config.get('is_shutdown')
        self.links: str = self.config.get('links')
        self.max_download_task: int = self.config.get('max_tasks', {'download': 3}).get('download')
        self.max_download_retries: int = self.config.get('max_retries', {'download': 5}).get('download')
        self.max_upload_task: int = (self.config.get('max_tasks') or {}).get('upload', 3) or 3
        self.max_upload_retries: int = (self.config.get('max_retries') or {}).get('upload', 3) or 3
        self.proxy: dict = self.config.get('proxy', {})
        self.enable_proxy: bool = self.proxy.get('enable_proxy', False)
        self.save_directory: str = self.config.get('save_directory')
        self.work_directory: str = PARSE_ARGS.session or (
                self.config.get('session_directory') or UserConfig.WORK_DIRECTORY)
        self.temp_directory: str = PARSE_ARGS.temp or (self.config.get('temp_directory') or UserConfig.TEMP_DIRECTORY)

    def get_last_history_record(self) -> None:
        """取得最近一次儲存的歷史設定檔。"""
        # 首先判斷是否存在目錄檔案。
        try:
            res: list = safe_scan_directory_file(UserConfig.ABSOLUTE_BACKUP_DIRECTORY)
        except FileNotFoundError:
            return
        except Exception as e:
            log.error(f'讀取歷史檔案時發生錯誤,{_t(KeyWord.REASON)}:"{e}"')
            return
        file_start: str = 'history_'
        file_end: str = '_config.yaml'

        now_timestamp: float = datetime.datetime.now().timestamp()  # 取得目前的時間戳。
        if res:
            for i in res:  # 找出離目前時間最近的設定檔。
                try:
                    if i.startswith(file_start) and i.endswith(file_end):
                        format_date_str = i.replace(file_start, '').replace(file_end, '').replace('_', ' ')
                        to_datetime_obj = datetime.datetime.strptime(format_date_str, '%Y-%m-%d %H-%M-%S')
                        timestamp = to_datetime_obj.timestamp()
                        self.history_timestamp[timestamp] = i
                except ValueError:
                    pass
                except Exception:  # noqa.
                    pass
            for i in self.history_timestamp.keys():
                self.difference_timestamp[now_timestamp - i] = i
            if self.history_timestamp:  # 如果有符合條件的歷史設定檔。
                self.last_record: dict = self.__find_history_config()

        else:
            return

    def __find_history_config(self) -> dict:
        """找到歷史設定檔。"""
        if not self.history_timestamp:
            return {}
        if not self.difference_timestamp:
            return {}
        try:
            min_key: int = min(self.difference_timestamp.keys())
            min_diff_timestamp: str = self.difference_timestamp.get(min_key)
            min_config_file: str = self.history_timestamp.get(min_diff_timestamp)
            if not min_config_file:
                return {}
            last_config_file: str = os.path.join(UserConfig.ABSOLUTE_BACKUP_DIRECTORY, min_config_file)  # 拼接檔案路徑。
            with open(file=last_config_file, mode='r', encoding='UTF-8') as f:
                config: dict = yaml.safe_load(f)
            last_record: dict = self.__check_params(config, history=True)  # v1.1.6修復讀取歷史如果缺失字段使得flag置True。

            if last_record == UserConfig.TEMPLATE:
                # 從字典中刪除目前檔案。
                self.history_timestamp.pop(min_diff_timestamp, None)
                self.difference_timestamp.pop(min_key, None)
                # 遞迴調用。
                return self.__find_history_config()
            else:
                return last_record
        except Exception:  # noqa.
            return {}

    def add_missing_keys(self, target, template, log_message, history=False) -> None:
        """添加缺失的設定檔參數。"""
        for key, value in template.items():
            if key not in target:
                target[key] = value
                if not history:
                    console.log(log_message.format(key))
                    self.modified = True
                    self.record_flag = True

    def remove_extra_keys(self, target, template, log_message, history=False) -> None:
        """刪除多餘的設定檔參數。"""
        keys_to_remove: list = [key for key in target.keys() if key not in template]
        for key in keys_to_remove:
            target.pop(key)
            if not history:
                console.log(log_message.format(key))
                self.record_flag = True

    def __check_params(self, config: dict, history=False) -> dict:
        """檢查設定檔的參數是否完整。"""
        # 如果 config 為 None，初始化為一個空字典。
        if config is None:
            config = {}

        # 處理父級參數。
        self.add_missing_keys(
            target=config,
            template=UserConfig.TEMPLATE,
            log_message='"{}"不在設定檔中,已添加。',
            history=history
        )

        self.process_nesting(param_name='proxy', config=config)
        self.process_nesting(param_name='max_tasks', config=config)
        self.process_nesting(param_name='max_retries', config=config)

        # 刪除父級模板中沒有的字段。
        self.remove_extra_keys(
            target=config,
            template=UserConfig.TEMPLATE,
            log_message='"{}"不在模板中,已刪除。',
            history=history
        )

        return config

    def load_config(self) -> dict:
        """載入一次目前的設定檔,並附帶合法性驗證、缺失參數的檢測以及各種異常時的處理措施。"""
        config: dict = UserConfig.TEMPLATE.copy()
        try:
            if not os.path.exists(self.config_path):
                with open(file=self.config_path, mode='w', encoding='UTF-8') as f:
                    yaml.dump(UserConfig.TEMPLATE, f, Dumper=CustomDumper)
                console.log('未找到設定檔,已生成新的模板檔案. . .')
                self.re_config = True  # v1.3.4 修復設定檔不存在時,無法重新生成設定檔的問題。
            with open(self.config_path, 'r', encoding='UTF-8') as f:
                config: dict = yaml.safe_load(f)  # v1.1.4 加入對每個字段的完整性檢測。
            compare_config: dict = config.copy() if config else {}
            config: dict = self.__check_params(config) if compare_config else None
            if config != compare_config or config == UserConfig.TEMPLATE:  # v1.3.4 修復設定檔所有參數都為空時報錯問題。
                self.re_config = True
        except UnicodeDecodeError as e:  # v1.1.3 加入設定檔路徑是中文或特殊字元時的錯誤提示,由於nuitka打包的性質決定,
            # 中文路徑無法被打包好的二進制檔案識別,故在設定檔時無論是連結路徑還是媒體儲存路徑都請使用英文命名。
            self.re_config = True
            log.error(
                f'讀取設定檔遇到編碼錯誤,可能儲存路徑中包含中文或特殊字元的資料夾。已生成新的模板檔案. . .{_t(KeyWord.REASON)}:"{e}"')
            self.backup_config(config, error_config=self.re_config)
        except Exception as e:
            self.re_config = True
            console.print('「注意」連結路徑和儲存路徑不能有引號!', style='#B1DB74')
            log.error(f'檢測到無效或損壞的設定檔。已生成新的模板檔案. . .{_t(KeyWord.REASON)}:"{e}"')
            self.backup_config(config, error_config=self.re_config)
        finally:
            if config is None:
                self.re_config = True
                log.warning('檢測到空的設定檔。已生成新的模板檔案. . .')
                config: dict = UserConfig.TEMPLATE.copy()
        return config

    def backup_config(
            self,
            backup_config: dict,
            error_config: bool = False,
            force: bool = False
    ) -> None:  # v1.2.9 更正backup_config參數類型。
        """備份目前的設定檔。"""
        if backup_config != UserConfig.TEMPLATE or force:  # v1.2.9 修復比較變量錯誤的問題。
            backup_path: str = gen_backup_config(
                old_path=self.config_path,
                absolute_backup_dir=UserConfig.ABSOLUTE_BACKUP_DIRECTORY,
                error_config=error_config
            )
            console.log(f'原來的設定檔已備份至"{backup_path}"', style='#B1DB74')
        else:
            console.log('設定檔與模板檔案完全一致,無需備份。')

    def config_guide(self) -> None:
        """引導用戶以互動式的方式修改、儲存設定檔。"""
        exit_flag: bool = False
        pre_load_config: dict = self.load_config()
        gsp = GetStdioParams()
        # v1.1.0 更替api_id和api_hash位置,與telegram申請的api位置對應以免輸錯。
        try:
            if not self.modified and pre_load_config != UserConfig.TEMPLATE:
                re_config: bool = False if PARSE_ARGS.quiet else gsp.get_is_re_config().get('is_re_config')
                if re_config:
                    self.re_config = re_config
                    # 快取原有的session_directory，防止重新設定時丟失。
                    origin_session_directory = pre_load_config.get('session_directory')
                    pre_load_config: dict = UserConfig.TEMPLATE.copy()
                    self.backup_config(backup_config=pre_load_config, error_config=False, force=True)
                    self.get_last_history_record()  # 更新到上次填寫的記錄。
                    if not PARSE_ARGS.session:
                        self.is_change_account = gsp.get_is_change_account(valid_format='y|n').get(
                            'is_change_account')
                        if self.is_change_account:
                            pre_load_config['session_directory'] = gsp.get_session_directory().get('session_directory')
                        else:
                            pre_load_config['session_directory'] = origin_session_directory
            _api_id: Union[str, None] = pre_load_config.get('api_id')
            _api_hash: Union[str, None] = pre_load_config.get('api_hash')
            _bot_token: Union[str, None] = pre_load_config.get('bot_token')
            _links: Union[str, None] = pre_load_config.get('links')
            _save_directory: Union[str, None] = pre_load_config.get('save_directory')
            _max_download_task: Union[int, None] = pre_load_config.get('max_tasks', {'download': 3}).get('download')
            _max_download_retries: Union[int, None] = pre_load_config.get('max_retries', {'download': 5}).get(
                'download')
            _download_type: Union[list, None] = pre_load_config.get('download_type')
            _is_shutdown: Union[bool, None] = pre_load_config.get('is_shutdown')
            _proxy_config: dict = pre_load_config.get('proxy', {})
            _enable_proxy: Union[str, bool] = _proxy_config.get('enable_proxy', False)
            _proxy_scheme: Union[str, bool] = _proxy_config.get('scheme', False)
            _proxy_hostname: Union[str, bool] = _proxy_config.get('hostname', False)
            _proxy_port: Union[str, bool] = _proxy_config.get('port', False)
            _proxy_username: Union[str, bool] = _proxy_config.get('username', False)
            _proxy_password: Union[str, bool] = _proxy_config.get('password', False)
            proxy_record: dict = self.last_record.get('proxy', {})  # proxy的歷史記錄。
            enable_bot: bool = False  # 是否開啟機械人。
            if any([not _api_id, not _api_hash, not _save_directory, not _max_download_task, not _download_type]):
                console.print('「注意」直接按 Enter代表使用上次的記錄。',
                              style='#B1DB74')
            if self.is_change_account or _api_id is None or _api_hash is None or self.re_config:
                if not _api_id:
                    api_id, record_flag = gsp.get_api_id(
                        last_record=self.last_record.get('api_id')).values()
                    if record_flag:
                        self.record_flag = record_flag
                        pre_load_config['api_id'] = api_id
                if not _api_hash:
                    api_hash, record_flag = gsp.get_api_hash(
                        last_record=self.last_record.get('api_hash'),
                        valid_length=32).values()
                    if record_flag:
                        self.record_flag = record_flag
                        pre_load_config['api_hash'] = api_hash
            if not _bot_token and self.re_config:
                enable_bot: bool = gsp.get_enable_bot(valid_format='y|n').get('enable_bot')
                if enable_bot:
                    bot_token, record_flag = gsp.get_bot_token(
                        last_record=self.last_record.get('bot_token'),
                        valid_format=':').values()
                    if record_flag:
                        self.record_flag = record_flag
                        pre_load_config['bot_token'] = bot_token
            if not _links or not _bot_token and self.re_config:
                links, record_flag = gsp.get_links(
                    last_record=self.last_record.get('links'),
                    valid_format='.txt',
                    enable_bot=True if enable_bot else False).values()
                if record_flag:
                    self.record_flag = record_flag
                    pre_load_config['links'] = links
            if not _save_directory or self.re_config:
                save_directory, record_flag = gsp.get_save_directory(
                    last_record=self.last_record.get('save_directory')).values()
                if record_flag:
                    self.record_flag = record_flag
                    pre_load_config['save_directory'] = save_directory
            if not _max_download_task or self.re_config:
                max_download_task, record_flag = gsp.get_max_download_task(
                    last_record=self.last_record.get('max_tasks', {'download': 3}).get('download')).values()
                if record_flag:
                    self.record_flag = record_flag
                    pre_load_config.get('max_tasks')['download'] = max_download_task
            if not _max_download_retries or self.re_config:
                max_retry_count, record_flag = gsp.get_max_retry_count(
                    last_record=self.last_record.get('max_retries', {'download': 5}).get('download')).values()
                if record_flag:
                    self.record_flag = record_flag
                    pre_load_config.get('max_retries')['download'] = max_retry_count
            if not _download_type or self.re_config:
                download_type, record_flag = gsp.get_download_type(
                    last_record=self.last_record.get('download_type')).values()
                if record_flag:
                    self.record_flag = record_flag
                    pre_load_config['download_type'] = download_type
            if _is_shutdown is None or self.re_config:
                is_shutdown, _is_shutdown_record_flag = gsp.get_is_shutdown(
                    last_record=self.last_record.get('is_shutdown'),
                    valid_format='y|n').values()
                if _is_shutdown_record_flag:
                    self.record_flag = True
                    pre_load_config['is_shutdown'] = is_shutdown
            # 是否開啟代理
            if not _enable_proxy and self.re_config:
                valid_format: str = 'y|n'
                is_enable_proxy, is_ep_record_flag = gsp.get_enable_proxy(
                    last_record=proxy_record.get('enable_proxy', False),
                    valid_format=valid_format).values()
                if is_ep_record_flag:
                    self.record_flag = True
                    _proxy_config['enable_proxy'] = is_enable_proxy
            # 如果需要使用代理。
            # 如果上面設定的enable_proxy為True或本來設定檔中的enable_proxy就為True。
            if _proxy_config.get('enable_proxy') is True or _enable_proxy is True:
                if ProcessConfig.is_proxy_input(proxy_config=_proxy_config):
                    if not _proxy_scheme:
                        scheme, record_flag = gsp.get_scheme(
                            last_record=proxy_record.get('scheme'),
                            valid_format=['http', 'socks4',
                                          'socks5']
                        ).values()
                        if record_flag:
                            self.record_flag = True
                            _proxy_config['scheme'] = scheme
                    if not _proxy_hostname:
                        hostname, record_flag = gsp.get_hostname(
                            proxy_config=_proxy_config,
                            last_record=proxy_record.get('hostname'),
                            valid_format='x.x.x.x').values()
                        if record_flag:
                            self.record_flag = True
                            _proxy_config['hostname'] = hostname
                    if not _proxy_port:
                        port, record_flag = gsp.get_port(
                            proxy_config=_proxy_config,
                            last_record=proxy_record.get('port'),
                            valid_format='0~65535').values()
                        if record_flag:
                            self.record_flag = True
                            _proxy_config['port'] = port
                    if not all([_proxy_username, _proxy_password]):
                        username, password, record_flag = gsp.get_proxy_authentication().values()
                        if record_flag:
                            self.record_flag = True
                            _proxy_config['username'] = username
                            _proxy_config['password'] = password
        except KeyboardInterrupt:
            n: bool = True
            try:
                if self.record_flag:
                    print('\n')
                    if gsp.get_is_ki_save_config().get('is_ki_save_config'):
                        self.save_config(pre_load_config)
                        console.log('設定已儲存!')
                    else:
                        console.log('不儲存目前填寫參數。')
                else:
                    raise SystemExit(0)
            except KeyboardInterrupt:
                n: bool = False
                print('\n')
                console.log('不儲存目前填寫參數(用戶手動終止設定參數)。')
            finally:
                if n:
                    print('\n')
                    console.log('用戶手動終止設定參數。')
                ctrl_c()
                exit_flag: bool = True
        if exit_flag:
            raise SystemExit(0)
        pre_load_config.get(
            'max_tasks',
            {
                'download': _max_download_task,
                'upload': 3
            }
        )['upload'] = (pre_load_config.get('max_tasks') or {}).get('upload', 3) or 3
        pre_load_config.get(
            'max_retries',
            {
                'download': _max_download_retries,
                'upload': 3}
        )['upload'] = (pre_load_config.get('max_retries') or {}).get('upload', 3) or 3
        if not PARSE_ARGS.session:
            _session_directory = pre_load_config.get(
                'session_directory',
                UserConfig.WORK_DIRECTORY) or UserConfig.WORK_DIRECTORY
            pre_load_config['session_directory'] = _session_directory
        else:
            pre_load_config['session_directory'] = PARSE_ARGS.session

        if not PARSE_ARGS.temp:
            _temp_directory = pre_load_config.get(
                'temp_directory',
                UserConfig.TEMP_DIRECTORY) or UserConfig.TEMP_DIRECTORY
            pre_load_config['temp_directory'] = _temp_directory
        else:
            pre_load_config['temp_directory'] = PARSE_ARGS.temp
        self.save_config(pre_load_config)  # v1.3.0 修復不儲存設定檔時,設定檔仍然儲存的問題。

    def save_config(self, config: dict) -> None:
        """儲存設定檔。"""
        try:
            with open(file=self.config_path, mode='w', encoding='UTF-8') as f:
                yaml.dump(config, f)
            log.info('設定檔已儲存。')
        except Exception as e:
            log.error(f'儲存設定檔失敗,{_t(KeyWord.REASON)}:"{e}"')


class GlobalConfig(BaseConfig):
    FILE_NAME: str = GLOBAL_CONFIG_NAME
    PATH: str = GLOBAL_CONFIG_PATH
    TEMPLATE: dict = {
        'notice': True,
        'file_log_level': logging.getLevelName(FILE_LOG_LEVEL),
        'console_log_level': logging.getLevelName(CONSOLE_LOG_LEVEL),
        'export_table': {
            'link': False,
            'count': False,
            'upload': False
        },
        'upload':
            {
                'download_upload': True,
                'delete': False
            },
        'forward_type':
            {
                'video': True,
                'photo': True,
                'audio': True,
                'document': True,
                'voice': True,
                'text': True,
                'animation': True,
                'video_note': True,
                'live_photo': True
            }
    }

    def __init__(self):
        super().__init__()
        self.default_upload_nesting = self.TEMPLATE.get('upload')
        self.default_forward_type_nesting = self.TEMPLATE.get('forward_type')
        self.load_config()
        self.__check_params(self.config.copy())
        self.download_upload: bool = self.get_nesting_config(
            default_nesting=self.default_upload_nesting,
            param='upload',
            nesting_param='download_upload'
        )
        self.upload_delete: bool = self.get_nesting_config(
            default_nesting=self.default_upload_nesting,
            param='upload',
            nesting_param='delete'
        )
        self.forward_type: dict = self.config.get('forward_type')

    def get_nesting_config(self, default_nesting, param, nesting_param):
        return self.config.get(param, default_nesting).get(nesting_param)

    def save_config(self, config: dict) -> None:
        super().save_config(config)
        self.download_upload = self.get_nesting_config(
            default_nesting=self.default_upload_nesting,
            param='upload',
            nesting_param='download_upload'
        )
        self.upload_delete = self.get_nesting_config(
            default_nesting=self.default_upload_nesting,
            param='upload',
            nesting_param='delete'
        )
        self.forward_type: dict = self.config.get('forward_type')
        p = '全局設定檔已重新載入。'
        console.log(p, style='#FF4689')
        log.info(f'{p.replace("。", ":")}{self.config}')

    def __check_params(self, config: dict) -> None:
        if config is None:
            config = {}

        # 處理父級參數。
        self.add_missing_keys(
            target=config,
            template=self.TEMPLATE,
            log_message='"{}"不在全局設定檔中,已添加。'
        )
        # 處理嵌套參數。
        self.process_nesting(param_name='export_table', config=config)
        self.process_nesting(param_name='upload', config=config)
        self.process_nesting(param_name='forward_type', config=config)
        # 刪除父級模板中沒有的字段。
        self.remove_extra_keys(
            target=config,
            template=self.TEMPLATE,
            log_message='"{}"不在模板中,已刪除。'
        )

        if config != self.config:
            self.config = config
            self.save_config(self.config)
