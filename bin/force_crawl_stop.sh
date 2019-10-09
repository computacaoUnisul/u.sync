#!/bin/sh
kill -9 $(ps aux | grep python3 | grep scrapy | awk '{printf $2}')