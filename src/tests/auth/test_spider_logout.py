import pytest
from book_bot.spiders import eva_auth


@pytest.fixture
def spider():
    return eva_auth.LogoutSpider()


def test_create_request_with_logged_html(spider, web_open, logged_html_response):
    assert spider.parse_home(logged_html_response) is not None
    web_open.assert_called_once()


def test_login_not_recognized_with_non_logged_html(spider, 
                                                web_open, 
                                                login_html_response,
                                                login_error_html_response):
    assert spider.parse_home(login_html_response) is None
    assert spider.parse_home(login_error_html_response) is None
    web_open.assert_not_called()
    