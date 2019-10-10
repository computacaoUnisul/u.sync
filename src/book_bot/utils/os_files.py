import os
import json


def maybe_create_dir(directory):
    if not (os.path.exists(directory) or os.path.isdir(directory)):
        os.makedirs(directory)


def dump_sync_data(filename, data):
    maybe_create_dir('.sync')
    with open(os.path.join('.sync', filename), 'w') as file:
        file.write(json.dumps(data))


def load_sync_data(filename, default=[]):
    filepath = os.path.join('.sync', filename)
    if not os.path.exists(filepath):
        return default
    with open(filepath, 'rb') as file:
        return json.load(file)