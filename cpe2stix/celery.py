import os
from celery import Celery
from celery.signals import setup_logging  # noqa
from .stix_store import StixStore
from .config import Config
from .helper import delete_subfolders, append_data
from .loggings import logger
from stix2.datastore.filters import Filter


if bool(os.getenv(" ")):
    from config import celery_app as app


if not bool(os.getenv("CENTRAL_CELERY")):
    CELERY_RESULT_BACKEND='amqp://',
    app = Celery(
        'cpe2stix', broker=Config.REDIS_URL, backend=Config.REDIS_URL
    )
    app.conf.task_default_queue = 'default'
    app.conf.worker_concurrency = 8  # Set the number of worker processes
    app.conf.worker_log_format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    app.conf.worker_log_file = 'logs/celery.log'  # Specify the log file path
    app.autodiscover_tasks()


@setup_logging.connect
def config_loggers(*args, **kwargs):
    from logging.config import dictConfig  # noqa
    # dictConfig({})


@app.task(soft_time_limit=1000, time_limit=1000)
def cpe_syncing_task(start, end, config):
    from .main import fetch_data
    fetch_data(start, end, Config(**config))


@app.task(soft_time_limit=1000, time_limit=1000)
def preparing_results(task_results, config, filename=None):
    from .main import map_marking_definition
    config = Config(**config)
    results = []
    results = map_marking_definition(config, results)
    results = append_data(results, config.file_system)
    softwares = config.fs.query([Filter("type", "=", "software")])
    if softwares:
        stix_store = StixStore(
            config.stix2_objects_folder, config.stix2_bundles_folder
        )
        stix_store.store_cpe_in_bundle(results, filename, update=True)
    else:
        logger.info("Not writing any file because no output")
    if bool(os.getenv("CENTRAL_CELERY")):
        delete_subfolders(config.stix2_objects_folder)
