from unittest.mock import MagicMock, Mock

import pytest
from book_bot.spiders import eva_parser
from book_bot.items import Subject, Book 
from book_bot.utils import http, os_files
from .util import fake_response, fake_response_from_file, mock_http_open


def test_book_parses_filename_from_url():
    filename = 'foo.txt'
    book = Book(name='bar', download_url=f'/baz?{Book.qs_file_arg}={filename}')
    assert book['filename'] == filename


def test_request_all_subjects():
    expected_subjects = 2
    fake_loader = fake_subject_loader(expected_subjects)

    spider = mock_parser(fake_loader)
   
    assert len(spider.subjects) == expected_subjects


def test_raises_exception_when_empty():
    response = fake_response()
    response.xpath = MagicMock(return_value=[])
    
    with pytest.raises(Exception):
        spider = eva_parser.SubjectSpider()
        spider.parse_subjects(response)


def test_subject_parsing_from_file():
    spider = mock_subject_spider()
    response = fake_response_from_file('assets/subjects.html')
    
    for index, subject_item in enumerate(spider.subjects):
        assert subject_item['class_id'] == str(index) 
        assert subject_item['name'] == f'subject{index}'


def fake_subject_loader(size):
    def loader_mock(spider, name, tree, loader):
        for i in range(size):
            s = Subject(name=name, class_id=str(i))
            loader.subjects.append(s)
    return loader_mock


def mock_parser(loader_fn):
    spider = mock_subject_spider([])
    
    old_loader = eva_parser._display_and_load 
    eva_parser._display_and_load = MagicMock(side_effect=loader_fn)

    response = fake_response()
    response.xpath = MagicMock()

    spider.parse_subjects(response)
    eva_parser._display_and_load = old_loader
    return spider


def mock_subject_spider(initial_subjects=[]):
    old_load_sync = os_files.load_sync_data
    os_files.load_sync_data = MagicMock(side_effect=lambda *all: initial_subjects)
    spider = eva_parser.SubjectSpider()
    os_files.load_sync_data = old_load_sync
    return spider