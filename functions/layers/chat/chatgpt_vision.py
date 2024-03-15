import os
import json
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
            return base64.b64encode(image_file.read()).decode('utf-8')

    def gpt_analysis_image_upload(self):
        image_file_key = self.prompt["image_string"]
        logger.info(image_file_key)
        logger.info(self.bucket_name)
        body, _ = self.s3_dd.s3_get_object(bucket=self.bucket_name, key=image_file_key)
        logger.info(body)
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


if __name__ == "__main__":
    question = (
        "\n\nConsider the given image and generate 1 heading and the corresponding summary. Suggest the "
        "heading text except introduction and conclusion. Make sure the the summary is in bullet points. "
        "The summary should include all the data points, facts and figures in minimum of 5 lines. "
        "The summary should contain as much information as possible. Form your answer in the following json "
        'format:\n{\n "heading": "heading text",\n "summary": "Summary text"\n}\n\ncontext:\n'
    )

    image_url = "https://nas-dd-input-files.s3.amazonaws.com/40c70010-803c-48c8-939c-b38bb45d88c1/e00b6b06-fdce-4ded-9614-c7734ccbebb9.jpg?AWSAccessKeyId=ASIAZQ3DSS2QZ3A72JVO&Signature=1T0HBgjSTyiBFRZ4jZjvq0HF4Ak%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEIL%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIQDIYa0qTT5JrCCXWG%2BS8JelZKCGsTWmw1uUKcmDYCzkywIgMLwpzxbyzQDCMQ0AulhtVdHbkByC%2BTZEMRKYEDZBHx4qjwMIi%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2NTQ2NTQ0Nzc5ODUiDAfSYEv0%2FygXATB01SrjAobmuyWCSW3r9Ok0aKYtHOF3s11Mqkz%2BRYp%2ByAh5mS17ZIcbxujoDLvnxcMvLAbWNIoPwcLxywX%2BRj%2BPj6gZ3quMEw%2FY7SgXkBgbbJqWlAqGnUl6rVgjMO7GUjC8DjkydvnGMG507M7mfz2BBQSnxO8eYHMhB%2FtS2M%2BRu1dRzTNCvJH4UOrB6bRWf0t34je2GqTYvp%2FUgkbim1xgdSrr3LDsb7zp21%2BSXXdx3tJ3Dj0TEi1gFspri9E2c%2B3rMECmgEuTV2neRgL0nwf8KQ3sTcFppyd1r4u2V0La%2F%2BlvpJmExsIO%2FvPHDIAui66VR4RVIKs0dy9CVFYPd9AYiWVJrmII4HpUdd1vlR70kSqjERtSvRQ1hLhNQy79iE0TsAadOd0jg9n5iEgpZtSe8lNwKarJO722nArhMzkuwTRvnAUDN5mnE9qdyfzd9T8JXj33cLbAU73QlEFqiPZDyIMqDDaRIPAw2azQrwY6ngFUx7f0iI6rhvTKhn3YoOFUQPGiIhuBINooCFnA3ZF2af4lwNVIBai0Hg0hAvg93q14bKQMDGJ5%2BI5EzY8prsNyPPuV%2B9wqg1CqD7jX0JwHPDhIWr1PheQYyHkfEl08gsqBjHT3Fcxjou%2F%2FB1x%2Fk4fCPKnsBChpkZVx9fpKgAdMzu41AmRXIQbCPd1OpDi6NM9iMufBxAp4VmFucAZiKA%3D%3D&Expires=1710583048"
    prompt = {
        "image_string": image_url,
        "questions": question
    }

    gptVision = ChatGptVision("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", "gpt-4-vision-preview", prompt)
    json_data = gptVision.gpt_analysis_image_url()
    print(json.loads(json_data))

