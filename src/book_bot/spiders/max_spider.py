from .eva_parser import SubjectSpider, BookSpider, _display_and_load
from .sync_spider import BookDownloaderSpider
from .eva_auth import LoginSpider
from book_bot.items import Item, SubjectLoader, Book, BookLoader, field_normalizer
from book_bot.utils import http, os_files


MAX_BASE_URL = 'http://paginas.unisul.br/max.pereira/'
UNISUL_PAGES_DOMAIN = 'paginas.unisul.br'


def remove_bad_chars(value):
    return ' '.join(value.replace("\r\n", '').split())


class MaxSubjectParser(SubjectSpider):
    name = 'max_subject_parser'
    allowed_domains = UNISUL_PAGES_DOMAIN

    def start_requests(self):
        yield http.web_open(url='/horario.htm', 
                            base_url=MAX_BASE_URL, 
                            callback=self.parse_schedule)
        
    def parse_schedule(self, response):
        subject_loader = MaxSubjectLoader()
        _display_and_load(self, 'subject', subject_loader.get_tree(response), subject_loader)
        self.logger.debug(subject_loader) 
        self.subjects.extend(subject_loader.subjects)


class MaxBookParser(BookSpider):
    name = 'max_book_parser'
    allowed_domains = UNISUL_PAGES_DOMAIN

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        all_subjects = os_files.load_sync_data(SubjectSpider.sync_file)
        max_subjects = filter(lambda s: 'url' in s, all_subjects)
        self.subjects_content = list(max_subjects)

    def sync_next_subject(self):
        self.logger.debug(self.subjects_content)
        if self.subjects_content:
            item = self.subjects_content.pop()
            subject = MaxSubjectLoader.from_dict(item)
            self.logger.debug('reading subject: %s', subject['name'])
            return http.web_open(subject['url'], 
                                meta={'subject': subject},
                                base_url=MAX_BASE_URL,
                                callback=self.parse_books)

    def parse_books(self, response):
        try:
            return super().parse_books(response)
        except AssertionError:
            if 'subject' in response.meta and response.meta['subject']:
                subject = response.meta['subject']
                self.logger.info('subject [%s] has any books', subject['name'])
            return self.start_requests() # restart requests

    def get_loader(self, subject):
        return MaxBookLoader(subject=subject)


class MaxSyncDownloader(BookDownloaderSpider):
    name = 'max_books_downloader'
    allowed_domains = UNISUL_PAGES_DOMAIN

    def start_requests(self):
        # we must fake the authentication on each loop
        LoginSpider.fake_auth()
        return super().start_requests()

    def dict_to_book(self, data):
        return MaxBookLoader.from_dict(data)

    def build_download_request(self, book):
        return http.web_open(book['download_url'],
                            cb_kwargs={'book': book},
                            base_url=MAX_BASE_URL,
                            callback=self.handle_download)

    def load_books(self):
        all_books = super().load_books()
        max_books = filter(lambda b: 'url' in b['subject'], all_books)
        return list(max_books)

    
class MaxSubject(Item):
    __keys__ = ['name', 'url']


class MaxBook(Book):
    name_in = field_normalizer(remove_bad_chars)
    
    def set_filename(self):
        download_url = self['download_url']
        # normalize url when full-urls
        if MAX_BASE_URL in download_url:
            stripped_url = download_url.replace(MAX_BASE_URL, '').lstrip('/')
            self['download_url'] = stripped_url
        self['filename'] = self['download_url']


class MaxSubjectLoader(SubjectLoader):
    def get_tree(self, response):
        night_subjects = response.xpath('//table[2]/tbody[1]/tr[last()]/td')
        del night_subjects[0]
        return night_subjects
    
    @staticmethod
    def from_dict(data):
        return MaxSubject(name=data['name'], url=data['url'])

    def __call__(self, index, subject_tree):
        s = MaxSubject()
        s['url'] = subject_tree.xpath('.//a[1]/@href')
        s['name'] = subject_tree.xpath('.//text()')
        self.subjects.append(s)
        return s['name']


class MaxBookLoader(BookLoader):
    def get_tree(self, response):
        books = response.xpath('/html/body/table/tbody/tr')
        if len(books):
            del books[0]
        return books

    @staticmethod
    def from_dict(data: dict):
        subject = MaxSubjectLoader.from_dict(data['subject'])
        return Book(name=data['name'], 
                    download_url=data['download_url'], 
                    filename=data['filename'],
                    subject=subject)

    def __call__(self, index, book_tree):
        b = MaxBook(subject=self.subject)
        link_xpath = './/td[last()]/a[1]'
        b['download_url'] = book_tree.xpath(f'{link_xpath}/@href')
        b['name'] = book_tree.xpath(f'{link_xpath}/text()')
        if b['download_url']:
            self.books.append(b)
            return b['name']