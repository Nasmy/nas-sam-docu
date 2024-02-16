from dataclasses import dataclass, field
from enum import Enum
from typing import Optional, Dict, List, Union

from chat.chatgpt import ChatGPT


class ContextTypes(str, Enum):
    QUESTION = "question"
    HEADINGS = "headings"
    TEXT = "text"
    BLOCKS = "blocks"
    FULL = "full"
    LABEL_BRIEF = "label_brief"


@dataclass
class PromptResponse:
    prompt: Union[List, str]
    response: Union[List, Dict, str]
    debug_info: Dict
    gpt_model: Optional[ChatGPT]
    information: Dict = field(default_factory=dict)
