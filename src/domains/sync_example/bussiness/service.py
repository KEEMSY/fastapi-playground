import logging

from sqlalchemy.orm import Session

from src.domains.sync_example.bussiness.schemas import SyncExampleSchema
from src.domains.sync_example.database import crud as example_crud
from src.domains.sync_example.presentation.schemas import CreateSyncExample
from src.exceptions import BLException, DLException

logger = logging.getLogger(__name__)


def get_sync_example(db: Session, sync_example_id: int) -> SyncExampleSchema:
    sync_example_schema: SyncExampleSchema = example_crud.read_sync_example(db, sync_example_id)
    if not sync_example_schema:
        logger.error(f"SyncExample not found with id {sync_example_id}")
        raise BLException("SyncExample not found")

    logger.info(f"Retrieved SyncExample {sync_example_id}")
    return sync_example_schema


def save_sync_example(db: Session, create_example_data: CreateSyncExample) -> SyncExampleSchema:
    try:
        sync_example_created = example_crud.create_sync_example(db, create_example_data)
        logger.info(f"Successfully created SyncExample with ID {sync_example_created.id}")

        return sync_example_created

    except DLException as de:
        # Handle specific data layer exceptions
        logger.error(f"Failed to create SyncExample: {de.detail}")
        raise BLException(de.detail)

    except Exception as e:
        # Handle unexpected errors
        logger.error(f"Unexpected error while creating SyncExample: {str(e)}")
        raise BLException("An unexpected error occurred during the creation process")
