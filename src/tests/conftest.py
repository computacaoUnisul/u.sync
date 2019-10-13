import pytest
import os
from unittest.mock import MagicMock

from . import util
from book_bot.items import Subject
from book_bot.utils import http


@pytest.fixture
def http_request():
    return util.fake_request()


@pytest.fixture
def http_response():
    return util.fake_response()


@pytest.fixture
def login_html_response():
    return util.fake_response_from_file('assets/login.html')


@pytest.fixture
def login_error_html_response():
    return util.fake_response_from_file('assets/login_err.html')


@pytest.fixture
def logged_html_response():
    return util.fake_response_from_file('assets/logged.html')


@pytest.fixture
def subjects_html_response():
    return util.fake_response_from_file('assets/subjects.html')


@pytest.fixture
def js_redirect_html_response():
    return util.fake_response_from_file('assets/login_js_redirect.html')


@pytest.fixture
def books_html_response():
    return util.fake_response_from_file('assets/books.html')


@pytest.fixture
def subject():
    return Subject(name='foo', class_id='-1')


@pytest.fixture
def web_open():
    old_impl = http.web_open
    mocked_http = MagicMock(side_effect=old_impl)
    http.web_open = mocked_http
    yield mocked_http
    http.web_open = old_impl
