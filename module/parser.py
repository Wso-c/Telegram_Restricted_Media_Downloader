# coding=UTF-8
# Author:Gentlesprite
# Software:PyCharm
# Time:2026/1/23 17:47
# File:parser.py
from argparse import (
    SUPPRESS,
    ArgumentParser
)
import os

from module import (
    console,
    VERSION_SEMVER,
    SOFTWARE_SHORT_NAME
)
from module.enums import (
    Banner,
    WebMeta,
    GradientColor
)


class TelegramRestrictedMediaDownloaderArgumentParser(ArgumentParser):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_argument(
            '-h', '--help',
            action='help',
            default=SUPPRESS,
            help='展示說明'
        )
        self.add_argument(
            '-v', '--version',
            action='version',
            version=f'{SOFTWARE_SHORT_NAME} {VERSION_SEMVER}',
            default=SUPPRESS,
            help='展示版本資訊'
        )
        self.add_argument(
            '-q', '--quiet',
            action='store_true',
            default=False,
            help='跳過重新設定檔的確認提示'
        )
        self.add_argument(
            '-c', '--config',
            type=str,
            required=False,
            default='',
            help='設定用戶設定檔的路徑'
        )
        self.add_argument(
            '-s', '--session',
            type=str,
            required=False,
            default='',
            help='設定會話檔案的路徑'
        )
        self.add_argument(
            '-t', '--temp',
            type=str,
            required=False,
            default='',
            help='設定執行快取的路徑'
        )
        self.add_argument(
            '-p', '--port',
            type=int,
            nargs='?',
            metavar='PORT',
            const=WebMeta.DEFAULT_PORT,
            default=WebMeta.DEFAULT_PORT,
            help='設定網頁面板的連接埠'
        )
        self.add_argument(
            '--host',
            type=str,
            default=os.environ.get('TRMD_WEB_HOST', '127.0.0.1'),
            help='設定網頁面板的綁定地址（預設僅本機可存取）'
        )

    def print_help(self, file=None):
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
        super().print_help(file)


PARSE_ARGS = TelegramRestrictedMediaDownloaderArgumentParser(add_help=False).parse_args()
