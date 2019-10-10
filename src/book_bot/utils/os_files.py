import os
import json


def maybe_create_dir(directory):
    if not (os.path.exists(directory) or os.path.isdir(directory)):
        os.makedirs(directory)


def dump_sync_data(filename, data):
    maybe_create_dir('.sync')
    with open(os.path.join('.sync', filename), 'w') as file:
        file.write(json.dumps(data))


def load_sync_data(filename):
    with open(os.path.join('.sync', filename), 'rb') as file:
        return json.load(file)