import os
import textwrap

import openai
from loguru import logger
from openai import InvalidRequestError

from chat.model_info import ModelInfo, OpenAIModels
from text.timer import Timer


class ChatGPT:
    total_input_tokens = 0
    total_output_tokens = 0

    def __init__(self, model: ModelInfo = OpenAIModels.get_model("gpt-3.5-turbo"), api_key=None, verbose=True):
        if api_key is None:
            api_key = os.getenv("openai_api_key_v2", None)
        logger.info("ChatGPT: api_key: {}".format(api_key))
        openai.api_key = api_key
        self.context_messages = []
        self.verbose = verbose
        # self.reset_context()
        self.model = None
        self.role = None
        self.set_model(model)

    def set_model(self, model: ModelInfo, role="friend"):
        self.model = model
        self.role = role
        logger.info(f"ChatGPT loading model: {self.model.name}")

    @staticmethod
    def get_all_gpt_models():
        models = openai.Model.list()
        model_list = [model.id for model in models.data if "gpt" in model.id]
        return model_list

    def get_current_model(self):
        return self.model.name

    def calculate_cost(self):
        total_cost = (
                ChatGPT.total_input_tokens * self.get_prompt_1k_cost()
                + ChatGPT.total_output_tokens * self.get_completion_1k_cost()
        )
        return total_cost / 1000

    def get_total_amount(self):
        return self.calculate_cost()

    def get_prompt_tokens(self):
        return ChatGPT.total_input_tokens

    def get_completion_tokens(self):
        return ChatGPT.total_output_tokens

    def get_total_tokens(self):
        return ChatGPT.total_input_tokens + ChatGPT.total_output_tokens

    def get_prompt_1k_cost(self):
        return self.model.prompt_token_1k

    def get_completion_1k_cost(self):
        return self.model.completion_token_1k

    def reset_context(self):
        self.context_messages = [{"role": "system", "content": f"Act as a {self.role}."}]

    def set_context_dict(self, context_dict):
        if context_dict:
            for dialog in context_dict["conversation"]:
                self.context_messages.append(dialog)
        else:
            self.reset_context()

    def get_context(self):
        return self.context_messages

    def get_context_dict(self):
        return {"conversation": self.context_messages}

    def initial_context(self, list_of_texts: list):
        for text in list_of_texts:
            self.context_messages.append({"role": "user", "content": text})

    @staticmethod
    def get_role_and_context(response):
        content = response.choices[0].message["content"]
        role = response.choices[0].message["role"]
        return role, content

    def usage(self, completion):
        ChatGPT.total_input_tokens += completion["usage"]["prompt_tokens"]
        ChatGPT.total_output_tokens += completion["usage"]["completion_tokens"]
        if self.verbose:
            for key in ["prompt_tokens", "completion_tokens", "total_tokens"]:
                logger.info(f"{key}: {completion['usage'][key]}")
            logger.info(
                f"Total cost for the session: ${self.calculate_cost():.3f}"
                f"[{ChatGPT.total_input_tokens}/{ChatGPT.total_output_tokens}]"
            )
            logger.info("-------------------------------------------")

    def chat_with_chatgpt(self, prompt: list, model="gpt-3.5-turbo"):
        messages = [{"role": "system", "content": f"Act as a {self.role}."}]
        for ppt in prompt:
            messages.append({"role": "user", "content": ppt})

        with Timer("Time to get the response"):
            completion = openai.ChatCompletion.create(model=model, messages=messages)
        role, content = self.get_role_and_context(completion)
        logger.info(f"{role}: {content}") if self.verbose else None
        self.usage(completion)
        return content

    def chat_with_context(self, prompt: str):
        """
        https://medium.com/mlearning-ai/using-chatgpt-api-to-ask-contextual-questions-within-your-application-a80b6a76da98
        :param prompt:
        :param model:
        :return:
        """
        logger.info(f"Prompt: {prompt}") if self.verbose else None
        content = None
        try:
            if prompt and prompt != "":
                self.context_messages.append({"role": "user", "content": prompt})
            with Timer("Time to get the response"):
                completion = openai.ChatCompletion.create(model=self.model.name, messages=self.context_messages)
                role, content = self.get_role_and_context(completion)
            self.context_messages.append({"role": "assistant", "content": content})
            logger.info(f"{role}: {content}") if self.verbose else None
            self.usage(completion)
        except InvalidRequestError as ir:
            logger.error(ir)
        return content

    def chat_with_gpt_vision_context(self, image_url, query):
        content = None
        try:
            if image_url and image_url != "" and query and query != "":
                prompt = [
                    {"type": "text", "text": query},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": image_url,
                        },
                    },
                ]
                self.context_messages.append({"role": "user", "content": prompt})
            with Timer("Time to get the response"):
                completion = openai.ChatCompletion.create(model=self.model.name, messages=self.context_messages)
                role, content = self.get_role_and_context(completion)

        except InvalidRequestError as ir:
            logger.error(ir)

        return content

    @staticmethod
    def wrap_content(text):
        # Wrap the text to a specific width
        wrapped_text = textwrap.wrap(text, width=100)
        logger.info("-------------------------------------------")
        # Print the wrapped text
        for index, line in enumerate(wrapped_text):
            logger.info(line)
        logger.info("-------------------------------------------")
