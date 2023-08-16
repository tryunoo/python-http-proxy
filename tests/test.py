import asyncio
from os.path import dirname, abspath
import sys
import copy

parent_dir = dirname(dirname(abspath(__file__)))
sys.path.append(parent_dir)
from proxy.http.http import RequestMessage, ResponseMessage, Headers, Query, MediaType, RequestLine
from proxy.http.request import Request, Response

raw_request = b"GET /test?a=%22%60%9%3C/%20srt%3E&b=2&a=3 HTTP/2\r\n"
raw_request += b"Host: login.yahoo.co.jp\r\n"
raw_request += b"Cookie: B=2qll3chhmovt0&b=3&s=06; XB=2qll3chhmovt0&b=3&s=06; A=2qll3chhmovt0&sd=B&t=1668054946&u=1686027519&v=1; XA=2qll3chhmovt0&sd=B&t=1668054946&u=1686027519&v=1; JV=A9wf0mQAAFEHJ26K-tXNQfuN2QeYxKjg-aC2vwadf-27xucopG74TK9SQ8c9yAkNfE003Nuiykl0Pi085P9e4-4-UX0cBdyTQ9v8Dg6MuOhspeLFdQ9pVjndp4h6G9xaG3w_IERtNa7UHzDutEuS1i9cGTChV41bvpmueL8VZ1422xVHEIUu6M9Zod3gxMqvnCJiFFMntJmuhCwOo5PenBvucqrmmk0Qbz0vuRb3d5pqcBI47momNKrhxzXFgCdL0hX6Y2LyQTT7aPnI2MW9uFw4b4V7CVLR8uLcKCPmi05_pNTFcrpGNzWtldCDSRxbInIlK11NM5BRQWvBprG45uj-3CPjS2I_7jn_n8erWLGOwEl5XyQKzQnUDW8sej9ZmfetzYfrkuhzxmpWP6WwYh3ryo9aNJs0GLBeFvMjarzUcZAhPN2rnCITQavH_FhCbRp3pMrIQ3W2mEq5DgTizkNJo4LwwWD2zIl5zOP1lh7TjW9vPtOpAuQNYTvWRjUxE7MYDJxcr9VA-MOBwdQmGVppqEip6hh45JXg-jHrF-EMx3asAcgbulQxOCwq5T8Ig0sLsob6sHM0EoRN60iMpGgdwQlYuYFONivy4nIyrowc7CNjJMsKPWmfUx8FqpqQmPogMj9T66YxQXvtdex6A98LlOw&v=2\r\n"
raw_request += b"User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10.15; rv:109.0) Gecko/20100101 Firefox/116.0\r\n"
raw_request += b"Accept: application/json, text/plain, */*\r\n"
raw_request += b"accept-encoding: gzip, test\r\n"
raw_request += b"accept-encoding: deflate\r\n"
raw_request += b"Content-Type: application/json\r\n"
raw_request += b"Content-Length: 270\r\n"
raw_request += b"\r\n"
raw_request += b'{"bcrumb":"Ankg0mQAg6Rr8yaM4Y8gGsB7VQY4zCzkUYA4Tu2qU-Osr85KCxHqBgtvJn1aPRBCY6yNTCsKXJiFstGP8qE8M_33FJBddGHwY-7BHpePA24F4afsTprwnkeodv7xrn7JXfW9p6T5","verify":"0","handle":"a","fido":"0","display":"","src":"www","trans":"61a613f3-82ac-4566-8263-8e9fcfe7a87e","auth_lv":0}'


async def main():
    request_message = RequestMessage(raw_request)

    host = 'login.yahoo.co.jp'
    port = 443
    is_ssl = True
    request = Request(host, port, is_ssl, message=request_message)

    headers = request_message.headers
    for key in headers:
        print(type(key))

asyncio.run(main())
