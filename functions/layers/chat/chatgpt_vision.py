from openai import OpenAI
import base64
import requests


# TODO Can do refactor. Just Written a Mock Code for Testing Purpose
class ChatGptVision:

    gpt_api_key = None
    gpt_model = None

    def __init__(self, gpt_api_key, gpt_model, prompt_data):
        self.gpt_api_key = gpt_api_key
        self.client = OpenAI(api_key=gpt_api_key)
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
        base64_image = self.encode_image(self.prompt["image_string"])
        image_path = f"data:image/jpeg;base64,{base64_image}"
        payload = self.get_vision_payload(image_url=image_path, gpt_questions=self.prompt["questions"])
        response = requests.post("https://api.openai.com/v1/chat/completions", headers=self.get_headers(), json=payload)

        print(response.json())

    def gpt_analysis_image_url(self):
        payload = self.get_vision_payload(image_url=self.prompt["image_string"], gpt_questions=self.prompt["questions"])

        response = requests.post("https://api.openai.com/v1/chat/completions", headers=self.get_headers(), json=payload)

        print(response.json())

    def analyse_image_string(self):

        if self.prompt["image_string"].startswith("http"):
            self.gpt_analysis_image_url()
        else:
            self.gpt_analysis_image_upload()


#if __name__ == "__main__":
    # prompt = {
        #"image_string": "https://upload.wikimedia.org/wikipedia/commons/thumb/d/dd/Gfp-wisconsin-madison-the-nature-boardwalk.jpg/2560px-Gfp-wisconsin-madison-the-nature-boardwalk.jpg",
        #"questions": "What’s in this image?"
    #}
    #gptVision = ChatGptVision("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", "gpt-4-vision-preview", prompt)
    #gptVision.analyse_image_string()
