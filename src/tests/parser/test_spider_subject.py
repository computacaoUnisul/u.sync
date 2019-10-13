from unittest.mock import MagicMock

import pytest
from book_bot.spiders import eva_parser
from book_bot.items import Subject
from tests.util import spider_from_scratch


@pytest.fixture
def spider():
    return spider_from_scratch(eva_parser.SubjectSpider)


@pytest.fixture
def subject_loader():
    def fake_subject_loader(size):
        def loader_mock(spider, name, tree, loader):
            for i in range(size):
                s = Subject(name=name, class_id=str(i))
                loader.subjects.append(s)
        return loader_mock
    return fake_subject_loader


@pytest.fixture
def load_spider(spider, subject_loader, http_response):
    def mock_parser(size):
        old_loader = eva_parser._display_and_load 
        eva_parser._display_and_load = MagicMock(side_effect=subject_loader(size))
        spider.parse_subjects(http_response)
        eva_parser._display_and_load = old_loader
        return spider
    return mock_parser


def test_request_all_subjects(load_spider):
    expected_subjects = 2
    spider = load_spider(expected_subjects)
    assert len(spider.subjects) == expected_subjects


def test_loading_raises_exception_when_empty(http_response):
    http_response.xpath = MagicMock(return_value=[])
    
    with pytest.raises(Exception):
        spider = eva_parser.SubjectSpider()
        spider.parse_subjects(http_response)


def test_subject_parsing_from_file(spider, subjects_html_response):
    spider.parse_subjects(subjects_html_response)
    for index, subject_item in enumerate(spider.subjects):
        assert subject_item['class_id'] == str(index) 
        assert subject_item['name'] == f'subject{index}'
