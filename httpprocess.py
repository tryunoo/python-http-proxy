
class HttpProcess():
    def __init__(self):
        pass

    # リクエスト送信前のカスタム処理
    def process_request(self, req):
        print(req.scheme + '://' + req.authority + req.path)
        return req

    # レスポンス取得後のカスタム処理
    def process_response(self, res):
        return res
