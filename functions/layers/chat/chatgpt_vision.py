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

""""
if __name__ == "__main__":
    question = (
        "\n\nBased on the image, suggest me 5 important possible questions and relevant answers."
        "Form your answer in the following exact json inside a list "
        'format:\n[{\n "question": "question text",\n "answer": "answer text"\n}]\n'
    )
    image_url = "https://nas-dd-input-files.s3.amazonaws.com/f1a73ad3-eedc-4a55-8cb9-dbc29414f989/0eb5e5e4-1dda-4a0e-91a5-96baa73abcf7.jpg?AWSAccessKeyId=ASIAZQ3DSS2Q63BXCKP5&Signature=POD74RGxn3n8NavYxk5nqSAokp0%3D&x-amz-security-token=IQoJb3JpZ2luX2VjEH0aCXVzLWVhc3QtMSJHMEUCIQDKMjWeLZj2oU%2B85DQh3TwwToTNW%2FxFquYxbxaaDd7N9wIgU0i7BggVxwTXrH1e%2BasaqUQB%2FpvnnwVZz6VpXfQ%2BJokqjwMIhv%2F%2F%2F%2F%2F%2F%2F%2F%2F%2FARAAGgw2NTQ2NTQ0Nzc5ODUiDJofKU1UJVlpSY7sqCrjAvEYaAquEYmDDvW%2FIyOvndfP8WgSvvb5aE6ekJZM1jxjb1ovxQVuU046nGNSOVE1QnV3R5YDqwWoAXZ6tjb4uoPstvSEPvQm99KtwR4h2mRfNkQwV9xI02s%2BVWF1wM1d8yC0EhitXwztQogPiIbkClOEhgcdeH3TlJeOnAzFYmHafe6LRwiVYmqokioOy6O61JOyOZh8MIYUQEWx5XHH0%2BlDkaATxK%2B49JYuBaVRe2W2Ujetf3ppct2FJiL6UH9Ki%2Ff689WSYG62uzER80szSliti0AmEBx3Ig2FnofYg3HdpZPD9RbpVweZTibSpu0d67ryztZNLqOjDOjHu5la5bDYF4Vb25TdQKYIOnFGyLTYVgjAlPKfmrLiKiE6D5va7nXMqdyMt%2F1Aj6qjjurM2CsTgPAi0nALtjG9j78I5Yt1sW81pVTF7rg0NgoVNO5N%2BELMqX2iiAPwA0Eohp%2FWloMeE9Uw26rPrwY6ngH%2FnlYGAahz4KP%2Bd%2Fym8LELjinQ6Vy0Mowgw5zAWHo0rRyeK%2FJwR%2BarLtSBp2M9BI620INTiutzecjty6StWdJcm9v6t9bZ8kh4nPVTrddG706s9X6bzjt7Y9x3NLwIQIwWSyyrORgmAKxv02RMYBPrLMocEvSI5VlvoeuNBImORBkjYImBBthevEvg%2Bu2kW%2Fa3H0rJBZFwKHipasinwA%3D%3D&Expires=1710565088"
    prompt = {
        "image_string": image_url,
        "questions": question
    }

    gptVision = ChatGptVision("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", "gpt-4-vision-preview", prompt)
    json_data = gptVision.gpt_analysis_image_url()
    print(json.loads(json_data))
    """""

