import os

import scrapy
from .eva_parser import BookSpider
from .eva_auth import check_login
from book_bot.items import BookLoader, maybe_getattr
from book_bot.utils import os_files, http 


class BookDownloaderSpider(scrapy.Spider):
    name = 'books_downloader'
    allowed_domains = 'unisul.br'

    # Cli arguments
    destination_directory = 'destination'

    def start_requests(self):
        yield http.web_open(callback=self.synchronize)

    @check_login
    def synchronize(self, response):
        content = os_files.load_sync_data(BookSpider.sync_file)
        def maybe_call_hook(method, args):
            self.logger.debug('looking for hook: %s', method)
            hook = maybe_getattr(self, method)
            if hook is not None:
                hook(args)

        for item in content:
            book_item = BookLoader.from_dict(item)
            self.logger.debug('analyzing book: %s', book_item)
            result = self._analyze_candidate(book_item) 

            if result is None:
                self.logger.info('skipping book: %s', book_item['name'])
                maybe_call_hook('book_skipped', book_item)
            else:
                self.logger.debug('downloading book: %s', book_item['name'])    
                maybe_call_hook('book_to_download', book_item)
                yield result

    def book_skipped(self, book):
        self.logger.info('SKIP WAS CALLED')
    
    def book_to_download(self, book):
        self.logger.info('WE ARE DOWNLOADING')

    @http.log_request
    def handle_download(self, response, book): 
        filename = http.parse_filename(response, default=book['filename'])
        dest_dir = self._get_book_path(book)
        file_path = os.path.join(dest_dir, filename)

        if os.path.exists(file_path): # check wheter file already exists
            return None

        os_files.maybe_create_dir(dest_dir)
        http.download(file_path, response)
        self.logger.info('book downloaded: %s', book['name'])

    def _analyze_candidate(self, book_item):
        assert 'download_url' in book_item, 'Book has missing download url'

        # weird behaviour, but we must ensure to skip these ones
        if book_item['download_url'] is None:
            return None

        if book_item['filename'] is None:    # show alert and try to download    
            self.logger.error('any filename found on URL, maybe URL uses another strategy?')
            self.logger.debug('we will attempt to download it anyway...')
        elif os.path.exists(self._get_book_path(book_item, book_item['filename'])):
            return None
    
        return http.web_open(book_item['download_url'], 
                        cb_kwargs={'book': book_item},
                        callback=self.handle_download)

    def _get_book_path(self, book_item, filename=''):
        return os.path.join(self._destination(), 
                            book_item['subject']['name'],
                            filename)
    
    def _destination(self, default='downloads'):
        return maybe_getattr(self, BookDownloaderSpider.destination_directory, 
                            default=default)