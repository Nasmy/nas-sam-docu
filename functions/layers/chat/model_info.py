from dataclasses import dataclass

from loguru import logger
from utils.document_types import get_document_type_from_extension, DocumentTypes


@dataclass
class ModelInfo:
    name: str
    engine: str
    max_tokens: int
    max_words: int
    prompt_token_1k: float
    completion_token_1k: float


class OpenAIModels:
    gpt_3_5_turbo = "gpt-3.5-turbo"
    gpt_3_5_turbo_16k = "gpt-3.5-turbo-16k-0613"
    gpt_4_vision = "gpt-4-vision-preview"
    # ['gpt-3.5-turbo', 'gpt-3.5-turbo-0613', 'gpt-3.5-turbo-16k-0613', 'gpt-4-0314', 'gpt-3.5-turbo-16k', 'gpt-4', 'gpt-4-0613', 'gpt-3.5-turbo-0301']
    model_info = {
        gpt_3_5_turbo: {
            "name": gpt_3_5_turbo,
            "engine": "davinci",
            "max_tokens": 4097,
            "max_words": 3000,
            "prompt_token_1k": 0.0015,
            "completion_token_1k": 0.002,
        },
        gpt_3_5_turbo_16k: {
            "name": gpt_3_5_turbo_16k,
            "engine": "davinci",
            "max_tokens": 16384,
            "max_words": 12000,
            "prompt_token_1k": 0.003,
            "completion_token_1k": 0.004,
        },
        "gpt-4": {
            "name": "gpt-4",
            "engine": "davinci",
            "max_tokens": 8192,
            "max_words": 3000,
            "prompt_token_1k": 0.003,
            "completion_token_1k": 0.006,
        },
        gpt_4_vision: {
            "name": gpt_4_vision,
            "engine": "davinci",
            "max_tokens": 16384,
            "max_words": 12000,
            "prompt_token_1k": 0.003,
            "completion_token_1k": 0.004
        }
    }

    @staticmethod
    def get_model(model_name):
        return ModelInfo(**OpenAIModels.model_info[model_name])

    @staticmethod
    def can_enable_gpt_4_vision(file_ext):
        doc_type = get_document_type_from_extension(file_ext)
        if doc_type in [
            DocumentTypes.IMAGE_JPG,
            DocumentTypes.IMAGE_PNG,
        ]:
            return True

        return False

    @staticmethod
    def get_model_based_on_token_length(token_length):
        if token_length < 4000:
            return ModelInfo(**OpenAIModels.model_info[OpenAIModels.gpt_3_5_turbo])
        # elif token_length < 8000:
        #     return ModelInfo(**OpenAIModels.model_info["gpt-4"])
        else:
            return ModelInfo(**OpenAIModels.model_info[OpenAIModels.gpt_3_5_turbo_16k])

    @staticmethod
    def get_model_based_on_text_length(text_length):
        """
        # Words to tokens - https://platform.openai.com/tokenizer
        # Estimated token count = 1.5 * word count
        """
        # Words to tokens - https://platform.openai.com/tokenizer
        # Estimated token count = 1.5 * word count
        token_length = text_length * 1.5
        model = OpenAIModels.get_model_based_on_token_length(token_length)
        logger.info(f"get_model_based_on_text_length[{text_length}]: {model.name}")
        return model
