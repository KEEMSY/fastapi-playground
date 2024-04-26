import os
from dotenv import load_dotenv

load_dotenv()

# ENV = os.environ["ENV"]

SYNC_SQLALCHEMY_DATABASE_URL = os.environ["SYNC_SQLALCHEMY_DATABASE_URL"]
ASYNC_SQLALCHEMY_DATABASE_URL = os.environ["ASYNC_SQLALCHEMY_DATABASE_URL"]
