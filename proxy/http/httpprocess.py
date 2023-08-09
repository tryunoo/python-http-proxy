from __future__ import annotations
from typing import TYPE_CHECKING
from termcolor import colored

if TYPE_CHECKING:
    from proxy.http.request import Request, Response

class HttpProcess():
    def __init__(self):
        pass

    # リクエスト送信前のカスタム処理
    def process_request(self, request: Request):
        pass

    # レスポンス取得後のカスタム処理
    def process_response(self, response: Response):
        request = response.request

        print(colored(request.message.method, 'cyan') + ' ' + request.url)
        print('    ' + colored(response.message.status_code, 'yellow') + ' ' + str(round(len(bytes(response.message))/1024, 3)) + ' kB ' + str(round(response.get_roundtrip_time(), 3)) + ' sec\n', end='')
        #print(response.message)
        #print(response_object.raw_body)
        #print(len(response_object.raw_body))
