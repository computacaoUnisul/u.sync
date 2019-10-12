import cgi
from urllib.parse import urlencode, urljoin

import scrapy


BASE_URL = 'https://www.uaberta.unisul.br/eadv4/'
EVA_DOMAIN = 'uaberta.unisul.br'
    

def save_response(filename):
    def wrapper(fn):
        def dumper(cls, response):
            download(filename, response)
            return fn(cls, response)
        return dumper
    return wrapper


def download(filename, response):
    with open(filename, 'wb') as file:
        file.write(response.body)


def web_open(url='', args=None, impl=scrapy.Request, base_url=BASE_URL, **kwargs):
    kwargs.setdefault('dont_filter', True)

    stripped_url = url.lstrip('/')
    url = f'{base_url}{stripped_url}'
        
    if args is not None:
        query_st = '?' + urlencode(args).lstrip('?')
        url = urljoin(url, query_st)
    return impl(url, **kwargs)


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