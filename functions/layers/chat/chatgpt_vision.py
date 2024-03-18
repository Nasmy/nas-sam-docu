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

    image_url = "https://nas-dd-input-files.s3.amazonaws.com/40c70010-803c-48c8-939c-b38bb45d88c1/ea128fa4-e10d-40c4-9d77-3b7003eb1e2f.jpg?AWSAccessKeyId=ASIAZQ3DSS2QRKNZQ3BK&Signature=Hl2Lokn%2FfkEZraFAKbMFZ8vxEhA%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEMb%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJGMEQCIANZ9lVRv32rcCqTMHNef%2BzTf1b5imXYSomZ4GdDl9GgAiBO77SU1E%2BFZ7kiKYxkFmDXPG9rfvgbnIhHCsnoJOKmbiqPAwjP%2F%2F%2F%2F%2F%2F%2F%2F%2F%2F8BEAAaDDY1NDY1NDQ3Nzk4NSIMtdvCHvcYfOztgtCQKuMCKVpumKAo2IDgBrfTnZ%2BOSZUgXQnTALcxEo9fksA5qDeo5vjaVSiZi%2FWqdOj1MnRKprVi1976UgYaZOBRAxFLUJ2xfD5r515I%2FHy4IH8e80RSLnPEFgHd2vzTWclSkBP9UpQoXw99xUPIl%2FdG151wJiZ%2FrBFoUCxLawDy0sSiUNklunwYnfyZ7RO1i1wcvV5iLDBRhzt1w5xJuYi%2FUu3Z7OgGKQNk04qMWQ%2BxgpUVF9DDZfo2RM8CaZPMOc9RJWEEXvWtodxdvp0oj56vVPhwASht4cR%2BFsLZhvQfkiBn0A8Nx%2BS%2FtuML513Ru10CkNnqWoGDkEj5BLtPiH%2BJW%2B5dr0xVRhXiW8UheS8rtevHyoUrxiBi2AB%2BfxPPtW%2F%2FgxzJcWX1VMYxRWhTsmHa%2BxmYez7njuWCWP7yzl7lwguh%2B%2FYBhLtyOtynfd9MmAaOqqoFNUANJ35DXAeevu9aOYm8GyX0bzCxqN%2BvBjqfAV102lM1hB%2B0kYB1S2dBF8vwQ6pYre9dRzHAF%2BBG68lUYaUnVCCrTUssp9a2SiTJRHTRDXfvQOKL2yXMuOT8IaRjPi2qNjs7yWGIBa1wMwRCHKF9GgdxnlSq4n4r3igij4CTI%2BnpNfaMjbY2LOEJNMOCi%2Fp2OjXixFPzkVHzlRdViPw33BIVe31N1tmyy9U58yj14ReLQziIod79Ou0qyA%3D%3D&Expires=1710826962"
    prompt = {
        "image_string": image_url,
        "questions": question
    }

    gptVision = ChatGptVision("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", "gpt-4-vision-preview", prompt)

    received_string = gptVision.gpt_analysis_image_url()
    received_string = received_string.strip('```json')
    received_string = received_string.strip('```')
    # Replace '\n' with '\\n' to escape newline characters within the JSON string
    heading_summary_list = []
    print(received_string)
    heading_summary_dict = json.loads(received_string)

    try:
        for i, qa_dict in enumerate(heading_summary_dict):
            heading_summary_list.append(qa_dict)
    except Exception as e:
        logger.error(e)

    logger.info(f"heading - {heading_summary_list}")

