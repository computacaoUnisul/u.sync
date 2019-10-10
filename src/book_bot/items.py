# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html
from urllib.parse import parse_qs
from dataclasses import dataclass, field

from scrapy.http import Response
from scrapy.utils.url import urlparse
from scrapy.loader.processors import MapCompose, TakeFirst
from scrapy.selector.unified import Selector


def fieldNormalizer(*args):
    def parse_tree(argument):
        if isinstance(argument, Selector):
            return argument.get()
        return argument
    return MapCompose(parse_tree, str, *args, str.strip)


def flattenOutput(cls, value):
    if type(value) is list:
        return TakeFirst()(value)
    return value


def parse_subject_name(name):
    return name.split('-')[-1]


def maybe_getattr(cls, name, default=None):
    if hasattr(cls, name):
        return getattr(cls, name)
    return default


class Item(dict):
    __keys__ =  []
    __input_processor__ = fieldNormalizer()
    __output_processor__ = flattenOutput

    def __init__(self, **kwargs):
        super().__init__()
        for key, value in kwargs.items():
            self.__setitem__(key, value)

    def _get_processor(self, suffix, key, default):
        processor = maybe_getattr(self, f'{key}{suffix}')
        if processor is None:
            processor = default
        return processor

    def __setitem__(self, key, value):
        if key in self.__keys__:
            processor = self._get_processor('_in', key, self.__input_processor__)
            super().__setitem__(key, processor(value))
        else:
            raise KeyError(f'Invalid key {key}.')
    
    def __getitem__(self, key):
        value = super().__getitem__(key)
        processor = self._get_processor('_out', key, self.__output_processor__)
        return processor(value)


class Subject(Item):
    __keys__ = ['name', 'class_id']

    # custom processor for name
    name_in = fieldNormalizer(parse_subject_name)


class Book(Item):
    __keys__ = ['name', 'download_url', 'filename', 'subject']
    
    subject_in = lambda cls, s: s # passthrough
    qs_file_arg = 'arquivo'

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if key == 'download_url' and self['download_url']:
            query_st = urlparse(self['download_url']).query
            parsed_qs = parse_qs(query_st)
        
            if Book.qs_file_arg in parsed_qs:
                self['filename'] = parsed_qs[Book.qs_file_arg][0]
            else:
                self['filename'] = None 


@dataclass
class SubjectLoader:
    subjects: list = field(default_factory=list)

    def get_tree(self, response: Response):
        return response.xpath("//div[@id='grad']/div[1]/div[1]/div[1]/div")

    @staticmethod
    def from_dict(data: dict):
        return Subject(name=data['name'], class_id=data['class_id'])

    def __call__(self, index, subject_tree):
        s = Subject()
        s['class_id'] = subject_tree.xpath('.//a/@data-turma_id')
        s['name'] = subject_tree.xpath('.//p/text()')
        self.subjects.append(s)
        return s['name']


@dataclass
class BookLoader:
    subject: Subject
    books: list = field(default_factory=list)

    def get_tree(self, response: Response):
        return response.xpath("//div[@id='insereEspaco']/div")

    @staticmethod
    def from_dict(data: dict):
        subject = SubjectLoader.from_dict(data['subject'])
        return Book(name=data['name'], 
                    download_url=data['download_url'], 
                    filename=data['filename'],
                    subject=subject)

    def __call__(self, index, book_tree):
        b = Book(subject=self.subject)
        b['name'] = book_tree.xpath('.//small//text()')
        b['download_url'] = book_tree.xpath(".//a[@title='Download']/@href")
        self.books.append(b)
        return b['name']
    