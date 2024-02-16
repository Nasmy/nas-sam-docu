import uuid
from datetime import datetime

from loguru import logger

# Lambda layer
from db.database import Database
from db.tables import OCRProgress, Documents
from utils.custom_exceptions import RaiseCustomException, MissingQueryParameterError, \
    DocumentNotFoundError
from utils.event_types import LambdaTriggerEventTypes
from utils.util import json_return, get_event_type


def handler(event, _):
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            event_type = get_event_type(event)

            if event_type == LambdaTriggerEventTypes.EVENT_BRIDGE:
                document_id = event["detail"]["document_id"]
                page_number = event["detail"]["page_number"]
                logger.info(f"document id: {document_id}, page number: {page_number}")
            else:
                raise RaiseCustomException(status_code=500, message="Unknown event type")

            document = session.query(Documents).filter(Documents.id == document_id).first()
            if not document:
                raise DocumentNotFoundError(document_id)

            # Count the number of rows
            count = session.query(OCRProgress).filter(
                OCRProgress.document_id == document_id).count()
            logger.info(f"count: {count}")

            if count < document.page_count:
                logger.info(f"OCR not completed for document: {document_id} - progress: {count}/{document.page_count}")
                status_code, msg = 202, {
                    "status": "success",
                    "message": "Updated usage information",
                    "details": {
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
            else:
                logger.info(f"OCR completed for document: {document_id} - progress: {count}/{document.page_count}")

                # session.query(DailyUsage).filter(DailyUsage.user_id == user_id, DailyUsage.eod == False).delete()
                # session.commit()
                #
                # last_updated_date = session.query(DailyUsage.date).filter(DailyUsage.user_id == user_id).order_by(
                #     DailyUsage.date.desc()).first()
                # if last_updated_date:
                #     last_updated_date = last_updated_date.date + timedelta(days=1)
                # logger.info(f"Last update date: {last_updated_date}")
                #
                # updated_rows = update_daily_usage(session, user_id, from_date=last_updated_date)
                # pprint(updated_rows)

                status_code, msg = 200, {
                    "status": "success",
                    "message": "Updated usage information",
                    "details": {
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }

        except (DocumentNotFoundError, RaiseCustomException, MissingQueryParameterError) as e:
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except Exception as exception:
            logger.exception(exception)
            error_id = uuid.uuid4()
            logger.error(f"an error occurred, id: {error_id} error: {exception}")
            return json_return(500, exception)
        else:
            session.commit()
            return json_return(status_code, msg)
