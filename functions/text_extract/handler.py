import json
import os
import pickle
from datetime import datetime

from loguru import logger

from aws.aws_s3 import S3Wrapper
from db.database import Database
from db.tables import Annotations, AnnotationTypesTable
from text.scrape_prediction import TextDetScrapePrediction
from utils.annotation_types import AnnotationTypes, AnnotationStatus

# initialize custom s3 client
dd_s3 = S3Wrapper()
predict_bucket_name = os.getenv("predict_bucket_name")
out_bucket_name = os.getenv("output_bucket")


def update_annotations(session, document_id, annotation_type, annotation_status: AnnotationStatus):
    # update annotations table
    db_annotations = (
        session.query(Annotations)
        .join(AnnotationTypesTable, AnnotationTypesTable.id == Annotations.annotation_type_id)
        .filter(Annotations.document_id == document_id)
        .filter(AnnotationTypesTable.name == annotation_type.value)
        .first()
    )
    if db_annotations:
        db_annotations.status = annotation_status.value
        session.commit()


def handler(event, _):
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            file_key = event["detail"]["object"]["key"]  # replace with your object key
            file_content, meta_data = dd_s3.s3_get_object(bucket=predict_bucket_name, key=file_key)
            logger.info(f"File downloaded from s3 - {predict_bucket_name}:{file_key}")
            user_id = meta_data["user_id"]
            document_id = meta_data["document_id"]
            logger.info(f"User id: {user_id}, document id: {document_id}")

            # Load the pickled data
            text_prediction: TextDetScrapePrediction = pickle.loads(file_content)

            # Upload bounding_box file to S3
            try:
                update_annotations(session, document_id, AnnotationTypes.BOUNDING_BOX, AnnotationStatus.IN_PROGRESS)
                blocks_json_object = {
                    "status": "success",
                    "message": "Successfully extracted blocks",
                    "details": {
                        "annotation_type": f"{AnnotationTypes.BOUNDING_BOX.value}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "response": text_prediction.get_block_wise_text(),
                    },
                }
                update_annotations(session, document_id, AnnotationTypes.BOUNDING_BOX, AnnotationStatus.COMPLETED)
            except Exception as e:
                update_annotations(session, document_id, AnnotationTypes.BOUNDING_BOX, AnnotationStatus.FAILED)
                logger.exception(e)
                blocks_json_object = {
                    "status": "failed",
                    "message": "Failed to extract blocks",
                    "details": {
                        "annotation_type": f"{AnnotationTypes.BOUNDING_BOX.value}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "response": "",
                        "error": str(e),
                    },
                }
            upload_key = f"{user_id}/{document_id}/{document_id}-{AnnotationTypes.BOUNDING_BOX.value}.json"
            dd_s3.s3_put_object(bucket=out_bucket_name, key=upload_key, body=json.dumps(blocks_json_object, indent=4))

            # Upload bounding_box file to S3
            try:
                update_annotations(session, document_id, AnnotationTypes.SPANS, AnnotationStatus.IN_PROGRESS)
                span_json_object = {
                    "status": "success",
                    "message": "Successfully extracted spans",
                    "details": {
                        "annotation_type": f"{AnnotationTypes.SPANS.value}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "response": text_prediction.get_span_wise_text(),
                    },
                }
                update_annotations(session, document_id, AnnotationTypes.SPANS, AnnotationStatus.COMPLETED)
            except Exception as e:
                update_annotations(session, document_id, AnnotationTypes.SPANS, AnnotationStatus.FAILED)
                logger.exception(e)
                span_json_object = {
                    "status": "failed",
                    "message": "Failed to extract spans",
                    "details": {
                        "annotation_type": f"{AnnotationTypes.SPANS.value}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "response": "",
                        "error": str(e),
                    },
                }
            upload_key = f"{user_id}/{document_id}/{document_id}-{AnnotationTypes.SPANS.value}.json"
            dd_s3.s3_put_object(bucket=out_bucket_name, key=upload_key, body=json.dumps(span_json_object, indent=4))

            # Upload page-wise text file to S3
            try:
                update_annotations(session, document_id, AnnotationTypes.PAGE_TEXT, AnnotationStatus.IN_PROGRESS)
                page_json_object = {
                    "status": "success",
                    "message": "Successfully extracted page text",
                    "details": {
                        "annotation_type": f"{AnnotationTypes.PAGE_TEXT.value}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "response": text_prediction.get_page_wise_json(),
                    },
                }
                update_annotations(session, document_id, AnnotationTypes.PAGE_TEXT, AnnotationStatus.COMPLETED)
            except Exception as e:
                update_annotations(session, document_id, AnnotationTypes.PAGE_TEXT, AnnotationStatus.FAILED)
                logger.exception(e)
                page_json_object = {
                    "status": "failed",
                    "message": "Failed to extract page text",
                    "details": {
                        "annotation_type": f"{AnnotationTypes.PAGE_TEXT.value}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "response": "",
                        "error": str(e),
                    },
                }
            upload_key = f"{user_id}/{document_id}/{document_id}-{AnnotationTypes.PAGE_TEXT.value}.json"
            dd_s3.s3_put_object(bucket=out_bucket_name, key=upload_key, body=json.dumps(page_json_object, indent=4))

            try:
                update_annotations(session, document_id, AnnotationTypes.ALL_TEXT, AnnotationStatus.IN_PROGRESS)
                all_text_json_object = {
                    "status": "success",
                    "message": "Successfully extracted full text",
                    "details": {
                        "annotation_type": f"{AnnotationTypes.ALL_TEXT.value}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "response": {
                            "text": text_prediction.get_text(),
                        },
                    },
                }
                update_annotations(session, document_id, AnnotationTypes.ALL_TEXT, AnnotationStatus.COMPLETED)
            except Exception as e:
                update_annotations(session, document_id, AnnotationTypes.ALL_TEXT, AnnotationStatus.FAILED)
                logger.exception(e)
                all_text_json_object = {
                    "status": "failed",
                    "message": "Failed to extract full text",
                    "details": {
                        "annotation_type": f"{AnnotationTypes.ALL_TEXT.value}",
                        "timestamp": datetime.utcnow().isoformat(),
                        "response": "",
                        "error": str(e),
                    },
                }
            upload_key = f"{user_id}/{document_id}/{document_id}-{AnnotationTypes.ALL_TEXT.value}.json"
            dd_s3.s3_put_object(bucket=out_bucket_name, key=upload_key, body=json.dumps(all_text_json_object, indent=4))

        except Exception as e:
            logger.exception(e)
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "Failed", "error": str(e)}),
            }
