import logging

from sqlalchemy.orm import Session

from src.domains.sync_example.bussiness.schemas import SyncExampleSchema, SyncExampleListSchema
from src.domains.sync_example.database import crud as example_crud
from src.domains.sync_example.presentation.schemas import CreateSyncExample, UpdateSyncExampleV2, UpdateSyncExampleV1
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


def get_sync_example_list(db: Session, limit: int = 10, offset: int = 0) -> SyncExampleListSchema:
    try:
        sync_example_list: SyncExampleListSchema = example_crud.get_sync_example_list(db, limit=limit, offset=offset)

        if not sync_example_list.example_list:
            logger.info("No SyncExamples found.")

        return sync_example_list

    except DLException as de:
        logger.error(f"Error in retrieving SyncExamples: {de.detail}")
        raise BLException("Could not fetch SyncExamples.")
    except Exception as e:
        logger.error(f"Unexpected error while fetching SyncExamples: {str(e)}")
        raise BLException("An unexpected error occurred while fetching SyncExamples.")


def update_sync_example_v1(db: Session, example_id: int, request: UpdateSyncExampleV1) -> SyncExampleSchema:
    try:
        updated_sync_example = example_crud.update_sync_example(db, example_id, request)
        logger.info(f"Successfully updated SyncExample with ID {example_id}")

        return updated_sync_example

    except DLException as de:
        logger.error(f"Failed to update SyncExample: {de.detail}")
        raise BLException(de.detail)

    except Exception as e:
        logger.error(f"Unexpected error while updating SyncExample: {str(e)}")
        raise BLException("An unexpected error occurred during the update process")


def update_sync_example_v2(db: Session, request: UpdateSyncExampleV2) -> SyncExampleSchema:
    try:
        example_id = request.sync_example_id
        updated_sync_example = example_crud.update_sync_example(db, example_id, request)
        logger.info(f"Successfully updated SyncExample with ID {example_id}")

        return updated_sync_example

    except DLException as de:
        logger.error(f"Failed to update SyncExample: {de.detail}")
        raise BLException(de.detail)

    except Exception as e:
        logger.error(f"Unexpected error while updating SyncExample: {str(e)}")
        raise BLException("An unexpected error occurred during the update process")


def delete_sync_example(db, example_id: int):
    try:
        example_crud.delete_sync_example(db, example_id)
        logger.info(f"Successfully deleted SyncExample with ID {example_id}")

    except DLException as de:
        logger.error(f"Failed to delete SyncExample: {de.detail}")
        raise BLException(code=de.code, detail=de.detail)

    except Exception as e:
        logger.error(f"Unexpected error while deleting SyncExample: {str(e)}")
        raise BLException("An unexpected error occurred during the deletion process")
