import json
import os
import pickle
from pathlib import Path

from loguru import logger

from aws.aws_s3 import S3Wrapper
from db.database import Database
from db.tables import Documents, AnnotationTypesTable, Annotations
from pdf_type import is_machine_readable
from pymupdf_scrape import PyMuPDF
from text.scrape_prediction import TextDetScrapePrediction
from text.span import Span
from utils.annotation_types import AnnotationTypes, AnnotationStatus
from utils.document_types import DocumentTypes
from chat.model_info import OpenAIModels

supported_image_types = [".jpg", ".jpeg", ".png", ".bmp"]
bucket_name = os.getenv("input_bucket")
image_out_bucket_name = os.getenv("image_output_bucket")
image_process_bucket_name = os.getenv("image_process_bucket")
out_bucket_name = os.getenv("scrape_output_bucket")
predict_bucket_name = os.getenv("predict_bucket_name")

dd_s3 = S3Wrapper()


def handler(event, _):
    # update page count
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            # replace with your bucket name
            key = event["detail"]["object"]["key"]  # replace with your object key
            logger.info(f"Key - {key}")

            # Download the file from S3
            file_content, metadata = dd_s3.s3_get_object(bucket=bucket_name, key=key)

            logger.info(f"Metadata - {metadata}")
            user_id = metadata["user_id"]
            document_id = metadata["document_id"]
            document_ext = metadata["document_ext"]
            document_type = metadata["document_type"]

            document = session.query(Documents).filter(Documents.id == document_id).first()
            if document is None:
                logger.info(f"Document not found - {document_id}")
                return {
                    "statusCode": 404,
                    "body": json.dumps({"message": "Document not found"}),
                    "content-type": "application/json",
                }

            if document.is_uploaded:
                logger.error("This document is already uploaded!")
                return {
                    "status": 400,
                    "body": json.dumps({"message": "This document is already uploaded!"}),
                    "content-type": "application/json",
                }

            document.is_uploaded = True
            can_enable_gpt_4 = OpenAIModels.can_enable_gpt_4_vision(document_ext)
            gpt_4_annotation_types = [
                AnnotationTypes.HEADINGS,
            ]
            """Update annotations"""
            for annotation_type in list(AnnotationTypes):
                if annotation_type == AnnotationTypes.CHAT:
                    continue
                if can_enable_gpt_4 and annotation_type not in gpt_4_annotation_types:
                    continue
                db_anno_type = (
                    session.query(AnnotationTypesTable)
                    .filter(AnnotationTypesTable.name == annotation_type.value)
                    .first()
                )
                if db_anno_type:
                    logger.info(f"Adding annotation - {annotation_type.value}")
                    new_annotation = Annotations(
                        document_id=document_id,
                        annotation_type_id=db_anno_type.id,
                        status=AnnotationStatus.NOT_STARTED.value,
                    )
                    session.add(new_annotation)

            # Save the file to disk
            tmp_file_location = f"/tmp/{document_id}{document_ext}"
            with open(tmp_file_location, "wb") as f:
                f.write(file_content)

            # If PDF
            upload_key = "NA"
            meta_data = {
                "user_id": user_id,
                "document_id": document_id,
                "document_type": document_type,
                "document_ext": document_ext,
            }
            page_count = 0
            if document_type == DocumentTypes.PDF.value:
                logger.info(f"Processing PDF - {document_id}")
                # Run the prediction
                pymu_obj = PyMuPDF(file_path=Path(tmp_file_location))
                page_count = pymu_obj.get_number_of_pages()
                predict: TextDetScrapePrediction = pymu_obj.predict()

                is_mr = is_machine_readable(tmp_file_location)
                logger.info(f"Is Machine Readable - {is_mr}")

                if is_mr:
                    '''
                    This is a Machine Readable PDF
                    '''
                    pickled_data = pickle.dumps(predict)
                    meta_data["text_prediction"] = "Scrape"
                    upload_key = f"{user_id}/{document_id}/{document_id}-scrape.pkl"
                    dd_s3.s3_put_object(bucket=predict_bucket_name, key=upload_key, body=pickled_data,
                                        metadata=meta_data)
                else:
                    # convert to images and upload to s3
                    logger.info(f"Page count - {page_count}")
                    for page_number in range(1, page_count + 1):
                        logger.info(f"Processing page - {page_number}")
                        meta_data["page_number"] = f"{page_number:04d}"
                        image_path = f"/tmp/page-{page_number:04d}.jpg"
                        file_key = f"{user_id}/{document_id}/{document_id}-page-{page_number:04d}.jpg"
                        pymu_obj.get_image(page_number, image_path)
                        dd_s3.s3_put_object(
                            body=open(image_path, "rb"), bucket=image_out_bucket_name, key=file_key, metadata=meta_data
                        )
                        logger.info(f"Uploaded image - {file_key} to bucket - {image_out_bucket_name}")

            # If image
            elif document_type in [DocumentTypes.IMAGE_JPG.value, DocumentTypes.IMAGE_PNG.value]:
                page_count = 1
                logger.info(f"Processing Image - {document_id}")
                meta_data["page_number"] = "0000"
                file_key = f"{user_id}/{document_id}-image{document_ext}"
                dd_s3.s3_put_object(
                    body=open(tmp_file_location, "rb"), bucket=image_process_bucket_name, key=file_key, metadata=meta_data
                )
            elif document_type in [DocumentTypes.TXT.value]:
                page_count = 1
                logger.info(f"Processing Text - {document_id}")
                span_list = []
                with open(tmp_file_location, "r") as f:
                    span_id = 0
                    for line in f.readlines():
                        span_id += 1
                        new_span = Span(
                            id=span_id,
                            text=line.strip(),
                            bbox=[0, 0, 0, 0],
                            page_number=1,
                            block_number=1,
                        )
                        logger.info("Adding span - {}".format(new_span))
                        span_list.append(new_span)
                block_bbox_dict = {1: {1: [0, 0, 0, 0]}}
                predict = TextDetScrapePrediction(prediction=span_list, block_bbox_list=block_bbox_dict)
                # Save prediction to disk
                pickled_data = pickle.dumps(predict)
                file_key = f"{user_id}/{document_id}-text{document_ext}"
                meta_data["text_prediction"] = "text"
                upload_key = f"{user_id}/{document_id}/{document_id}-text.pkl"
                dd_s3.s3_put_object(bucket=predict_bucket_name, key=upload_key, body=pickled_data, metadata=meta_data)
            else:
                logger.info(f"Unsupported file: {key} with type: {document_ext}")

            """ Update page count"""
            document.page_count = page_count
            logger.info(f"Updated page count for document - {document_id}")

        except FileNotFoundError as e:
            logger.exception(e)
            logger.error(f"Failed to process file: {key} - {str(e)}")
            return {
                "statusCode": 500,
                "body": json.dumps({"message": "Failed", "error": str(e)}),
            }
        else:
            session.commit()
            return {
                "statusCode": 200,
                "body": json.dumps({"message": "Success", "key": upload_key}),
            }

