import os
import json


def file_exists(directory, filename):
    return os.path.exists(os.path.join(directory, filename))


def maybe_create_dir(directory):
    if not (os.path.exists(directory) or os.path.isdir(directory)):
        os.makedirs(directory)


def open_sync_file(filename, mode):
    return open(os.path.join('.sync', filename), mode) 


def dump_sync_data(filename, data):
    maybe_create_dir('.sync')
    with open_sync_file(filename, 'w') as file:
        file.write(json.dumps(data, indent=2))


def load_sync_data(filename, default=[]):
    if not file_exists('.sync', filename):
        return default
    with open_sync_file(filename, 'rb') as file:
        return json.load(file)