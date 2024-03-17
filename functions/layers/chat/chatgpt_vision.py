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

    image_url = "https://nas-dd-input-files.s3.amazonaws.com/40c70010-803c-48c8-939c-b38bb45d88c1/844824ff-fb90-4caf-b46f-9829ccd0ce31.jpg?AWSAccessKeyId=ASIAZQ3DSS2QRDPKAJHU&Signature=P3StTeijFYS15lMhp4O5ff1wsow%3D&x-amz-security-token=IQoJb3JpZ2luX2VjELD%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FwEaCXVzLWVhc3QtMSJHMEUCIDrfBoskTVsqsT64B5JDfrUc%2FWdBiAf%2F%2Bdicc8FYrWChAiEAlyIjnm2M0IlaobYsYiLOrSwUTQbhALkZKO8ZEnJ%2BeE8qjwMIuf%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2NTQ2NTQ0Nzc5ODUiDF0EWg1Ce298D89b0CrjAqEKkzLfMrzet8dBVWp01e9iZaj0Pj%2F92EoOZsPQ7ijTO%2BqBC%2FzOCHjlGwo28MeS69HaqxfpHCFrie125PrcqxSc3K3W9enH4w5Hg2YnUkPYI%2FLedH6U2PIiWzES2GT35s%2BwxFKTEmQLA6binOP8eX8Om9DfLy5tHmylQTWIUpwHJz%2BR6f33uAXphZLtrHcb%2BmZI86zuFZfRxRqWpz4E%2F6X8cmhfN%2BtxvBJAvk7yoyD4Gokd5g5z5fKuEYcen6hjviewI0YWlh1mYLRFWoyDpc4uRHUIEPLNfqoxjO90QqlVDoApl3j0LjwUzNtkOMiit5bB%2BpRaD4%2F9kWVmNnPxVmr7ovI1C204bjmiaaXYE4vl6sRABsHNdOGysA3JUEfKAI423sMK2jC8n%2FncQ9%2Fu0JOJBELrppjUmxGhoDiMiCSmpumJWezsrQudCggaKXeTJz8pJpbWLKyqxXurUJZLbaDPIy8wxsbarwY6ngGspXStz%2BS2kNx%2FfJOWfpWsfmhCphuLzON6AR61R1jGTKY9UPCOmI5u0QLTfwU1JWpu03ZnRalKq%2BEgviEH6wl8WdnzeOI2aCkp1di7T4%2Fcnn6PU9W6HCyu2Ric%2F4c42M24OJELAWAAgAHN5PZHIKC0JHrMD%2Ff22H5gyX8w0JRZ1N3lfrEI6FGEK5Vy0Q1qStC1F7boRQN5y7l6o2qUSA%3D%3D&Expires=1710749213"
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

