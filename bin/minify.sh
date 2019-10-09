#!/bin/sh
if [ -z "$1" ]; then
    echo "Usage: src [dest]"
    exit 128
fi

SRC=${1}
DEST=${2}

if [ -z "$2" -o "$1" == "$2" ]; then
    DEST=${1}
    SRC=".${RANDOM}"
    
    rm_tmp() {
        rm "$SRC"
    }
    
    cat "$1" > "$SRC"
    trap rm_tmp EXIT
fi

(cat "$SRC" | tr -d '\n\t\r\b\f') > "$DEST"