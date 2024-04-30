import os
import logging.config


def setup_logging():
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    logging_config_path = os.path.join(base_dir, 'logging.ini')
    logging.config.fileConfig(logging_config_path, disable_existing_loggers=False)


setup_logging()
logger = logging.getLogger('uvicorn')
