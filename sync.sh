#!/bin/sh

unset AUTH_FILE DOWNLOAD_DESTINATION KEEP_COOKIES
pushd src/

COOKIEJAR="${EVA_COOKIEJAR:-$(pwd)/.scrapy/cookies}"

while getopts 'kx:d:' option; do
    case $option in
        k) KEEP_COOKIES=1 ;;
        x) AUTH_FILE=$OPTARG ;;
        d) DOWNLOAD_DESTINATION=$OPTARG ;;
    esac
done

maybe_drop_cookies() {
    [ -z "$KEEP_COOKIES" ] && rm "$COOKIEJAR"
}

trap maybe_drop_cookies 0

AUTH_SCRIPT="scrapy crawl eva_login"
DOWNLOADER_SCRIPT="scrapy crawl books_downloader"

if [ -n "$AUTH_FILE" ]; then
    AUTH_SCRIPT+=" -a auth_file=${AUTH_FILE}"
fi

if [ -n "$DOWNLOAD_DESTINATION" ]; then
    DOWNLOADER_SCRIPT+=" -a destination=${DOWNLOAD_DESTINATION}"
fi

pushd book_bot/

$AUTH_SCRIPT && \
    chmod 640 ${COOKIEJAR} && \
    scrapy crawl subject_parser && \
    scrapy crawl book_parser && \
    $DOWNLOADER_SCRIPT 

scrapy crawl logout_eva
popd
popd