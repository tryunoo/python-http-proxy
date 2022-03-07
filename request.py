import urllib
import email
import json
import io

class HttpRequest():
    def __init__(self):
        self.send_time = None
        # https://www.w3.org/Protocols/rfc2616/rfc2616-sec5.html
        self.http_version = None
        self.method = None # GET, POST, etc.
        self.uri = None # https://www.example.com:443/test/index.html?param1=foo&param2=bar#fragment
        self.scheme = None # http or https
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
        self.body_len = 0
        self.res_len = 0


    def get_raw_request(self):
        return self.raw_header + self.raw_body


    def set_header(self, raw_header):
        self.res_len = len(raw_header)
        self.raw_header = raw_header
        request_line, headers = raw_header.decode('utf-8').split('\n', 1)

        message = email.message_from_file(io.StringIO(headers))
        self.headers = dict(message.items())

        self.method, self.uri, self.http_version = request_line.split(' ')

        if ':' in self.headers['Host']:
            self.host, self.port = self.headers['Host'].split(':')
            self.port = int(self.port)
        else:
            self.host = self.headers['Host']

        if self.method == 'CONNECT':
            self.uri = 'https://' + self.uri
        elif self.uri[0] == '/':
            self.uri = 'https://' + self.host + self.uri

        o = urllib.parse.urlparse(self.uri)

        self.scheme = o.scheme
        self.authority = o.netloc
        self.path = o.path
        self.query_string = o.query
        self.fragment = o.fragment

        self.queries = urllib.parse.parse_qs(self.query_string)

        if self.scheme == 'http':
            self.raw_header = self.raw_header.replace(b'http://' + self.host.encode('utf-8'), b'', 1)

        if self.port == None:
            if self.scheme == 'http':
                self.port = 80
            else:
                self.port = 443


    def set_body(self, raw_body):
        self.raw_body = raw_body
        self.body_len = len(raw_body)
        self.res_len += self.body_len
        
        if len(self.raw_body) > 0 and 'Content-Type' in self.headers:
            if self.headers['Content-Type'] == 'application/json':
                try:
                    self.body_parameters = json.loads(self.raw_body)
                except:
                    pass
            
            if self.headers['Content-Type'] == 'application/json':
                self.body_parameters = urllib.parse.parse_qs(self.raw_body)



class HttpResponse():
    def __init__(self):
        self.round_trip_time = None
        self.http_version = None
        self.status_code = None
        self.raw_header = b''
        self.raw_body = b''
        self.queries = {}
        self.headers = {}
        self.body_parameters = {}
        self.body_len = 0
        self.res_len = 0
    

    def get_raw_response(self):
        return self.raw_header + self.raw_body


    def set_body(self, raw_body):
        self.raw_body = raw_body
        self.body_len = len(raw_body)
        self.res_len += self.body_len


    def set_header(self, raw_header):
        self.res_len = len(raw_header)
        self.raw_header = raw_header
        response_line, headers = raw_header.decode('utf-8').split('\n', 1)

        message = email.message_from_file(io.StringIO(headers))
        self.headers = dict(message.items())

        try:
            self.http_version, self.status_code, _ = response_line.split(' ', 2)
        except:
            self.http_version, self.status_code = response_line.split(' ', 2)


