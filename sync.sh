#!/bin/sh

unset AUTH_FILE DOWNLOAD_DESTINATION KEEP_ONLINE SPIDER_MAX CLEAN_OLD_RUN
pushd src/ > /dev/null

COOKIEJAR="${EVA_COOKIEJAR:-$(pwd)/.scrapy/cookies}"

print_help_line() {
    printf "\t${1} (${2})\n" 1>&2
}

show_usage() {
    echo "Usage: [-kmc] [-x AUTH_FILE] [-d DESTINATION_DIR]" 1>&2
    print_help_line '-k' 'Indicates wheter to keep account online'
    print_help_line '-m' "Run max spider, don't need authentication"
    print_help_line '-c' 'Removes old synchronize run'
    print_help_line '-x' 'Specifies the file with username/password'
    print_help_line '-d' 'Specifies the directory to sync'
    exit 128
}

while getopts 'hkmcx:d:' option; do
    case $option in
        k) KEEP_ONLINE=1 ;;
        x) AUTH_FILE=$OPTARG ;;
        d) DOWNLOAD_DESTINATION=$OPTARG ;;
        m) SPIDER_MAX=1 ;;
        c) CLEAN_OLD_RUN=1 ;;
        h) show_usage ;;
        *) show_usage ;;
    esac
done

maybe_drop_account() {
    pushd src/book_bot/ > /dev/null
    if [[ -z is_max_run && -z $KEEP_ONLINE ]]; then 
        scrapy crawl logout_eva
        rm "$COOKIEJAR"
    fi
    popd > /dev/null
}

is_max_run() {
    [ -n "$SPIDER_MAX" ]
}

trap maybe_drop_account 0

DOWNLOADER_SCRIPT="scrapy crawl "

if is_max_run; then
    DOWNLOADER_SCRIPT+="max_books_downloader"
else
    DOWNLOADER_SCRIPT+="books_downloader"
fi

if [ -n "$DOWNLOAD_DESTINATION" ]; then
    DOWNLOADER_SCRIPT+=" -a destination=${DOWNLOAD_DESTINATION}"
fi

pushd book_bot/

# maybe clean last run
[ -n "$CLEAN_OLD_RUN" ] && rm -rf .sync/

if is_max_run; then
    scrapy crawl max_subject_parser && \
        scrapy crawl max_book_parser
else
    AUTH_SCRIPT="scrapy crawl eva_login"
  
    if [ -n "$AUTH_FILE" ]; then
        AUTH_SCRIPT+=" -a auth_file=${AUTH_FILE}"
    fi

    $AUTH_SCRIPT && \
        chmod 640 ${COOKIEJAR} && \
        scrapy crawl subject_parser && \
        scrapy crawl book_parser
fi

$DOWNLOADER_SCRIPT

popd ; popd > /dev/null