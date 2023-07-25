from __future__ import annotations
from typing import TYPE_CHECKING
from termcolor import colored

if TYPE_CHECKING:
    from request import HttpRequest, HttpResponse

class HttpProcess():
    def __init__(self):
        pass

    # リクエスト送信前のカスタム処理
    def process_request(self, request_object: HttpRequest):
        pass

    # レスポンス取得後のカスタム処理
    def process_response(self, response_object: HttpResponse):
        request_object = response_object.request_object

        print(colored(response_object.status_code, 'yellow') + ' ' + colored(request_object.get_method(), 'cyan') + ' ' + request_object.get_url())
        #print(str(round(response_object.res_len/1024, 3)) + 'kb ' + str(response_object.get_roundtrip_time()) + 'sec\n', end='')
        #print(response_object.get_raw_response())
        #print(response_object.raw_body)
        #print(len(response_object.raw_body))
