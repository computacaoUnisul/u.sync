import scrapy
from .eva_parser import BookSpider, _display_and_load
from .sync_spider import BookDownloaderSpider
from .eva_auth import LoginSpider
from book_bot.loaders import MaxSubjectLoader, MaxBookLoader
from book_bot.utils import http


class MaxSubjectParser(scrapy.Spider):
    name = 'max_subject_parser'
    allowed_domains = http.UNISUL_PAGES_DOMAIN

    custom_settings = {
        'ITEM_PIPELINES': {
            'book_bot.pipelines.MaxSubjectExportPipeline': 100
        }
    }

    def start_requests(self):
        yield http.web_open(url='/horario.htm', 
                            base_url=http.MAX_BASE_URL, 
                            callback=self.parse_schedule)
        
    def parse_schedule(self, response):
        return _display_and_load(self, 
                                'subject', 
                                response, 
                                MaxSubjectLoader())


class MaxBookParser(BookSpider):
    name = 'max_book_parser'
    allowed_domains = http.UNISUL_PAGES_DOMAIN

    def start_requests(self):
        for item in self.load_subjects():
            subject = MaxSubjectLoader.from_dict(item)
            self.logger.debug('reading subject: %s', subject['name'])
            yield http.web_open(subject['url'], 
                                meta={'subject': subject},
                                base_url=http.MAX_BASE_URL,
                                callback=self.parse_books)

    def parse_books(self, response):
        try:
            return super().parse_books(response)
        except AssertionError:
            if 'subject' in response.meta and response.meta['subject']:
                subject = response.meta['subject']
                self.logger.info('subject [%s] has any books', subject['name'])

    def get_loader(self, subject):
        return MaxBookLoader(subject=subject)


class MaxSyncDownloader(BookDownloaderSpider):
    name = 'max_books_downloader'
    allowed_domains = http.UNISUL_PAGES_DOMAIN

    def start_requests(self):
        # we must fake the authentication, sounds bad...
        LoginSpider.fake_auth()
        yield http.web_open(base_url=http.MAX_BASE_URL, callback=self.synchronize)

    def dict_to_book(self, data: dict):
        return MaxBookLoader.from_dict(data)