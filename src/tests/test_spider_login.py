from unittest.mock import MagicMock

from book_bot.spiders import eva_spider
from .util import fake_request, fake_response_from_file


def test_do_not_block_logged_html():
    spider = _login_assertions_from_file('assets/logged.html')
    spider.retry_login.assert_not_called()
    spider._open_req.assert_called_once()


def test_retry_login_when_not_logged():
    _do_not_login('assets/login.html')
    

def test_retry_login_when_login_failed():
    _do_not_login('assets/login_err.html')


def test_retry_login_with_default_credentials():
    spider = eva_spider.EvaSpider()
    old_creds = spider._build_creds('foo', '123')
    next_creds = spider._build_creds('', '321')
    expected_creds = spider._build_creds('foo', '321')

    spider._read_auth = MagicMock(side_effect=lambda: next_creds)
    
    request = fake_request()
    request.meta['creds'] = old_creds
    new_request = spider.retry_login(request)
    assert new_request.meta['creds'] == expected_creds


def _do_not_login(file):
    spider = _login_assertions_from_file(file)
    spider.retry_login.assert_called_once()
    spider._open_req.assert_not_called()


def _login_assertions_from_file(file):
    spider = eva_spider.EvaSpider()
    spider.retry_login = MagicMock()
    spider._open_req = MagicMock()

    response = fake_response_from_file(file)
    spider.after_login(response)
    return spider
    