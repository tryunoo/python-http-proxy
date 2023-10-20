# -*- coding: utf-8 -*-
import sys
import proxy
from httprequest import PreparedRequest, Response
from termcolor import colored


def request_process(request: PreparedRequest):
    pass


def response_process(response: Response):
    request = response.request

    print(colored(request.message.method, 'cyan') +
            ' ' + str(request.get_uri()))
    print('    ' + colored(response.message.status_code, 'yellow') + ' ' + str(round(len(response.message) /
            1024, 3)) + ' kB ' + str(round(response.get_roundtrip_time(), 3)) + ' sec\n', end='')


if __name__ == '__main__':
    sys.exit(proxy.run_proxy(request_process, response_process))