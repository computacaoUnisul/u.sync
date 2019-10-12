from book_bot.spiders import eva_auth
from .util import fake_response_from_file, mock_http_open


def test_create_request_with_logged_html():
    spider = eva_auth.LogoutSpider()
    http = mock_http_open()
    response = fake_response_from_file('assets/logged.html')
    assert spider.parse_home(response) is not None
    http.assert_called_once()


def test_do_not_recognize_logout_url_with_non_logged_html():
    spider = eva_auth.LogoutSpider()
    http = mock_http_open()
    response = fake_response_from_file('assets/login.html')
    assert spider.parse_home(response) is None
    http.assert_not_called()
    