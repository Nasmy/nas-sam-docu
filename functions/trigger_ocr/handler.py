import os
import pickle
import uuid
from datetime import datetime

from loguru import logger

from aws.aws_s3 import S3Wrapper

# Lambda layer
from db.database import Database
from db.tables import OCRProgress, Documents
from text.scrape_prediction import TextDetScrapePrediction
from utils.custom_exceptions import RaiseCustomException, MissingQueryParameterError, DocumentNotFoundError
from utils.document_types import DocumentTypes
from utils.event_types import LambdaTriggerEventTypes
from utils.util import json_return, get_event_type

dd_s3 = S3Wrapper()
predict_bucket_name = os.getenv("predict_bucket_name")
ocr_output_bucket = os.getenv("ocr_output_bucket")


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
            count = session.query(OCRProgress).filter(OCRProgress.document_id == document_id).count()
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

                all_spans = []
                block_bbox_dict = {}
                metadata = {}
                for page_number in range(1, document.page_count + 1):
                    logger.info(f"Downloading OCR for page: {page_number}")
                    four_digit_page_no = f"{page_number:04d}"
                    upload_key = f"{document_id}/{document_id}-page-{four_digit_page_no}-ocr.pkl"

                    # Download the file from S3
                    file_content, metadata = dd_s3.s3_get_object(bucket=ocr_output_bucket, key=upload_key)

                    # Load the pickled data
                    text_prediction: TextDetScrapePrediction = pickle.loads(file_content)
                    """change the page number of the spans"""
                    for span in text_prediction.prediction:
                        span.page_number = page_number

                    all_spans.extend(text_prediction.prediction)
                    block_bbox_dict.update({page_number: text_prediction.block_bbox_list[1]})

                meta_data = {
                    "user_id": metadata.get("user_id", None),
                    "document_id": document_id,
                    "document_type": metadata.get("document_type", DocumentTypes.PDF.value),
                    "document_ext": metadata.get("document_ext", None),
                }

                logger.info("Combining OCR predictions into a single scrape prediction")
                scrape_prediction = TextDetScrapePrediction(all_spans, block_bbox_list=block_bbox_dict)

                pickled_data = pickle.dumps(scrape_prediction)
                meta_data["text_prediction"] = "Scrape"
                upload_key = f"{meta_data['user_id']}/{document_id}/{document_id}-scrape.pkl"
                dd_s3.s3_put_object(bucket=predict_bucket_name, key=upload_key, body=pickled_data, metadata=meta_data)

                logger.info(f"OCR completed for document: {document_id}")

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
