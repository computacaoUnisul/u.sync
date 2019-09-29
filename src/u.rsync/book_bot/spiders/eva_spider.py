import os
import cgi
from urllib.parse import urlencode, urljoin, urlparse, parse_qs
from getpass import getpass
from dataclasses import dataclass, field

import scrapy
from book_bot.items import Subject, Book
from scrapy.loader import ItemLoader


def auth_failed(response):
    return b'Login ou senha inv' in response.body


def get_credentials(user_key, pwd_key, file=None):
    if file:
        with open(file, 'r') as h:
            username, password = h.readlines()
    else:
        username, password = input('Username: '), getpass()
    
    return {user_key: username.strip(), pwd_key: password.strip()}


def log_request(fn):
    def wrapper(cls, response, **kwargs):
        cls.logger.debug('response url: %s', response.url)
        cls.logger.debug('response status: %s', response.status)
        return fn(cls, response, **kwargs)
    return wrapper


def parse_filename(response, default=None):
    if 'content-disposition' in response.headers:
        disposition_header = response.headers['content-disposition'].decode('utf-8')
        attachment = cgi.parse_header(disposition_header)
        if attachment[0] != 'attachment':
            raise FileNotFoundError('Invalid response header.') 
        return attachment[1]['filename']
    return default

@dataclass
class SubjectLoader:
    subjects: list = field(default_factory=list)

    def __call__(self, index, subject_tree):
        loader = ItemLoader(item=Subject(), selector=subject_tree)
        loader.add_xpath('class_id', './/a/@data-turma_id')
        loader.add_xpath('name', './/p//text()')
        
        item = loader.load_item()
        self.subjects.append(item)
        return item['name']


@dataclass
class BookLoader:
    books: list = field(default_factory=list)

    def __call__(self, index, book_tree):
        loader = ItemLoader(item=Book(), selector=book_tree)
        loader.add_xpath('name', './/small//text()')
        loader.add_xpath('download_url', ".//a[@title='Download']/@href")
        
        item = loader.load_item()
        self.books.append(item)
        return item['name']


class EvaSpider(scrapy.Spider):
    name = 'eva'

    # URLs
    url = 'https://www.uaberta.unisul.br'

    # Request information
    username_arg = 'id_login'
    password_arg = 'id_senha'

    def start_requests(self):
        credentials = self._read_auth()
        yield self.get_login_req(credentials)

    def get_login_req(self, credentials):
        self._log_user(credentials, 'login attempt with user: %s')
        
        return self._open_req('/eadv4/login.processa',
                            callback=self.after_login,
                            formdata=credentials,
                            meta={'creds': credentials},
                            dont_filter=True,
                            impl=scrapy.FormRequest)

    def after_login(self, response):
        self.logger.debug('received login response: %s', repr(response))

        if auth_failed(response):
            return self.retry_login(response.request)
        self.logger.info('logged in')
        
        # not too sure about this parameters
        args = dict(turmaIdSessao=-1,
                    situacao="C",
                    turmaId=-1,
                    disciplinaId=-1,
                    confirmacao=0,
                    subMenu="",
                    ferramenta="")
        
        return self._open_req('/eadv4/listaDisciplina.processa', 
                            args=args, 
                            callback=self.parse_subjects)

    def retry_login(self, request):
        self.logger.info('authentication failed')
        
        original_data = request.meta['creds']
        self._log_user(original_data, 'last login with username: %s')
        
        self.logger.info('retrying login...')
        new_credentials = self._read_auth()
        
        for key, value in original_data.items():
            new_credentials.setdefault(key, value)

        return self.get_login_req(new_credentials)

    @log_request
    def parse_subjects(self, response):
        subjects_tree = response.xpath("//div[@id='grad']/div[1]/div[1]/div[1]/div")
        
        loader = SubjectLoader()
        self._display_list('subject', subjects_tree, loader)
        
        args = dict(situacao=1,
                    tipoFiltro=0,
                    filtro='',
                    turmaAberta='true',
                    turmaFechada='false')

        for subject_item in loader.subjects:
            args['turmaIdSessao'] = subject_item['class_id']
            self.logger.debug('reading subject: %s', subject_item['name'])
            yield self._open_req('/eadv4/listaMidiatecas.processa', 
                                args=args,
                                callback=self.parse_books)

    @log_request
    def parse_books(self, response):
        books_tree = response.xpath("//div[@id='insereEspaco']/div")
        
        loader = BookLoader()
        self._display_list('book', books_tree, loader)

        for book_item in loader.books:
            self.logger.debug('analyzing book: %s', book_item)
            query_st = urlparse(book_item['download_url']).query
            qs = parse_qs(query_st)
            filename = qs['arquivo'][0] if 'arquivo' in qs else None

            if filename is None:    # nothing to do here    
                self.logger.error('any filename found on URL, maybe another strategy?')
                self.logger.debug('we will attempt to download it anyway...')
            else:
                if self._file_exists(filename):
                    self.logger.info('skipping book: %s', book_item['name'])
                    continue

            self.logger.debug('downloading book: %s', book_item['name'])
            
            download_kwargs = {'book_name': book_item['name'], 
                                'fallback_filename': filename}
            
            yield self._open_req(book_item['download_url'], 
                                cb_kwargs=download_kwargs,
                                callback=self.handle_download)

    @log_request
    def handle_download(self, response, book_name, fallback_filename): 
        filename = parse_filename(response, default=fallback_filename)
        if self._file_exists(filename): # check wheter file already exists
            return None

        directory = self._destination()
        if not (os.path.exists(directory) or os.path.isdir(directory)):
            os.mkdir(directory)

        with open(os.path.join(directory, filename), 'wb') as handler:
            handler.write(response.body)
        self.logger.info('book downloaded: %s', book_name)

    def _display_list(self, name, tree, callback):
        tree_length = len(tree)
        if not tree_length:
            raise Exception(f'{name.capitalize()}(s) are empty.')
        
        self.logger.debug(f'{name} received: %s', tree)  
        self.logger.info(f'number of {name}(s) found: %d', tree_length)
        
        listing = f'listing of {name}(s):\n'
        for index, item_tree in enumerate(tree):
            text = callback(index, item_tree)
            listing += f'{index + 1} - {text}\n'
        self.logger.info(listing)

    def _open_req(self, url='', args=None, impl=scrapy.Request, **kwargs):
        if args is not None:
            query_st = '?' + urlencode(args).lstrip('?')
            url = urljoin(url, query_st)
        
        url = urljoin(EvaSpider.url, url)
        kwargs.setdefault('errback', self._errhandler)
        return impl(url, **kwargs)

    def _destination(self, default='downloads'):
        return getattr(self, 'destination', default)

    def _file_exists(self, filename):
        destination = os.path.join(self._destination(), filename)
        return os.path.exists(destination)

    def _read_auth(self):
        return get_credentials(EvaSpider.username_arg, 
                                EvaSpider.password_arg,
                                file=getattr(self, 'auth_file'))

    def _log_user(self, formdata, message):
        self.logger.info(message, formdata[EvaSpider.username_arg])

    def _errhandler(self, failure):
        self.logger.error(failure.getTraceback())
        self.logger.info(repr(failure))