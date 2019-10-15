import os

import scrapy
from .eva_parser import BookSpider
from .eva_auth import check_login
from book_bot.loaders import BookLoader
from book_bot.utils import os_files, http
from scrapy.utils.project import project_data_dir 


class BookDownloaderSpider(scrapy.Spider):
    name = 'books_downloader'
    allowed_domains = http.EVA_DOMAIN

    custom_settings = {
        'DOWNLOAD_TIMEOUT': 1200,
        'CONCURRENT_REQUESTS_PER_DOMAIN': 100,
        'CONCURRENT_REQUESTS': 100,
        
        'FILES_STORE': os.path.join(project_data_dir(), 'downloads'),
        'ITEM_PIPELINES': {
            'book_bot.pipelines.SyncPipeline': 100,
        },
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        assert hasattr(self, 'book_uri'), 'Missing argument: book_uri' 

    @classmethod
    def from_crawler(cls, crawler):
        spider = cls(
            book_uri=crawler.settings.get('BOOK_EXPORTER_URI')
        )
        spider.crawler = crawler
        return spider

    def start_requests(self):
        yield http.web_open(callback=self.synchronize)

    @check_login
    def synchronize(self, response):
        for item in self.load_books():
            book_item = self.dict_to_book(item)
            download_url = book_item['download_url'] 
            
            # normalize url when not full-url
            if not response.url in download_url:
                book_item['download_url'] = response.urljoin(book_item['download_url'])
            yield book_item

    def dict_to_book(self, data: dict):
        return BookLoader.from_dict(data)

    def load_books(self):
        return os_files.load_sync_data(self.book_uri)