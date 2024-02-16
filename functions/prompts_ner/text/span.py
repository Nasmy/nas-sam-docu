import enum

from text.bbox_utils import get_iou, parent_bounding_box, get_normalized_bounding_box
from text.text_ele import BasicTextElement


class SpanTypes(str, enum.Enum):
    OCR = "ocr"
    SCRAPE = "scrape"


class Span(BasicTextElement):
    def __init__(self, id, text, bbox, page_number, block_number, span_type: SpanTypes = SpanTypes.SCRAPE):
        """
        Span class should have the normalize values of the bounding box
        """
        self.id = id
        self.text = text
        self.word_count = len(text.split())
        self.bbox = bbox
        self.page_number = page_number
        self.block_number = block_number
        self.span_type = span_type
        self.clean()

    @classmethod
    def create_span_from_words(cls, words, page_shape, page_number, block_number):
        """
        Create a span from a list of words
        page_shape: (height, width)
        """
        text_list = []
        bbox_list = []
        for word in words:
            text_list.append(word.text)
            normalized_bbox = get_normalized_bounding_box(word.bbox, page_shape)
            bbox_list.append(normalized_bbox)

        return cls(
            " ".join(text_list), parent_bounding_box(bbox_list), page_number, block_number, span_type=SpanTypes.OCR
        )

    def __repr__(self):
        return f"Span({self.text}, {self.bbox}, {self.page_number})"

    def iou(self, bbox):
        return get_iou(self.bbox, bbox)

    def clean(self):
        replace_list_of_tuples = [("�", " "), ("  ", " ")]
        for pair in replace_list_of_tuples:
            self.text = self.text.replace(pair[0], pair[1])
        return 1
