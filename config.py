import os
from dotenv import load_dotenv

load_dotenv()

# ENV = os.environ["ENV"]

SYNC_SQLALCHEMY_DATABASE_URL = os.environ["SYNC_SQLALCHEMY_DATABASE_URL"]
ASYNC_SQLALCHEMY_DATABASE_URL = os.environ["ASYNC_SQLALCHEMY_DATABASE_URL"]
LOG_FILE_PATH = os.environ["LOG_FILE_PATH"]
LOG_FILE_EXT = os.environ["LOG_FILE_EXT"]