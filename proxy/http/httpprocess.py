from __future__ import annotations
from typing import TYPE_CHECKING
from termcolor import colored

if TYPE_CHECKING:
    from .request import Request, Response


class HttpProcess:
    def __init__(self) -> None:
        pass

    # リクエスト送信前のカスタム処理
    def process_request(self, request: Request) -> None:
        _ = request

    # レスポンス取得後のカスタム処理
    def process_response(self, response: Response) -> None:
        request = response.request

        print(colored(request.message.method, 'cyan') +
              ' ' + str(request.get_uri()))
        print('    ' + colored(response.message.status_code, 'yellow') + ' ' + str(round(len(response.message) /
              1024, 3)) + ' kB ' + str(round(response.get_roundtrip_time(), 3)) + ' sec\n', end='')
