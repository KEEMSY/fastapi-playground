import logging
from datetime import datetime

from pydantic import ValidationError
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from src.domains.sync_example.business.schemas import SyncExampleSchema, SyncExampleListSchema
from src.domains.sync_example.database.models import SyncExample
from src.domains.sync_example.presentation.schemas import CreateSyncExample
from src.exceptions import DLException

logger = logging.getLogger(__name__)


# 현재 문제점: PL 스키마를 DL에서 사용한다.
# - BL을거치는 것이 아닌 바로 사용하는 것이 문제임

def read_sync_example(db: Session, sync_example_id: int) -> SyncExampleSchema:
    result = db.query(SyncExample).get(sync_example_id)
    if result is None:
        logger.error(f"No SyncExample found with id {sync_example_id}")
        raise DLException(detail=f"No SyncExample found with id {sync_example_id}")

    try:
        result_into_schema = SyncExampleSchema.model_validate(result)
        logger.info(f"Retrieved SyncExample {sync_example_id}")
        return result_into_schema

    except Exception as e:
        logger.error(f"Error while retrieving SyncExample {sync_example_id}")
        raise DLException(code="D0000", detail=f"Error while retrieving SyncExample {sync_example_id}")


def create_sync_example(db: Session, create_example_data: CreateSyncExample) -> SyncExampleSchema:
    try:
        new_sync_example = SyncExample(
            name=create_example_data.name,
            description=create_example_data.description,
            user=None
        )
        db.add(new_sync_example)
        db.commit()
        db.refresh(new_sync_example)
        logger.info(f"Created SyncExample with ID {new_sync_example.id}")

        return SyncExampleSchema.model_validate(new_sync_example)

    except ValidationError as ve:
        logger.error(f"Validation error while creating SyncExample: {ve}")
        raise DLException(detail="Validation error on data input.")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while creating SyncExample: {e}")
        raise DLException(detail="Database error occurred while creating SyncExample.")

    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error while creating SyncExample: {e}")
        raise DLException(detail="An unexpected error occurred while creating SyncExample.")


def get_sync_example_list(db: Session, limit: int = 10, offset: int = 0) -> SyncExampleListSchema:
    try:
        _example_list = db.query(SyncExample).order_by(SyncExample.create_date.desc())

        total = _example_list.count()
        example_list = _example_list.offset(offset).limit(limit).all()
        example_schema_list = [SyncExampleSchema.model_validate(example) for example in example_list]

        return SyncExampleListSchema(
            total=total,
            example_list=example_schema_list
        )
    except ValidationError as ve:
        logger.error(f"Validation error while creating SyncExampleListSchema: {ve}")
        raise DLException(code="D0002", detail="Validation error on data input.")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while creating SyncExampleListSchema: {e}")
        raise DLException(detail="Database error occurred while creating SyncExampleListSchema.")

    except Exception as e:
        logger.error(f"Database error during retrieving SyncExamples: {str(e)}")
        raise DLException(detail="Failed to retrieve SyncExample list.")


def update_sync_example(db: Session, example_id: int, request):
    target_example = db.query(SyncExample).get(example_id)
    if target_example is None:
        raise DLException(detail="SyncExample not found")

    try:

        target_example.name = request.name
        target_example.description = request.description
        target_example.modify_date = datetime.now()
        db.commit()
        db.refresh(target_example)

        return SyncExampleSchema.model_validate(target_example)

    except ValidationError as ve:
        logger.error(f"Validation error while updating SyncExample: {ve}")
        raise DLException(detail="Validation error on data input.")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while updating SyncExample: {e}")
        raise DLException(detail="Database error occurred while updating SyncExample.")

    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error while updating SyncExample: {e}")
        raise DLException(detail="An unexpected error occurred while updating SyncExample.")


def delete_sync_example(db, example_id: int):
    target_example = db.query(SyncExample).get(example_id)
    if target_example is None:
        raise DLException(code="D0001", detail="SyncExample not found")

    try:
        db.delete(target_example)
        db.commit()
        logger.info(f"Deleted SyncExample with ID {example_id}")

    except SQLAlchemyError as e:
        db.rollback()
        logger.error(f"Database error while deleting SyncExample: {e}")
        raise DLException(detail="Database error occurred while deleting SyncExample.")

    except Exception as e:
        db.rollback()
        logger.error(f"Unexpected error while deleting SyncExample: {e}")
        raise DLException(detail="An unexpected error occurred while deleting SyncExample.")
