import scrapy
from .eva_auth import LoginSpider, check_login
from book_bot.items import maybe_getattr
from book_bot.utils import http, os_files
from book_bot.loaders import SubjectLoader, BookLoader


def _display_and_load(spider, name, response, loader):
    tree = loader.get_tree(response)
    tree_length = len(tree)
    assert tree_length, f'{name.capitalize()}(s) are empty.'
    
    spider.logger.debug(f'{name} received: %s', tree)  
    spider.logger.info(f'number of {name}(s) found: %d', tree_length)
    
    listing = f'listing of {name}(s):\n'
    index = 0
    for item_tree in tree:
        item = loader(item_tree)
        if item:
            index += 1
            listing += f'{index} - {item}\n'
            yield item
    spider.logger.info(listing)


class SubjectSpider(scrapy.Spider):
    name = 'subject_parser'
    allowed_domains = http.EVA_DOMAIN

    custom_settings = {
        'ITEM_PIPELINES': {
            'book_bot.pipelines.SubjectExportPipeline': 100
        }
    }

    subject_args = dict(turmaIdSessao=-1,
                        situacao="C",
                        turmaId=-1,
                        disciplinaId=-1,
                        confirmacao=0,
                        subMenu="",
                        ferramenta="")

    def start_requests(self):
        yield http.web_open('/listaDisciplina.processa',
                            args=SubjectSpider.subject_args, 
                            callback=self.parse_subjects)

    @http.log_request
    @check_login
    def parse_subjects(self, response):
        return _display_and_load(self, 
                                'subject', 
                                response, 
                                SubjectLoader())


class BookSpider(scrapy.Spider):
    name = 'book_parser'
    allowed_domains = http.EVA_DOMAIN

    custom_settings = {
        'CONCURRENT_REQUESTS': 1, # fix overlap during crawl
        'ITEM_PIPELINES': {
            'book_bot.pipelines.BookExportPipeline': 100
        }
    }

    book_args = dict(situacao=1,
                    tipoFiltro=0,
                    turmaAberta='true',
                    turmaFechada='false')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert hasattr(self, 'subject_uri'), 'Missing argument: subject_uri'

    @classmethod
    def from_crawler(cls, crawler):
        return cls(
            subject_uri=crawler.settings.get('SUBJECT_EXPORTER_URI')
        )

    def start_requests(self):
        for item in self.load_subjects():
            subject = SubjectLoader.from_dict(item)
            self.logger.debug('reading subject: %s', subject['name'])
            args = self._get_book_args(subject)
            yield http.web_open('/listaMidiatecas.processa', 
                                meta={'subject': subject},
                                args=args,
                                callback=self.parse_books)

    @http.log_request
    @check_login
    def parse_books(self, response):
        assert 'subject' in response.meta, 'Main subject was not provided.'
        subject = response.meta['subject']
        self.logger.debug('subject: %s', subject)
        return _display_and_load(self, 
                                'book', 
                                response, 
                                self.get_loader(subject))

    def load_subjects(self):
        return os_files.load_sync_data(self.subject_uri)

    def get_loader(self, subject):
        return BookLoader(subject=subject)
    
    def _get_book_args(self, subject_item):
        new_args = BookSpider.book_args
        new_args['turmaIdSessao'] = subject_item['class_id']
        return new_args