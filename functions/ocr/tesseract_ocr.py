import os

import cv2
import numpy as np
import pytesseract
from loguru import logger as logging
from pandas import DataFrame

from text.bbox_utils import remove_overlapping_words
from text.scrape_prediction import TextDetScrapePrediction
from text.span import Span, SpanTypes
from text.timer import Timer
from text.word import Word


class TesseractOcr:
    def __init__(self, lang="eng", tess_data_dir=f"{os.getenv('LAMBDA_TASK_ROOT')}/tessdata", config=""):
        self.set_lang(lang)
        if tess_data_dir is not None:
            os.environ["TESSDATA_PREFIX"] = tess_data_dir
        logging.info(f"Loading Tesseract OCR 411 - {tess_data_dir}")
        self.lang = lang
        self.large_image_px = 1500
        self.line_number = []
        self.config = config
        self.block_bbox_dict = {}

    def predict_text_det_ocr(self, image, remove_duplicates=False):
        if isinstance(image, str) and os.path.exists(image):
            image = cv2.imread(image)
        word_array = self.detect_bboxes(image)
        if remove_duplicates:
            word_array = remove_overlapping_words(word_array)
        return word_array

    def set_lang(self, lang):
        self.lang = lang

    def get_version(self):
        try:
            version = [str(v) for v in pytesseract.get_tesseract_version().version[:3]]
            version_text = "Tesseract " + ".".join(version)
        except AttributeError:
            version = str(pytesseract.get_tesseract_version())
            version_text = "Tesseract " + version
        return version_text

    def _pre_process(self, image):
        """
        Pre-process image for tesseract OCR
        @param image:
        @return:
        """
        # check no of channels and if 4 channels convert to 3 channels
        if image.shape[2] == 4:
            image = cv2.cvtColor(image, cv2.COLOR_BGRA2BGR)
        # Convert to grayscale
        image = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        return image

    def detect(self, image) -> dict:
        return self.get_text(image)

    def get_text(self, image) -> dict:
        _ret = str(pytesseract.image_to_string(image, lang=self.lang, config=self.config))
        return {"text": _ret.strip()}

    def detect_bboxes(self, image):
        self.block_bbox_dict = {}
        with Timer("OCR Prediction time [v4.1.1]"):
            results_list = []
            h, w = image.shape[:2]
            logging.info(f"Image shape: {image.shape}")
            tes_out: DataFrame = pytesseract.image_to_data(
                image, config=self.config, lang=self.lang, output_type=pytesseract.Output.DATAFRAME
            )
            tes_out.dropna(inplace=True)
            logging.info(f"OCR output shape: {tes_out.shape}")

            for index, row in tes_out.iterrows():
                word_dict = row.to_dict()
                word_dict["id"] = f"{index}"
                word_dict["version"] = "4.1.1"
                word_dict["lang"] = self.lang
                word_dict["resolution"] = f"{w}x{h}"
                word_dict["config"] = self.config
                word_dict["g_line_num"] = self.get_line_number(
                    word_dict["block_num"], word_dict["par_num"], word_dict["line_num"]
                )
                block_number = word_dict["block_num"]
                text = word_dict["text"]
                if text.strip() == "":
                    continue

                word_bbox = (
                    word_dict["left"],
                    word_dict["top"],
                    word_dict["left"] + word_dict["width"],
                    word_dict["top"] + word_dict["height"],
                )
                normalized_bbox = (
                    word_bbox[0] / w,
                    word_bbox[1] / h,
                    word_bbox[2] / w,
                    word_bbox[3] / h,
                )
                word_obj = Word(
                    text=text,
                    bbox=normalized_bbox,
                    confidence=word_dict["conf"],
                    block_num=block_number,
                    g_line_num=word_dict["g_line_num"],
                )
                results_list.append(word_obj)

                if block_number not in self.block_bbox_dict:
                    self.block_bbox_dict[block_number] = normalized_bbox
                else:
                    # update the existing bounding box
                    self.block_bbox_dict[block_number] = (
                        min(self.block_bbox_dict[block_number][0], normalized_bbox[0]),
                        min(self.block_bbox_dict[block_number][1], normalized_bbox[1]),
                        max(self.block_bbox_dict[block_number][2], normalized_bbox[2]),
                        max(self.block_bbox_dict[block_number][3], normalized_bbox[3]),
                    )

            logging.info(f"OCR output shape: {len(results_list)}")
            return np.array(results_list) if len(results_list) > 0 else None

    def get_line_number(self, block, para, line):
        _unique_number = block * 10000 + para * 100 + line
        if _unique_number in self.line_number:
            return self.line_number.index(_unique_number) + 1
        else:
            self.line_number.append(_unique_number)
            return len(self.line_number)

    def predict_text_lines(self, image):
        word_array = self.predict_text_det_ocr(image)
        logging.info(f"Predicted {len(word_array)} words")
        span_array = []
        span_id = 1

        def merge_bounding_boxes(box1, box2=None):
            if box2 is None:
                return box1
            x1 = min(box1[0], box2[0])
            y1 = min(box1[1], box2[1])
            x2 = max(box1[2], box2[2])
            y2 = max(box1[3], box2[3])
            return [x1, y1, x2, y2]

        text_lines = dict()
        word: Word
        for word in word_array:
            _line__num_unique = word.g_line_num
            _text = word.text
            _conf = word.confidence
            _bbox = word.bbox

            if _line__num_unique in text_lines:
                text_lines[_line__num_unique]["text"] += " " + _text
                text_lines[_line__num_unique]["conf"].append(_conf)
                text_lines[_line__num_unique]["words"].append({"box": _bbox, "text": _text, "conf": _conf})
                text_lines[_line__num_unique]["bbox"] = merge_bounding_boxes(
                    text_lines[_line__num_unique]["bbox"], _bbox
                )
            else:
                text_lines[_line__num_unique] = {
                    "text": _text,
                    "bbox": _bbox,
                    "conf": [_conf],
                    "words": [{"box": _bbox, "text": _text, "conf": _conf}],
                    "block_num": word.block_num,
                }
        for _key, _value in text_lines.items():
            text_lines[_key]["conf"] = np.round(np.mean(text_lines[_key]["conf"]), 2)
            span = Span(
                id=span_id,
                text=_value["text"],
                bbox=_value["bbox"],
                page_number=1,
                block_number=_value["block_num"],
                span_type=SpanTypes.OCR,
            )
            span_array.append(span)
            span_id += 1
        logging.info(f"Predicted {len(span_array)} text lines")
        return np.array(span_array)

    def predict(self, image):
        image = self._pre_process(image)
        span_list = self.predict_text_lines(image)
        ret = np.array(span_list) if len(span_list) > 0 else None
        return TextDetScrapePrediction(ret, block_bbox_list={1: self.block_bbox_dict})
