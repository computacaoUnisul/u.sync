from unittest.mock import MagicMock

import pytest
from tests.util import file_with
from book_bot.spiders import eva_auth
from book_bot.utils import http


@pytest.fixture
def spider(web_open):
    spider = eva_auth.LoginSpider()
    spider.retry_login = MagicMock(side_effect=spider.retry_login)
    return spider


@pytest.fixture
def login_handler(spider):
    return spider.get_login_handler()


@pytest.fixture
def my_credential_getter():
    old_impl = eva_auth.get_credentials
    def wrapper(**kwargs):
        mock = MagicMock(**kwargs)
        eva_auth.get_credentials = mock
        return mock
    yield wrapper
    eva_auth.get_credentials = old_impl 


def test_do_not_block_logged_html(spider, login_handler, logged_html_response):
    login_handler(logged_html_response)
    spider.retry_login.assert_not_called()
    http.web_open.assert_not_called()


def test_retry_login_when_not_logged(spider, login_handler, login_html_response):
    assert_login_failed(spider, login_handler, login_html_response)


def test_retry_login_when_login_failed(spider, login_handler, login_error_html_response):
    assert_login_failed(spider, login_handler, login_error_html_response)


def test_retry_login_when_redirect_to_login_with_js(spider, login_handler, js_redirect_html_response):
    assert_login_failed(spider, login_handler, js_redirect_html_response)
    

def test_retry_login_with_default_credentials(spider, http_response, my_credential_getter):
    old_creds = spider._build_creds('foo', '123')
    next_creds = ('', '321')
    expected_creds = spider._build_creds('foo', '321')
    my_credential_getter(return_value=next_creds)
     
    http_response.meta['creds'] = old_creds
    http_response.request.meta['creds'] = old_creds
    new_request = next(spider.retry_login(http_response))
    
    assert new_request.meta['creds'] == expected_creds
    assert not 'creds' in http_response.request.meta
    assert not 'creds' in http_response.meta


def test_fake_authentication_once(login_html_response):
    eva_auth.LoginSpider.fake_auth()
    assert not eva_auth.LoginSpider.auth_failed(login_html_response)
    assert eva_auth.LoginSpider.auth_failed(login_html_response)


def test_read_auth_info_from_file(spider, 
                                login_handler, 
                                login_html_response, 
                                my_credential_getter):
    filename, user, pwd = '.login_test', 'foo', 'baz'
    file_with(filename, f'{user}\n{pwd}')
    credential_mock = my_credential_getter(side_effect=eva_auth.get_credentials)
    spider.auth_file = filename # forces the spider to read from file credentials
    new_user, new_pwd = spider._read_auth().values()
    assert user == new_user
    assert pwd == new_pwd
    credential_mock.assert_called_once()


def assert_login_failed(spider, handler, response):
    handler(response)
    spider.retry_login.assert_called_once()
    http.web_open.assert_not_called()
    