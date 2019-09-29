# -*- coding: utf-8 -*-

# Define here the models for your scraped items
#
# See documentation in:
# https://docs.scrapy.org/en/latest/topics/items.html

import scrapy
from scrapy.loader.processors import TakeFirst, MapCompose


def fieldNormalizer(*args):
    processor = MapCompose(str.strip, *args)
    return scrapy.Field(input_processor=processor, 
                        output_processor=TakeFirst())


class Subject(scrapy.Item):
    name = fieldNormalizer()
    class_id = fieldNormalizer()


class Book(scrapy.Item):
    name = fieldNormalizer()
    download_url = fieldNormalizer()