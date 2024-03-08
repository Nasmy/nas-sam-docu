import json

import boto3
import numpy as np
from loguru import logger


class S3Wrapper:
    def __init__(self):
        self.s3_client = boto3.client("s3")

    def load_image_from_s3(self, bucket_name, key) -> (np.ndarray, json):
        import cv2

        """
        Download image from S3 bucket
        :param bucket: S3 bucket name
        :param key: S3 key
        :return: Image as numpy array
        """
        try:
            # Fetch the image data from S3
            obj = self.s3_client.get_object(Bucket=bucket_name, Key=key)
            image_data = obj["Body"].read()
            metadata = obj["Metadata"]

            # Convert the image data to a numpy array and then read it into OpenCV
            image_nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(image_nparr, cv2.IMREAD_COLOR)
            logger.info(f"Loaded image from S3 - {bucket_name}:{key}")

            return image, metadata
        except Exception as e:
            print(e)
            return None, None

    def s3_put_object(self, bucket, key, body, metadata=None):
        if metadata is None:
            metadata = {}
        self.s3_client.put_object(Bucket=bucket, Key=key, Body=body, Metadata=metadata)
        logger.info(f"Uploaded file to s3 - {bucket}:{key}")
        return True

    def s3_get_object(self, bucket, key) -> (bytes, json):
        obj = self.s3_client.get_object(Bucket=bucket, Key=key)
        body = obj["Body"].read()
        metadata = obj.get("Metadata", None)
        logger.info(f"Loaded file from S3 - {bucket}:{key}")
        return body, metadata

    def s3_get_json(self, bucket, key) -> (json, json):
        obj = self.s3_client.get_object(Bucket=bucket, Key=key)
        json_content = json.loads(obj["Body"].read().decode("utf-8"))
        metadata = obj.get("Metadata", None)
        logger.info(f"Loaded json from S3 - {bucket}:{key}")
        return json_content, metadata

    def s3_put_json(self, bucket, key, body, metadata=None):
        if metadata is None:
            metadata = {}
        self.s3_client.put_object(Bucket=bucket, Key=key, Body=json.dumps(body), Metadata=metadata)
        logger.info(f"Uploaded json to s3 - {bucket}:{key}")
        return True
