from unittest.mock import MagicMock

from book_bot.spiders import eva_auth
from book_bot.utils import http
from .util import fake_response, fake_response_from_file, mock_http_open


def test_do_not_block_logged_html():
    spider = _login_assertions_from_file('assets/logged.html')
    spider.retry_login.assert_not_called()
    http.web_open.assert_not_called()


def test_retry_login_when_not_logged():
    _do_not_login('assets/login.html')
    

def test_retry_login_when_login_failed():
    _do_not_login('assets/login_err.html')


def test_retry_login_with_default_credentials():
    spider = eva_auth.LoginSpider()
    old_creds = spider._build_creds('foo', '123')
    next_creds = ('', '321')
    expected_creds = spider._build_creds('foo', '321')

    eva_auth.get_credentials = MagicMock(side_effect=lambda **kwargs: next_creds)
     
    response = fake_response()
    response.meta['creds'] = old_creds
    response.request.meta['creds'] = old_creds
    new_request = next(spider.retry_login(response))
    print(new_request.meta)
    assert new_request.meta['creds'] == expected_creds
    assert not 'creds' in response.request.meta
    assert not 'creds' in response.meta


def test_fake_authentication_once():
    login_response = fake_response_from_file('assets/login.html')
    eva_auth.LoginSpider.fake_auth()
    assert not eva_auth.LoginSpider.auth_failed(login_response)
    assert eva_auth.LoginSpider.auth_failed(login_response)


def _do_not_login(file):
    spider = _login_assertions_from_file(file)
    spider.retry_login.assert_called_once()
    http.web_open.assert_not_called()


def _login_assertions_from_file(file):
    spider = eva_auth.LoginSpider()
    spider.retry_login = MagicMock()
    mock_http_open()

    response = fake_response_from_file(file)
    spider.after_login(spider.retry_login)(response)
    return spider
    