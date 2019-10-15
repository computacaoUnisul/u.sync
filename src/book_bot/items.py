# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html
import os
from urllib.parse import parse_qs, unquote

import scrapy
from book_bot.utils import http
from scrapy.utils.url import urlparse
from scrapy.loader.processors import MapCompose, TakeFirst
from scrapy.selector.unified import Selector
from scrapy.item import Item
from scrapy.loader import ItemLoader


def default_field(*args):
    input_proc = MapCompose(first_when_list, parse_tree, str, *args, str.strip, remove_bad_chars)
    return scrapy.Field(
        input_processor=input_proc,
        output_processor=TakeFirst()
    )


def remove_bad_chars(value):
    return ' '.join(value.replace("\r\n", '').split())


def parse_tree(value):
    if isinstance(value, Selector):
        return value.get()
    return value


def first_when_list(value):
    if isinstance(value, list):
        return TakeFirst()(value)
    return value


def parse_subject_name(name):
    return name.split('-')[-1]


def maybe_getattr(cls, name, default=None):
    if hasattr(cls, name):
        return getattr(cls, name)
    return default


class NamedItem(Item):
    name = default_field()

    def __str__(self):
        return self['name']


class Subject(NamedItem):
    name = default_field(parse_subject_name)
    class_id = default_field()


class Book(NamedItem):
    download_url = default_field()
    filename = default_field(unquote)
    subject = scrapy.Field()

    qs_file_arg = 'arquivo'

    def __setitem__(self, key, value):
        super().__setitem__(key, value)
        if key == 'download_url' and self['download_url'] and not 'filename' in self:
            self.parse_filename()

    def parse_filename(self):
        query_st = urlparse(self['download_url']).query
        parsed_qs = parse_qs(query_st)
    
        if Book.qs_file_arg in parsed_qs:
            self.set_filename(parsed_qs[Book.qs_file_arg][0])
    
    def set_filename(self, filename):
        """Sets the filename processing input/output manually"""
        field = self.fields['filename']
        out_proc, in_proc = field['output_processor'], field['input_processor']
        self['filename'] = out_proc(in_proc(filename))


class MaxSubject(NamedItem):
    url = default_field()


class MaxBook(Book):
    def parse_filename(self):
        self.set_filename(os.path.basename(self['download_url']))
        

    