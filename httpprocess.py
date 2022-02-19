from request import HttpRequest, HttpResponse
from termcolor import colored

class HttpProcess():
    def __init__(self):
        pass

    # リクエスト送信前のカスタム処理
    def process_request(self, req: HttpRequest):
        return req

    # レスポンス取得後のカスタム処理
    def process_response(self, req: HttpRequest, res: HttpResponse):
        print(colored(req.method, 'cyan') + ' ' + req.scheme + '://' + req.authority + req.path + '\n    ' + colored(res.status_code, 'yellow') + ' ' + str(round(res.res_len/1024, 3)) + 'kb ' + str(res.round_trip_time) + 'sec')

        return res
