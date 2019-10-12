import os
from unittest.mock import MagicMock

from book_bot.utils import http
from scrapy.http import TextResponse, Request


def fake_response(url=None, request=None, **kwargs):
    if request is None:
        request = fake_request(url=url)
    return TextResponse(url=request.url, 
                        request=request, 
                        encoding='utf-8', 
                        **kwargs)


def fake_response_from_file(file_name, url=None):
    """@link https://stackoverflow.com/questions/6456304/scrapy-unit-testing"""
    if not file_name[0] == '/':
        responses_dir = os.path.dirname(os.path.realpath(__file__))
        file_path = os.path.join(responses_dir, file_name)
    else:
        file_path = file_name

    with open(file_path, 'rb') as h:
        file_content = h.read()

    return fake_response(url=url, body=file_content)


def fake_request(url=None):
    if not url:
        url = 'http://www.example.com'
    return Request(url=url)


def mock_http_open():
    mocked_http = MagicMock(side_effect=http.web_open)
    http.web_open = mocked_http
    return mocked_http