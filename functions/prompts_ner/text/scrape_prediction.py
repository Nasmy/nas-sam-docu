from copy import deepcopy

from text.bbox_utils import get_iou
from text.span import Span


class TextDetScrapePrediction:
    def __init__(self, prediction, block_bbox_list):
        self.blocks = {}
        for span in prediction:
            page_no = span.page_number
            block_no = span.block_number
            if page_no not in self.blocks:
                self.blocks[page_no] = []
            self.blocks[page_no].append(block_no)

        self.prediction = prediction
        self.pages = list(self.blocks.keys())
        self.block_bbox_list = block_bbox_list

    def get_word_count(self):
        return sum([span.word_count for span in self.prediction])

    # Serch the text
    def get_block_wise_text(self):
        block_wise_text = {"pages": {}}
        for page_no in self.pages:
            block_wise_text["pages"][page_no] = {"blocks": {}}
            for block_no in self.blocks[page_no]:
                block_text = self.get_text(page_number=page_no, block_number=block_no)
                block_wise_text["pages"][page_no]["blocks"][block_no] = {
                    "text": block_text,
                    "bbox": self.block_bbox_list[page_no][block_no],
                }
        return block_wise_text

    def get_span_wise_text(self):
        span_wise_text = {"pages": {}}
        for page_no in self.pages:
            span_wise_text["pages"][page_no] = {"spans": {}}
            for span in self.get_prediction(page_number=page_no):
                span_wise_text["pages"][page_no]["spans"][span.id] = {
                    "text": span.text,
                    "bbox": span.bbox,
                }
        return span_wise_text

    def get_page_wise_json(self):
        page_wise_json = {"pages": {}}
        for page_no in self.pages:
            page_wise_json["pages"][page_no] = {"text": self.get_text(page_number=page_no)}
        return page_wise_json

    def get_page_list(self):
        return self.pages

    def get_block_list(self, page_number):
        return self.blocks[page_number]

    def is_a_page(self):
        return len(self.pages) == 1

    def get(self, page_number):
        return TextDetScrapePrediction(deepcopy(self.get_prediction(page_number)))

    def get_prediction(self, page_number=None, block_number=None, bounding_box=None, word_limit=None, word_offset=None):
        if self.prediction is None:
            return []
        if page_number is not None and bounding_box is not None:
            return [span for span in self.get_prediction(page_number) if get_iou(span.bbox, bounding_box) > 0.1]
        elif page_number is not None and block_number is not None:
            return [
                span
                for span in self.prediction
                if span.page_number == page_number and span.block_number == block_number
            ]
        elif page_number is not None:
            return [span for span in self.prediction if span.page_number == page_number]
        elif word_limit is not None:
            if word_offset is None:
                word_offset = 0
            span_list = []
            current_count = 0
            added_count = 0
            for span in self.prediction:
                current_count += span.word_count
                if current_count < word_offset:
                    continue
                if added_count >= word_limit:
                    break
                span_list.append(span)
                added_count += span.word_count
            return span_list
        else:
            return self.prediction

    def add_span(self, span: Span, page_number):
        """
        Add the span in the correct location
        """
        if page_number not in self.pages:
            self.pages.append(page_number)

        _, y1, _, _ = span.bbox
        _span_index = 0
        for _span in self.get_prediction(page_number):
            _x1, _y1, _x2, _y2 = _span.bbox
            if y1 <= _y1:
                _span_index = self.prediction.index(_span)
                self.prediction.insert(_span_index, span)
                break
        else:
            self.prediction.insert(_span_index - 1, span)

    def get_bounding_boxes(self, page_number=None):
        return [_span.bbox for _span in self.get_prediction(page_number)]

    def get_text(self, page_number=None, block_number=None, word_limit=None, word_offset=None):
        return " ".join(self.get_texts(page_number, block_number, word_limit, word_offset))

    def get_texts(self, page_number=None, block_number=None, word_limit=None, word_offset=None):
        return [
            _span.text
            for _span in self.get_prediction(page_number, block_number, word_limit=word_limit, word_offset=word_offset)
            if _span.clean()
        ]

    def get_block_text(self, page_block_list: list):
        block_text = []
        # page_block_list sort by page_no, block_no
        sorted_list = sorted(page_block_list, key=lambda x: (x[0], x[1]))
        for page_no, block_no in sorted_list:
            block_text.extend(self.get_texts(page_number=page_no, block_number=block_no))
        return " ".join(block_text)

    def set_prediction(self, prediction):
        self.prediction = prediction

    def get_span_list(self):
        return self.prediction

    def __len__(self):
        return len(self.get_prediction())

    def show(self, page_number=None):
        for _span in self.get_prediction(page_number):
            print(_span)

    def get_bbox_text(self, page_number, bounding_box):
        return [_span.text for _span in self.get_prediction(page_number, bounding_box=bounding_box)]

    def reorder(self):
        """
        Reorder the spans in the prediction page wise
        """
        pass
