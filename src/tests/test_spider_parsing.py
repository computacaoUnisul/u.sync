from unittest.mock import MagicMock, Mock

import pytest
from book_bot.spiders import eva_spider
from book_bot.items import Subject, Book 
from .util import fake_response, fake_response_from_file


def test_request_subject_by_id():
    spider_helper = eva_spider.EvaSpider()
    
    index = 0
    def assert_requests(*args, **kwargs):
        nonlocal index
        req_args = kwargs.get('args')
        fake_subject = dict(class_id=str(index))
        default_args = spider_helper._get_subject_args(fake_subject)
        index += 1
        assert req_args == default_args

    fake_loader = fake_subject_loader(2)
    mock_parser(fake_loader, side_effect=assert_requests)


def test_book_parses_filename_from_url():
    filename = 'foo.txt'
    book = Book(name='bar', download_url=f'/baz?{Book.qs_file_arg}={filename}')
    assert book['filename'] == filename


def test_request_all_subjects():
    expected_calls = 2
    fake_loader = fake_subject_loader(expected_calls)

    spider = mock_parser(fake_loader)
    assert spider._open_req.call_count == expected_calls


def test_raises_exception_when_empty():
    response = fake_response()
    response.xpath = MagicMock(return_value=[])
    
    with pytest.raises(Exception):
        spider = eva_spider.EvaSpider()
        iterate(spider.parse_subjects(response))


def test_subject_parsing_from_file():
    spider = eva_spider.EvaSpider()
    
    response = fake_response_from_file('assets/subjects.html')
    iterator = spider.parse_subjects(response)

    for index, req in enumerate(iterator):
        subject_item = req.meta['subject']
        assert subject_item['class_id'] == str(index) 
        assert subject_item['name'] == f'subject{index}'


def fake_subject_loader(size):
    def loader_mock(name, tree, loader):
        for i in range(size):
            s = Subject(name=name, class_id=str(i))
            loader.subjects.append(s)
    return loader_mock


def mock_parser(loader_fn, **req_mock_kwargs):
    spider = eva_spider.EvaSpider()
    
    spider._display_list = MagicMock(side_effect=loader_fn)
    spider._open_req = MagicMock(**req_mock_kwargs)

    response = fake_response()
    response.xpath = MagicMock()

    iterate(spider.parse_subjects(response))
    return spider


def iterate(iterator):
    for _ in iterator:
        pass
