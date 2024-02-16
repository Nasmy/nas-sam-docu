import json

import cv2

from ocr.tesseract_ocr import TesseractOcr


def test_ocr():
    ocr_model = TesseractOcr(tess_data_dir="assets/tessdata")
    _image = cv2.imread("assets/statistics_image_1.jpg")
    text_prediction = ocr_model.predict(_image)
    ret = text_prediction.get_block_wise_text()
    print(json.dumps(ret, indent=4))
