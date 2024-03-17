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

    image_url = "https://nas-dd-input-files.s3.amazonaws.com/40c70010-803c-48c8-939c-b38bb45d88c1/79b845cf-2e9c-4f39-aa59-03f71d2bd38e.jpg?AWSAccessKeyId=ASIAZQ3DSS2QWCPW7YM3&Signature=nBsvjNJI0jvWGRiBtJNhOsQArNM%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEKr%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIHQFTUjf0tvVHiO%2F0QTURcNrximhn15cA5NR0yYecCjCAiEAkQx9Orp5Qr3pg%2FcuDVg5FBORvkVDw47JM0rwA4IHVXkqjwMIs%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2NTQ2NTQ0Nzc5ODUiDEdZgsbu0rrfNRKdxirjAky95WsBT3ZQJH0G3d9cz9bcXjTRixGXluCZMCknqJTJ9kRE20VTSnhWtNhTYN2v4A%2F7HHyCafbiTiEGxnOW1fhUceyCmj1l0lcuSPLD6Tkm45dD78HXCPlFkG4tENjRcG9Rv9dvgW8aW8cMVhAAqtbDL7NycJXqwlZjt68m0fbIOc3sIkEjxYtdiSUJG2SL1Zx4HXanvAfjXjp2noUoHRPbFyuwbnOhY7%2BVpQWKXLWZpynp4oZd%2FRnaqq6JIKVsKZbYqBw5ADdJH8IWDr1jB6E5MDY45%2FJrC4yrxzIZm1av0oY45W2jvPBebg97UbH4IYIzeV9L3g0J0Fa4mCjzdnkq%2BcKU%2BGQgPlBRRLIKUre0CoAWfphTVBhziDVQYBqsUUkmJ61wjJE8mA7fWqluCFl1wkOTu9%2BDsa73s5qfPzMpkZEL7EiSY8nGxGVesRpBSwxh%2F%2FEGsJqgr13BmAGb0SBlrl4wh43ZrwY6ngHPoDTHiXSVfY0ckumElE%2BIkqI3UdgEqvlmuuA79PddWfi9DdLE%2BdWBwt57BLoduYHziQPMkagdnf%2BPTiQ6fnVVEUctT91BA0UIJsFELW2R%2BdDRtnmkSx2RHjzPFDmWYsMuI6juwNGIdrCEd2nXC9YbSURtslTxV1f8iQe4ACrYL8dEf4AWIuc2A98NfKzEOPRzAJdXw7KOP2vzTq5w5Q%3D%3D&Expires=1710725132"
    prompt = {
        "image_string": image_url,
        "questions": question
    }

    gptVision = ChatGptVision("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", "gpt-4-vision-preview", prompt)

    json_data = gptVision.gpt_analysis_image_url()
    heading_summary_list = []
    cleaned_response = json_data.replace("\n", "").replace("\r", "").replace("\t", " ")
    heading_summary_dict = json.loads(cleaned_response)
    heading_summary_list.append(heading_summary_dict)
    try:
        for i, qa_dict in enumerate(heading_summary_dict):
            heading_summary_list.append(qa_dict)
    except Exception as e:
        logger.error(e)

    logger.info(f"heading - {heading_summary_list}")

