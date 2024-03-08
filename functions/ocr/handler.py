import json
import os
import pickle

from loguru import logger

from aws.aws_s3 import S3Wrapper
from tesseract_ocr import TesseractOcr
from text.scrape_prediction import TextDetScrapePrediction
from utils.document_types import DocumentTypes


def handler(event, _):
    logger.info(event)
    try:
        # Initialize custom S3 client
        s3_dd = S3Wrapper()

        source_bucket_name = os.getenv("images_bucket")  # replace with your bucket name
        key = event["detail"]["object"]["key"]  # replace with your object key
        image, metadata = s3_dd.load_image_from_s3(source_bucket_name, key)  # Download the file from S3

        document_type = metadata.get("document_type", None)
        four_digit_page_no = metadata.get("page_number", None)
        file_id = metadata.get("document_id", None)

        metadata["text_prediction"] = "OCR"

        tess_obj = TesseractOcr(tess_data_dir="/function/tessdata", lang="eng")
        predict: TextDetScrapePrediction = tess_obj.predict(image)

        if document_type == DocumentTypes.PDF.value and file_id and four_digit_page_no:
            ocrd_text = {"text": predict.get_text()}
            dest_bucket_name = os.getenv("ocr_output_bucket")
            upload_key = f"{file_id}/{file_id}-page-{metadata['page_number']}-ocr.json"
            s3_dd.s3_put_object(
                body=json.dumps(ocrd_text, indent=4), bucket=dest_bucket_name, key=upload_key, metadata=metadata
            )
        elif document_type in [DocumentTypes.IMAGE_JPG.value, DocumentTypes.IMAGE_PNG.value]:
            pickled_data = pickle.dumps(predict)
            upload_key = f"{metadata['user_id']}/{file_id}/{file_id}-ocr.pkl"
            predict_bucket_name = os.getenv("predict_bucket_name")
            s3_dd.s3_put_object(bucket=predict_bucket_name, key=upload_key, body=pickled_data, metadata=metadata)
        else:
            logger.error(f"Invalid document type: {document_type}")

    except Exception as e:
        logger.exception(e)
        return {"statusCode": 500, "body": json.dumps({"message": "Internal Server Error"})}
