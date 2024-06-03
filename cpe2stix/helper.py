"""
Miscellaneous helper functions
"""
import os
import logging
import shutil
import hashlib
import json
from .config import Config
logger = logging.getLogger(__name__)


def get_date_string_nvd_format(date):
    return date.strftime("%Y-%m-%dT%H:%M:%SZ")

def clean_filesystem(path):
    logging.info("Deleting old data from filesystem")
    for filename in os.listdir(path):
        file_path = os.path.join(path, filename)
        try:
            if os.path.isfile(file_path) or os.path.islink(file_path):
                os.unlink(file_path)
            elif os.path.isdir(file_path):
                shutil.rmtree(file_path)
        except Exception as e:
            logging.error(f"Failed to delete {file_path}. Reason: {e}")
    logging.info("Deletion done!")


def load_json_file(filename, data_folder="data/stix_templates/", include_filepath=False):
    config = Config()
    path = filename
    if not include_filepath:
        path = os.path.join("{}/{}".format(config.data_path, data_folder), filename)
    return json.load(open(path))


def delete_subfolders(directory_path, ignore_extension='.json'):
    for root, dirs, files in os.walk(directory_path, topdown=False):
        for dir in dirs:
            dir_path = os.path.join(root, dir)
            print(os.path.join(root, dir))
            shutil.rmtree(dir_path)


def append_data(results, file_system):
    for root, _, files in os.walk(file_system):
        for filename in files:
            if filename.endswith(".json"):
                file_path = os.path.join(root, filename)
                with open(file_path, "r") as file:
                    stix_object = json.load(file)
                    results.append(stix_object)
    return results
def generate_md5_from_list(stix_objects: list) -> str:
    json_str = json.dumps(stix_objects, sort_keys=True).encode('utf-8')
    return hashlib.md5(json_str).hexdigest()