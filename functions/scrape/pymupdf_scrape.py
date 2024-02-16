import json
from pathlib import Path

import fitz
from loguru import logger

from text.bbox_utils import get_normalized_bounding_box, get_denormalized_bounding_box
from text.scrape_prediction import TextDetScrapePrediction
from text.span import Span
from text.timer import Timer


class PyMuPDF:
    def __init__(self, file_path: Path):
        self.file_path = file_path
        self.doc = fitz.open(self.file_path)

    def get_number_of_pages(self):
        return self.doc.page_count

    def get_page_wise_text(self):
        all_text = {}
        for page in self.doc:
            text = page.get_text("text")
            all_text[f"{page.number + 1}"] = text
            logger.info(f"Page {page.number + 1} text extracted!")
        logger.info(f"Page text scrape done for {self.doc.page_count} of pages")
        return all_text

    def get_all_spans(self):
        spans = []
        page_list = []
        block_bbox_list = {}
        for page in self.doc:
            span_id = 1
            page_number = page.number + 1
            page_list.append(page_number)

            page_width = page.rect.width
            page_height = page.rect.height

            text_instances = page.get_text("dict", flags=11)["blocks"]
            block_bbox_list[page_number] = {}
            for block_index, block in enumerate(text_instances):
                span_obj = None
                for line in block["lines"]:
                    for span in line["spans"]:
                        text = span["text"].strip()
                        if text == "":
                            continue

                        bbox = span["bbox"]
                        normalized_bbox = get_normalized_bounding_box(bbox, (page_height, page_width))
                        span_obj = Span(span_id, text, normalized_bbox, page_number, block_number=block_index + 1)
                        span_obj.clean()
                        spans.append(span_obj)
                        span_id += 1
                if span_obj is not None:
                    # append new line character
                    span_obj.text += "\n"
                # normalize block bbox
                normalized_block_bbox = get_normalized_bounding_box(block["bbox"], (page_height, page_width))
                block_bbox_list[page_number][block_index + 1] = normalized_block_bbox
        return spans, block_bbox_list

    def predict(self) -> TextDetScrapePrediction:
        with Timer("PyMuPDF predict"):
            spans, block_bbox_list = self.get_all_spans()
            ret = TextDetScrapePrediction(prediction=spans, block_bbox_list=block_bbox_list)
        return ret

    def get_image(self, page_number, image_path=None):
        page = self.doc[page_number - 1]
        zoom_x = 1.0  # horizontal zoom
        zoom_y = 1.0  # vertical zoom
        mat = fitz.Matrix(zoom_x, zoom_y)  # zoom factor 2 in each dimension
        pix = page.get_pixmap(matrix=mat)  # use 'mat' instead of the identity matrix
        image_path = f"page-{page_number:04d}.png" if image_path is None else image_path
        pix.save(image_path)
        return image_path


if __name__ == "__main__":
    import cv2
    import shutil

    pdf_path = Path("/home/dulanj/SB/DocuDive/1. What is Strategy.pdf")
    obj = PyMuPDF(pdf_path)
    prediction = obj.predict()
    # download all images
    output_path = pdf_path.parent / pdf_path.stem
    output_path.mkdir(exist_ok=True)

    # copy original pdf
    shutil.copy(pdf_path, output_path)

    for pg_index in range(1, obj.get_number_of_pages() + 1):
        image_save_path = output_path / f"page-{pg_index:04d}.png"
        obj.get_image(pg_index, image_save_path)

    dict = prediction.get_block_wise_text()

    output_dict_path = output_path / "output.json"
    with open(output_dict_path, "w") as f:
        json.dump(dict, f, indent=4)

    for page_no in dict.keys():
        print(f"page no: {page_no}")
        image = cv2.imread(obj.get_image(page_no))
        # print(dict[1])
        for key, value in dict[page_no].items():
            box_id = key
            block_bbox = value["bbox"]
            denormalized_bbox = get_denormalized_bounding_box(block_bbox, image.shape[:2])
            # print(block_bbox)
            # draw bounding box
            cv2.rectangle(
                image,
                (denormalized_bbox[0], denormalized_bbox[1]),
                (denormalized_bbox[2], denormalized_bbox[3]),
                (0, 255, 0),
                2,
            )
            # draw text
            cv2.putText(
                image,
                f"id: {box_id}",
                (denormalized_bbox[0], denormalized_bbox[1]),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.5,
                (0, 0, 255),
                1,
                cv2.LINE_AA,
            )
        output_image_path = output_path / f"page-{page_no:04d}-output.png"
        cv2.imwrite(str(output_image_path), image)
