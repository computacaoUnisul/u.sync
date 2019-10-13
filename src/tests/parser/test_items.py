import pytest
from unittest.mock import Mock, MagicMock

from book_bot.items import Item, Subject, Book 
from scrapy.selector.unified import Selector


@pytest.fixture
def selector():
    return Mock(spec=Selector)


class MyItem(Item):
    __keys__ = ['test']


class MyTestValue:
    def __init__(self, value: str):
        self.value = value

    def __str__(self):
        return self.value 


def test_book_parses_filename_from_url():
    filename = 'foo.txt'
    book = Book(download_url=f'/baz?{Book.qs_file_arg}={filename}')
    assert book['filename'] == filename


def test_subject_parses_name():
    subject = Subject(name='any - any - foo')
    assert subject['name'] == 'foo'


def test_item_default_processors(selector):
    selector.get = MagicMock(return_value=MyTestValue('\r\nfoo\t'))
    item = MyItem(test=[selector])
    selector.get.assert_called_once()
    assert item['test'] == 'foo'


def test_item_with_custom_input():
    expected = 'foo'
    item = MyItem()
    item.test_in = lambda v: expected
    item['test'] = 'baz'
    assert expected == item['test']


def test_item_with_custom_output():
    expected = 'foo'
    item = MyItem()
    item.test_out = lambda v: expected
    item['test'] = 'baz'
    assert expected == item['test']