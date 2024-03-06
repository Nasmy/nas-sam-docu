import os
import base64
import boto3
import requests
from aws.aws_s3 import S3Wrapper
from loguru import logger


# TODO Can do refactor. Just Written a Mock Code for Testing Purpose
class ChatGptVision:
    gpt_api_key = None
    gpt_model = None
    bucket_name = os.getenv("image_bucket")
    s3 = boto3.client("s3")
    s3_dd = S3Wrapper()

    def __init__(self, gpt_api_key, gpt_model, prompt_data):
        self.gpt_api_key = gpt_api_key
        self.gpt_model = gpt_model
        self.prompt = prompt_data

    def get_content_payload(self, image_url, gpt_questions):
        return [
            {
                "type": "text",
                "text": gpt_questions
            },
            {
                "type": "image_url",
                "image_url": {
                    "url": image_url
                }
            }
        ]

    def get_vision_payload(self, image_url, gpt_questions):
        return {
            "model": "gpt-4-vision-preview",
            "messages": [
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "text",
                            "text": gpt_questions
                        },
                        {
                            "type": "image_url",
                            "image_url": {
                                "url": image_url
                            }
                        }
                    ]
                }
            ],
            "max_tokens": 300
        }

    def get_headers(self):
        return {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.gpt_api_key}"
        }

    def encode_image(self, image_path):
        with open(image_path, "rb") as image_file:
            image_data = image_file.read().replace(b'\x00', b'')
            return base64.b64encode(image_data).decode('utf-8')

    def gpt_analysis_image_upload(self):
        image_file_key = self.prompt["image_string"]
        logger.info(image_file_key)
        logger.info(self.bucket_name)
        body, _ = self.s3_dd.s3_get_object(bucket=self.bucket_name, key=image_file_key)
        base64_image = self.encode_image(body)
        image_path = f"data:image/jpeg;base64,{base64_image}"
        payload = self.get_vision_payload(image_url=image_path, gpt_questions=self.prompt["questions"])
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=self.get_headers(), json=payload)
        return self.load_response_content(response)

    def gpt_analysis_image_url(self):
        payload = self.get_vision_payload(image_url=self.prompt["image_string"], gpt_questions=self.prompt["questions"])
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=self.get_headers(), json=payload)
        content, role = self.load_response_content(response)
        return content

    @staticmethod
    def load_response_content(response):
        # Accessing content of response
        response_content = response.json()
        content = response_content['choices'][0]['message']['content']
        role = response_content['choices'][0]['message']['role']
        return content, role

    def analyse_image_string(self):

        if self.prompt["image_string"].startswith("http"):
            content = self.gpt_analysis_image_url()
        else:
            content = self.gpt_analysis_image_upload()

        return content


"""" Internal testing purpose
if __name__ == "__main__":
    prompt = {
        "image_string": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
        "questions": "What’s in this image?"
    }
    gptVision = ChatGptVision("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", "gpt-4-vision-preview", prompt)
    print(gptVision.analyse_image_string()) """
