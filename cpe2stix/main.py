"""
Main driver logic for cpe2stix
"""

import dataclasses
import math
import requests
import time
from datetime import datetime, timedelta

from .config import Config
from .helper import (
    get_date_string_nvd_format, load_json_file, clean_filesystem
)
from .parse_api_response import parse_cpe_api_response
from stix2 import parse
from celery import group, chord
from .celery import cpe_syncing_task, preparing_results
from .loggings import logger


def fetch_data(start, end, config):
    total_results = math.inf
    start_index = -1
    backoff_time = 10
    all_responses_content = []
    while config.results_per_page * (start_index + 1) < total_results:
        start_index += 1
        print("Calling NVD cpe API with startIndex: %d", start_index)
        query = {
            "lastModStartDate": get_date_string_nvd_format(start),
            "lastModEndDate": get_date_string_nvd_format(end),
            "resultsPerPage": config.results_per_page,
            "startIndex": start_index * config.results_per_page
        }

        try:
            logger.info(f"Query => {query}")
            response = requests.get(config.nvd_cpe_api_endpoint, query, headers=dict(apiKey=config.nvd_api_key))
            logger.info(f"Status Code => {response.status_code}")
            if response.status_code != 200:
                logger.warning("Got response status code %d.", response.status_code)
                raise requests.ConnectionError

        except requests.ConnectionError as ex:
            logger.warning(
                "Got ConnectionError. Backing off for %d seconds.", backoff_time
            )
            start_index -= 1
            time.sleep(backoff_time)
            backoff_time *= 2
            continue

        content = response.json()
        total_results = content["totalResults"]
        logger.info(f"Total Results {total_results}")
        parse_cpe_api_response(content, config)

        if config.results_per_page * (start_index + 1) < total_results:
            time.sleep(5)
        backoff_time = 10
    return all_responses_content


def map_marking_definition(config, object_list):
    logger.info("Marking Definition creation start")
    marking_definition = parse(config.CPE2STIX_MARKING_DEFINITION_REF)
    config.fs.add(marking_definition)
    logger.info("Marking Definition creation end")
    return object_list


def main(c_start_date=None, c_end_date=None, filename=None, config = Config()):
    clean_filesystem(config.file_system)
    params = []
    current_date = datetime.strptime(config.start_date, "%Y-%m-%dT%H:%M:%S")
    if c_start_date:
        current_date = datetime.strptime(c_start_date, "%Y-%m-%dT%H:%M:%S")

    end_date_ = datetime.strptime(config.end_date, "%Y-%m-%dT%H:%M:%S")
    if c_start_date:
        end_date_ = datetime.strptime(c_end_date, "%Y-%m-%dT%H:%M:%S")

    while current_date < end_date_:
        start_date = current_date
        end_date = current_date + timedelta(days=120)
        if end_date > end_date_:
            end_date = end_date_
        params.append(
            [start_date, end_date]
        )
        current_date = end_date

    tasks = [cpe_syncing_task.s(param[0], param[1], dataclasses.asdict(config)) for param in params]
    result = chord(group(tasks))(preparing_results.s(dataclasses.asdict(config), filename))
    return result
