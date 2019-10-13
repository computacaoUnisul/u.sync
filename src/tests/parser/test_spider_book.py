from unittest.mock import MagicMock

import pytest
from book_bot.spiders import eva_parser
from book_bot.items import Book, Subject
from tests.util import spider_from_scratch


@pytest.fixture
def spider():
    return spider_from_scratch(eva_parser.BookSpider)


@pytest.fixture
def book_loader():
    def fake_book_loader(size):
        def loader_mock(spider, name, tree, loader):
            for i in range(size):
                s = Book(name=name, download_url=str(i))
                loader.books.append(s)
        return loader_mock
    return fake_book_loader


@pytest.fixture
def load_spider(spider, book_loader, http_response, subject):
    def mock_parser(size):
        http_response.meta['subject'] = subject
        old_loader = eva_parser._display_and_load 
        eva_parser._display_and_load = MagicMock(side_effect=book_loader(size))
        spider.parse_books(http_response)
        eva_parser._display_and_load = old_loader
        return spider
    return mock_parser


def test_request_all_books(load_spider):
    expected_books = 2
    spider = load_spider(expected_books)
    assert len(spider.books) == expected_books


def test_book_parsing_from_file(spider, books_html_response, subject):
    spider.books = [] # clear any remaining books
    books_html_response.meta['subject'] = subject
    spider.parse_books(books_html_response)
    for index, book_item in enumerate(spider.books):
        assert book_item['subject'] == subject
        assert book_item['download_url'] == str(index) 
        assert book_item['name'] == f'book{index}'


def test_stop_requests_when_subjects_are_empty(spider, books_html_response, subject):
    books_html_response.meta['subject'] = subject
    with pytest.raises(StopIteration):
        next(spider.parse_books(books_html_response))

    
def test_generate_more_requests_with_subjects(spider, web_open, books_html_response, subject):
    spider.subjects_content = [subject]
    books_html_response.meta['subject'] = subject
    next(spider.parse_books(books_html_response))
    web_open.assert_called_once()