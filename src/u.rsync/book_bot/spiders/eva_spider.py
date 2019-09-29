from urllib.parse import urlencode, urljoin
from getpass import getpass
from dataclasses import dataclass

import scrapy


@dataclass
class Subject:
    name: str
    class_id: str


@dataclass
class Book:
    name: str
    download_url: str


def auth_failed(response):
    return b'Login ou senha inv' in response.body


def get_credentials(user_key, pwd_key):
    # username, password = input('Username: '), getpass()
    with open('.login', 'r') as h:
        username, password = h.readlines()
    
    return {user_key: username.strip(), pwd_key: password.strip()}


def log_request(fn):
    def wrapper(cls, response):
        cls.logger.debug('response url: %s', response.url)
        cls.logger.debug('response status: %s', response.status)
        return fn(cls, response)
    return wrapper


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
        
        return self.open_req('/eadv4/login.processa',
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
        
        return self.open_req('/eadv4/listaDisciplina.processa', args=args, callback=self.parse_subjects)

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
        
        subjects = []
        def create_subject(index, subject_tree):
            class_id = subject_tree.xpath('.//a').attrib['data-turma_id']
            text = subject_tree.xpath('.//p//text()').get().strip()
            subjects.append(Subject(name=text, class_id=class_id))
            return text

        self._display_list('subject', subjects_tree, create_subject)

        args = dict(turmaIdSessao=subjects[0].class_id,
                    situacao=1,
                    tipoFiltro=0,
                    filtro='',
                    turmaAberta='true',
                    turmaFechada='false')

        return self.open_req('/eadv4/listaMidiatecas.processa', 
                            args=args,
                            callback=self.parse_books)

    @log_request
    def parse_books(self, response):
        books_tree = response.xpath("//div[@id='insereEspaco']/div")
        
        books = []
        def create_book(index, book_tree):
            name = book_tree.xpath('.//small//text()').get().strip()
            url = book_tree.xpath(".//a[@title='Download']").attrib['href']
            books.append(Book(name=name, download_url=url))
            return name

        self._display_list('book', books_tree, create_book)
        return self.open_req(books[0].download_url, callback=self.handle_downloads)

    @log_request
    def handle_download(self, response):
        with open('file', 'wb') as h:
            h.write(response.body)

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

    def open_req(self, url='', args=None, impl=scrapy.Request, **kwargs):
        if args is not None:
            query_st = '?' + urlencode(args).lstrip('?')
            url = urljoin(url, query_st)
        
        url = urljoin(EvaSpider.url, url)
        kwargs.setdefault('errback', self._errhandler)
        return impl(url, **kwargs)

    def _read_auth(self):
        return get_credentials(EvaSpider.username_arg, EvaSpider.password_arg)

    def _log_user(self, formdata, message):
        self.logger.info(message, formdata[EvaSpider.username_arg])

    def _errhandler(self, failure):
        self.logger.error(failure.getTraceback())
        self.logger.info(repr(failure))