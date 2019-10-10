from getpass import getpass
from urllib.parse import urlencode, urljoin
import os
import cgi
import secrets
import json

from .eva_auth import LoginSpider, check_login
from book_bot.items import SubjectLoader, BookLoader, MaxSubjectLoader, maybe_getattr
from book_bot.utils import http, os_files
import scrapy


def _display_and_load(spider, name, tree, callback):
    tree_length = len(tree)
    assert tree_length, f'{name.capitalize()}(s) are empty.'
    
    spider.logger.debug(f'{name} received: %s', tree)  
    spider.logger.info(f'number of {name}(s) found: %d', tree_length)
    
    listing = f'listing of {name}(s):\n'
    for index, item_tree in enumerate(tree):
        text = callback(index, item_tree)
        listing += f'{index + 1} - {text}\n'
    spider.logger.info(listing)


class SubjectSpider(scrapy.Spider):
    name = 'subject_parser'
    allowed_domains = 'unisul.br'

    sync_file = 'subjects.json'

    subject_args = dict(turmaIdSessao=-1,
                        situacao="C",
                        turmaId=-1,
                        disciplinaId=-1,
                        confirmacao=0,
                        subMenu="",
                        ferramenta="")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subjects = os_files.load_sync_data(SubjectSpider.sync_file, default=[])

    def start_requests(self):
        yield http.web_open('/listaDisciplina.processa',
                    args=SubjectSpider.subject_args, 
                    callback=self.parse_subjects)

    @http.log_request
    @check_login
    def parse_subjects(self, response):
        loader = SubjectLoader()
        _display_and_load(self, 'subject', loader.get_tree(response), loader)
        self.logger.debug(loader.subjects)
        self.subjects.extend(loader.subjects)

    def closed(self, reason):
        os_files.dump_sync_data(SubjectSpider.sync_file, self.subjects)


class BookSpider(scrapy.Spider):
    name = 'book_parser'
    allowed_domains = 'unisul.br'

    sync_file = 'books.json'

    book_args = dict(situacao=1,
                    tipoFiltro=0,
                    turmaAberta='true',
                    turmaFechada='false')

    books = []
    subjects_content = []

    def start_requests(self):
        self.subjects_content = os_files.load_sync_data(SubjectSpider.sync_file)
        request = self.sync_next_subject()
        if request is not None:
            yield request 

    def sync_next_subject(self):
        self.logger.debug(self.subjects_content)
        if self.subjects_content:
            item = self.subjects_content.pop()
            subject = SubjectLoader.from_dict(item)
            self.logger.debug('reading subject: %s', subject['name'])
            args = self._get_book_args(subject)
            return http.web_open('/listaMidiatecas.processa', 
                                meta={'subject': subject},
                                args=args,
                                callback=self.parse_books)

    @http.log_request
    @check_login
    def parse_books(self, response):
        assert 'subject' in response.meta, 'Main subject was not provided.'
        subject = response.meta['subject']
        self.logger.debug('subject: %s', subject)
        loader = BookLoader(subject=subject)
        _display_and_load(self, 'book', loader.get_tree(response), loader)
        self.logger.debug(loader.books)
        self.books.extend(loader.books)
        request = self.sync_next_subject()
        if request is not None:
            return request

    def closed(self, reason):
        os_files.dump_sync_data(BookSpider.sync_file, self.books)
    
    def _get_book_args(self, subject_item):
        new_args = BookSpider.book_args
        new_args['turmaIdSessao'] = subject_item['class_id']
        return new_args


class MaxPageSpider(SubjectSpider):
    name = 'max_subject_parser'
    allowed_domains = 'paginas.unisul.br'

    def start_requests(self):
        url = 'http://paginas.unisul.br/max.pereira/horario.htm'
        yield http.web_open(base_url=url, callback=self.parse_schedule)
        
    def parse_schedule(self, response):
        subject_loader = MaxSubjectLoader()
        _display_and_load(self, 'subject', subject_loader.get_tree(response), subject_loader)
        self.logger.debug(subject_loader) 
        self.subjects.extend(subject_loader.subjects)