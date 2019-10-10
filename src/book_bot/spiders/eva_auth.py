import getpass

import scrapy
from book_bot.items import maybe_getattr
from book_bot.utils import http, os_files


def check_login(fn):
    def wrapper(cls, response):
        if LoginSpider.auth_failed(response):
            raise AuthenticationException()
        return fn(cls, response)
    return wrapper


def interative_login(fn):
    def wrapper(cls, retry):
        def interative_wrapper(response):
            try:
                return check_login(fn)(cls, response)
            except AuthenticationException as e:
                return retry(response)
        return interative_wrapper
    return wrapper


def get_credentials(file=None, username=None):
    if file:
        with open(file, 'r') as h:
            username, password = h.readlines()
    else:
        header = 'Username'
        if username:
            header += f' [{username}]'
        header += ': '
        username, password = input(header), getpass()
    return username.strip(), password.strip()


class AuthenticationException(Exception):
    def __init__(self, message='User is not authenticated.', **kwargs):
        super().__init__(message, **kwargs)


class LoginSpider(scrapy.Spider):
    name = 'eva_login'
    allowed_domains = 'unisul.br'

    # Cli arguments
    authentication_file = 'auth_file'

    # Request information
    username_arg = 'id_login'
    password_arg = 'id_senha'

    def start_requests(self):
        login_handler = self.after_login(self.retry_login)
        yield http.web_open(callback=login_handler)

    @interative_login
    @http.log_request
    def after_login(self, response):
        self.logger.info('logged in')

    def retry_login(self, response):
        self.logger.info('authentication failed')
        
        original_data = response.meta.get('creds', None)
        if original_data:
            del response.meta['creds']
            del response.request.meta['creds']
            self._log_user(original_data, 'last login with username: %s')
        
        self.logger.info('retrying login...')
        new_credentials = self._read_auth(default_dict=original_data)

        self._log_user(new_credentials, 'login attempt with user: %s')
        login_handler = self.after_login(self.retry_login)
        yield http.web_open('/login.processa',
                    callback=login_handler,
                    formdata=new_credentials,
                    dont_filter=True,
                    impl=scrapy.FormRequest)

    @staticmethod
    def auth_failed(response):
        body = response.body

        # text is bytes-like object
        user_key = LoginSpider.username_arg.encode()
        pwd_key = LoginSpider.password_arg.encode()
        has_ids = user_key in body and pwd_key in body
        has_js_redirect = b'eadv4/login/index.jsp' in body

        if 'redirect_reasons' in response.meta:
            redirect_statuses = response.meta['redirect_reasons']
            if redirect_statuses and redirect_statuses[-1] != 302:
                return False
        return has_ids or has_js_redirect

    def _build_creds(self, username, password, default_username=None):
        if not username and default_username:
            username = default_username
        return {LoginSpider.username_arg: username,
                LoginSpider.password_arg: password} 

    def _read_auth(self, default_dict=None):
        auth_file = maybe_getattr(self, LoginSpider.authentication_file)
        username = None
        if default_dict is not None and LoginSpider.username_arg in default_dict:
            username = default_dict[LoginSpider.username_arg]
        args = get_credentials(file=auth_file, username=username)
        return self._build_creds(*args, default_username=username)

    def _log_user(self, formdata, message):
        if LoginSpider.username_arg in formdata:
            self.logger.info(message, formdata[LoginSpider.username_arg])


class LogoutSpider(scrapy.Spider):
    name = 'logout_eva'

    def start_requests(self):
        yield http.web_open(callback=self.parse_home)

    def parse_home(self, response):
        logout_url = response.css('#icon-sair-perfil').xpath('.//following::a[1]/@href').get()
        if logout_url:
            return http.web_open(logout_url, callback=self.handle_exit)
        self.logger.debug('user already out!?')

    @http.log_request
    def handle_exit(self, response):
        self.logger.debug('logout redirects: %s', response.meta)
        self.logger.info('logged out')