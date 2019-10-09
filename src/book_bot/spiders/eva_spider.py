import os
import cgi
import secrets
from getpass import getpass
from urllib.parse import urlencode, urljoin

import scrapy
from book_bot.items import SubjectLoader, BookLoader, maybe_getattr


def get_credentials(file=None):
    if file:
        with open(file, 'r') as h:
            username, password = h.readlines()
    else:
        username, password = input('Username: '), getpass()
    return username.strip(), password.strip()


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


class EvaSpider(scrapy.Spider):
    name = 'eva'

    # URLs
    url = 'https://www.uaberta.unisul.br'

    # Cli arguments
    authentication_file = 'auth_file'
    destination_directory = 'destination'

    # Request information
    username_arg = 'id_login'
    password_arg = 'id_senha'

    subject_args = dict(turmaIdSessao=-1,
                        situacao="C",
                        turmaId=-1,
                        disciplinaId=-1,
                        confirmacao=0,
                        subMenu="",
                        ferramenta="")

    book_args = dict(situacao=1,
                    tipoFiltro=0,
                    filtro='',
                    turmaAberta='true',
                    turmaFechada='false')


    def start_requests(self):
        credentials = self._read_auth()
        yield self._get_login_req(credentials)

    def after_login(self, response):
        self.logger.debug('received login response: %s', repr(response))

        if self._auth_failed(response):
            return self.retry_login(response.request)
        self.logger.info('logged in')
        
        return self._open_req('/eadv4/listaDisciplina.processa', 
                            args=EvaSpider.subject_args, 
                            callback=self.parse_subjects)

    def retry_login(self, request):
        self.logger.info('authentication failed')
        
        original_data = request.meta['creds']
        self._log_user(original_data, 'last login with username: %s')
        
        self.logger.info('retrying login...')
        new_credentials = self._read_auth()
        
        for key, value in original_data.items():
            if not new_credentials[key]:
                new_credentials[key] = value

        return self._get_login_req(new_credentials)

    @log_request
    def parse_subjects(self, response):
        loader = SubjectLoader()
        self._display_and_load('subject', loader.get_tree(response), loader)

        for subject_item in loader.subjects:
            self.logger.debug('reading subject: %s', subject_item['name'])
            args = self._get_book_args(subject_item)
            yield self._open_req('/eadv4/listaMidiatecas.processa', 
                                meta={'subject': subject_item},
                                args=args,
                                callback=self.parse_books)

    @log_request
    def parse_books(self, response):
        assert 'subject' in response.meta, 'Main subject was not provided.'

        loader = BookLoader(subject=response.meta['subject'])
        self._display_and_load('book', loader.get_tree(response), loader)

        def maybe_call_hook(method, args):
            self.logger.debug('looking for hook: %s', method)
            hook = maybe_getattr(self, method)
            if hook is not None:
                hook(args)

        for book_item in loader.books:
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

    @log_request
    def handle_download(self, response, book): 
        filename = parse_filename(response, default=book['filename'])
        # if filename is None:
        #     filename = secrets.token_hex(16)
        #     self.logger.error('downloading unamed file, saving to: %s', filename)
        #     self.logger.debug('unknow book: %s', book)
            
        #     # set destination on top of directory
        #     dest_dir = self._destination()
        # else:
        #     dest_dir = self._get_book_path(book)

        dest_dir = self._get_book_path(book)
        file_path = os.path.join(dest_dir, filename)
        if os.path.exists(file_path): # check wheter file already exists
            return None

        if not (os.path.exists(dest_dir) or os.path.isdir(dest_dir)):
            os.makedirs(dest_dir)

        with open(file_path, 'wb') as handler:
            handler.write(response.body)
        self.logger.info('book downloaded: %s', book['name'])

    def _build_creds(self, username, password):
        return {EvaSpider.username_arg: username,
                EvaSpider.password_arg: password}

    def _get_book_args(self, subject_item):
        new_args = EvaSpider.book_args
        new_args['turmaIdSessao'] = subject_item['class_id']
        return new_args

    def _get_book_path(self, book_item, filename=''):
        return os.path.join(self._destination(), 
                            book_item['subject']['name'],
                            filename)

    def _auth_failed(self, response):
        body = response.body

        # text is bytes-like object
        user_key = EvaSpider.username_arg.encode()
        pwd_key = EvaSpider.password_arg.encode()
        return user_key in body and pwd_key in body 

    def _display_and_load(self, name, tree, callback):
        tree_length = len(tree)
        assert tree_length, f'{name.capitalize()}(s) are empty.'
        
        self.logger.debug(f'{name} received: %s', tree)  
        self.logger.info(f'number of {name}(s) found: %d', tree_length)
        
        listing = f'listing of {name}(s):\n'
        for index, item_tree in enumerate(tree):
            text = callback(index, item_tree)
            listing += f'{index + 1} - {text}\n'
        self.logger.info(listing)

    def _open_req(self, url='', args=None, impl=scrapy.Request, **kwargs):
        kwargs.setdefault('dont_filter', True)
        if args is not None:
            query_st = '?' + urlencode(args).lstrip('?')
            url = urljoin(url, query_st)
        
        url = urljoin(EvaSpider.url, url)
        kwargs.setdefault('errback', self._errhandler)
        return impl(url, **kwargs)

    def _get_login_req(self, credentials):
        self._log_user(credentials, 'login attempt with user: %s')
        
        return self._open_req('/eadv4/login.processa',
                            callback=self.after_login,
                            formdata=credentials,
                            meta={'creds': credentials},
                            dont_filter=True,
                            impl=scrapy.FormRequest)

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

        return self._open_req(book_item['download_url'], 
                            cb_kwargs={'book': book_item},
                            callback=self.handle_download)

    def _destination(self, default='downloads'):
        return maybe_getattr(self, EvaSpider.destination_directory, default=default)

    def _read_auth(self):
        auth_file = maybe_getattr(self, EvaSpider.authentication_file)
        args = get_credentials(file=auth_file)
        return self._build_creds(*args)

    def _log_user(self, formdata, message):
        self.logger.info(message, formdata[EvaSpider.username_arg])

    def _errhandler(self, failure):
        self.logger.error(failure.getTraceback())
        self.logger.info(repr(failure))