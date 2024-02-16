
from dataclasses import dataclass


@dataclass
class Word:
    text: str
    bbox: tuple
    confidence: float
    block_num: int
    g_line_num: int
