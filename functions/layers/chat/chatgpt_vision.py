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
        'format:\n{\n "heading": "heading text",\n "summary": "Summary text"\n}\n\nimage:\n'
    )

    image_url = "https://nas-dd-input-files.s3.amazonaws.com/40c70010-803c-48c8-939c-b38bb45d88c1/319f6c3f-61fa-46fc-97da-653ef86aab09.jpg?AWSAccessKeyId=ASIAZQ3DSS2Q64ZSQMX6&Signature=gSEfLYLsk3G48qkV1cX%2FL0%2F9CBE%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEIT%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIQCfDnWQ1K3eHNbvXFFnefnBofe0uuWZ%2Bk0IlvgAETIXVwIgCL5L6R%2BRqXY21ddgW8Z%2B6qpjEIA7HHHyJijxYThsgsMqjwMIjf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2NTQ2NTQ0Nzc5ODUiDOHHKAce3ldekwV9SyrjAhOG%2FFwnsn3qL%2BhuGfKi0tyyZFCt06nK3YZQLmCHOhtXs00fIFbQT578eqWgYrWFsoKT%2FNKXKVQPwFd%2FbioUOe%2B3RZcXNlgVoBNHC3j9GGHK5q15XAp5D27sRixv%2BqHAAmUg7eeMMaR%2FfPFmElCQ4tFhoYOqTa0zih0ifmBmrmykTZ%2B%2B1thAYjD13fE%2BAr3WbC9ApeMjs%2BPv5Olj1mWWg3kjuWDSAhr1XIkDPnIIzRVwDxChR3LN9oI926attofPa8RsxAQyPxeu60Dc69lXfwl2%2B8tVgy%2FKUD1rGY1wVdLChMtTwYAZA%2BOVq7MuaM5NrbWQxvETm8nU1YsgL%2BFzJJ%2B6LTpXxV2dhFZ1Bz7pV3mV1jSstmMP5%2FasVJBMbSJOHQTggzp8rBav7T7Twnkx%2BVPyfi1Sj7cJGLKFFgVQKkWC0KWn92BYHXvGtNuEPZXvFrbZRejC0HOR1U9RjI2a69%2BwNAcwlOvQrwY6ngERSpSRZvT3mTm7h2svTWIvEEPHIqU0EaXc3BlCXfiznz7iduD5X3inoUkrfsNl5qZVBl%2F%2BXDB6dPblakXk8cbTeS%2FOlIqQsw90jBv1ldK76%2BRyECpalon7DC%2Fu1LD8QOvs0mzu4knA17%2F3l8vq2hvCqEeorfHOKb56gqxpi3tu61WwwrhVaVPhMZYbnUxYhQkQS50P1zM8HXLj21QcpQ%3D%3D&Expires=1710589979"
    prompt = {
        "image_string": image_url,
        "questions": question
    }

    gptVision = ChatGptVision("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", "gpt-4-vision-preview", prompt)

    json_data = gptVision.gpt_analysis_image_url()
    print(json_data)
    print(json.loads(json_data))

