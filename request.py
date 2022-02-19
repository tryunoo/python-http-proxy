import urllib
import email
import json
import io

class HttpRequest():
    def __init__(self, raw_req: bytes):
        self.send_time = None
        # https://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html
        self.http_version = None
        self.method = None # GET, POST, etc.
        self.uri = None # https://user:pass@www.example.com:443/test/index.html?param1=foo&param2=bar#fragment
        self.scheme = None # http or https
        self.authority = None # user:pass@www.example.com:443
        self.user_info = '' # user:pass
        self.host = None # www.example.com
        self.port = None # 80, 443, etc.
        self.path = '' # /test/index.html
        self.query_string = '' # param1=foo&param2=bar
        self.fragment = '' # fragment
        self.raw_header = b''
        self.raw_body = b''
        self.queries = {}
        self.headers = {}
        self.body_parameters = {}

        try:
            self.create_request_object(raw_req)
        except Exception as e:
            print("Request parse error")
            print(e)
        

    def get_raw_request(self):
        return self.raw_header + b'\r\n\r\n' + self.raw_body


    def create_request_object(self, raw_req: bytes):  
        self.raw_header, self.raw_body = raw_req.split(b'\r\n\r\n', 1)
        request_line, headers = self.raw_header.decode('utf-8').split('\r\n', 1)
        
        message = email.message_from_file(io.StringIO(headers))
        self.headers = dict(message.items())
        self.method, self.uri, self.http_version = request_line.split(' ')

        if self.method == 'CONNECT':
            self.uri = 'https://' + self.uri
        elif self.uri[0] == '/':
            self.host = self.headers['Host']
            self.uri = 'https://' + self.host + self.uri

        o = urllib.parse.urlparse(self.uri)

        self.scheme = o.scheme
        self.authority = o.netloc
        self.path = o.path
        self.query_string = o.query
        self.fragment = o.fragment

        self.queries = urllib.parse.parse_qs(self.query_string)

        if '@' in self.authority:
            splitted = self.authority.split('@')
            self.user_info = splitted[0]

            if ':' in splitted[1]:
                self.host, self.port = splitted[1].split(':')
                self.port = int(self.port)
            else:
                self.host = splitted[1]
                if self.scheme == 'http':
                    self.port = 80
                else:
                    self.port = 443

        else:
            if ':' in self.authority:
                self.host, self.port = self.authority.split(':')
                self.port = int(self.port)
            else:
                self.host = self.authority
                if self.scheme == 'http':
                    self.port = 80
                else:
                    self.port = 443
        
        if self.host == '':
            self.host = self.headers['Host']


        if len(self.raw_body) > 0 and 'Content-Type' in self.headers:
            if self.headers['Content-Type'] == 'application/json':
                try:
                    self.body_parameters = json.loads(self.raw_body)
                except:
                    pass
            
            if self.headers['Content-Type'] == 'application/json':
                self.body_parameters = urllib.parse.parse_qs(self.raw_body)



class HttpResponse():
    def __init__(self, raw_res: bytes):
        self.round_trip_time = None
        self.http_version = None
        self.status_code = None
        self.raw_header = b''
        self.raw_body = b''
        self.queries = {}
        self.headers = {}
        self.body_parameters = {}
        self.res_len = 0

        self.create_response_object(raw_res)
    

    def get_raw_response(self):
        return self.raw_header + b'\r\n\r\n' + self.raw_body


    def create_response_object(self, raw_res: bytes):
        self.raw_header, self.raw_body = raw_res.split(b'\r\n\r\n', 1)

        self.res_len = len(raw_res)

        try:
            response_line, headers = self.raw_header.decode('utf-8').split('\r\n', 1)
        except:
            response_line = self.raw_header

        try:
            self.http_version, self.status_code, _ = response_line.split(' ', 2)
        except:
            self.http_version, self.status_code = response_line.split(' ', 2)

        message = email.message_from_file(io.StringIO(headers))
        self.headers = dict(message.items())

