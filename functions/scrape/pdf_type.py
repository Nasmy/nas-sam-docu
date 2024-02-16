from copy import copy, deepcopy
from pathlib import Path

import fitz


def get_text_percentage(file_path) -> float:
    """
    Calculate the percentage of document that is covered by (searchable) text.

    If the returned percentage of text is very low, the document is
    most likely a scanned PDF
    """
    doc = fitz.open(file_path)
    total_page_area = 0.0
    total_text_area = 0.0

    for page_num, page in enumerate(doc):
        total_page_area = total_page_area + abs(page.rect)
        text_area = 0.0
        for b in page.get_text_blocks():
            r = fitz.Rect(b[:4])  # rectangle where block text appears
            text_area = text_area + abs(r)
        total_text_area = total_text_area + text_area
    doc.close()
    return total_text_area / total_page_area


def is_machine_readable(file_path):
    """
    If any page is readable this will return True
    """
    pdf = fitz.open(file_path)
    res = []
    for page in pdf:
        image_area = 0.0
        text_area = 0.0
        for b in page.get_text("blocks"):
            if '<image:' in b[4]:
                r = fitz.Rect(b[:4])
                image_area = image_area + abs(r)
            else:
                r = fitz.Rect(b[:4])
                text_area = text_area + abs(r)
        if image_area == 0.0 and text_area != 0.0:
            res.append(1)
        if text_area == 0.0 and image_area != 0.0:
            res.append(0)
    pdf.close()
    return all(res)


if __name__ == '__main__':
    file_name = "anti_money_image_based.pdf"
    doc = fitz.open(file_name)
    from functions.scrape.pymupdf_scrape import PyMuPDF

    pymu_obj = PyMuPDF(file_path=Path(file_name))
    page_count = pymu_obj.get_number_of_pages()

    print("Page count - ", page_count)
    # print(get_text_percentage(doc))
    print(is_machine_readable(pymu_obj.doc))
    for i in range(1, page_count + 1):
        print(i)
        pymu_obj.get_image(i, f"page-{i:04d}.jpg")
