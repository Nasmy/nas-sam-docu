import json
import os
import pickle
from pathlib import Path

import boto3
from loguru import logger

from db.database import Database
from db.documents import Documents
from pymupdf_scrape import PyMuPDF
from text.scrape_prediction import TextDetScrapePrediction
from text.span import Span
from utils.document_types import DocumentTypes

supported_image_types = [".jpg", ".jpeg", ".png", ".bmp"]
bucket_name = os.getenv("input_bucket")
image_out_bucket_name = os.getenv("image_output_bucket")
out_bucket_name = os.getenv("scrape_output_bucket")
predict_bucket_name = os.getenv("predict_bucket_name")


def handler(event, _):
    try:
        logger.info(event)

        # initialize s3 client
        s3 = boto3.client("s3")

        # replace with your bucket name
        key = event["detail"]["object"]["key"]  # replace with your object key
        logger.info(f"Key - {key}")

        # Download the file from S3
        obj = s3.get_object(Bucket=bucket_name, Key=key)

        logger.info(f"Metadata - {obj['Metadata']}")
        user_id = obj["Metadata"]["user_id"]
        document_id = obj["Metadata"]["document_id"]
        document_ext = obj["Metadata"]["document_ext"]
        document_type = obj["Metadata"]["document_type"]

        # Save the file to disk
        tmp_file_location = f"/tmp/{document_id}{document_ext}"
        with open(tmp_file_location, "wb") as f:
            f.write(obj["Body"].read())

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

            # Save prediction to disk
            pickled_data = pickle.dumps(predict)
            meta_data["text_prediction"] = "Scrape"
            upload_key = f"{user_id}/{document_id}/{document_id}-scrape.pkl"
            s3.put_object(Bucket=predict_bucket_name, Key=upload_key, Body=pickled_data, Metadata=meta_data)
            logger.info(f"Uploaded file to s3 - {predict_bucket_name}:{upload_key}")

            # Update the database with the page number
            database = Database()
            with database.get_session() as session:
                # search for document
                document = session.query(Documents).filter(Documents.document_id == document_id).first()
                if document is None:
                    logger.info(f"Document not found - {document_id}")
                    return {
                        "statusCode": 404,
                        "body": json.dumps({"message": "Document not found"}),
                    }
                document.page_count = pymu_obj.get_number_of_pages()
                session.commit()
                logger.info(f"Updated page count for document - {document_id}")
            database.close_connection()

            # convert to images and upload to s3
            # TODO - Logic to check none scrapable pages and only upload those pages as images
            for page_number in range(1, pymu_obj.get_number_of_pages() + 1):
                meta_data["page_number"] = f"{page_number:04d}"
                image_path = f"/tmp/page-{page_number:04d}.jpg"
                file_key = f"{user_id}/{document_id}/{document_id}-page-{page_number:04d}.jpg"
                pymu_obj.get_image(page_number, image_path)
                s3.put_object(
                    Body=open(image_path, "rb"), Bucket=image_out_bucket_name, Key=file_key, Metadata=meta_data
                )
                logger.info(f"Convert page {page_number} to an image and uploaded - {image_out_bucket_name}:{file_key}")
                # Only upload one image for now
                break

        # If image
        elif document_type in [DocumentTypes.IMAGE_JPG.value, DocumentTypes.IMAGE_PNG.value]:
            page_count = 1
            logger.info(f"Processing Image - {document_id}")
            meta_data["page_number"] = "0000"
            file_key = f"{user_id}/{document_id}-image{document_ext}"
            s3.put_object(
                Body=open(tmp_file_location, "rb"), Bucket=image_out_bucket_name, Key=file_key, Metadata=meta_data
            )
            logger.info(f"Uploaded image file for OCR - {file_key}")
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
            s3.put_object(Bucket=predict_bucket_name, Key=upload_key, Body=pickled_data, Metadata=meta_data)
            logger.info(f"Uploaded text file - {file_key}")
        else:
            logger.info(f"Unsupported file: {key} with type: {document_ext}")

        # update page count
        database = Database()
        with database.get_session() as session:
            # search for document
            document = session.query(Documents).filter(Documents.document_id == document_id).first()
            if document is None:
                logger.info(f"Document not found - {document_id}")
                return {
                    "statusCode": 404,
                    "body": json.dumps({"message": "Document not found"}),
                    "content-type": "application/json",
                }
            document.page_count = page_count
            session.commit()
            logger.info(f"Updated page count for document - {document_id}")
        database.close_connection()

        return {
            "statusCode": 200,
            "body": json.dumps({"message": "Success", "key": upload_key}),
        }
    except Exception as e:
        logger.error(f"Failed to process file: {key} - {str(e)}")
        logger.exception(e)
        return {
            "statusCode": 500,
            "body": json.dumps({"message": "Failed", "error": str(e)}),
        }
