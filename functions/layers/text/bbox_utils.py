import numpy as np
from loguru import logger
from numpy import ndarray

from text.word import Word


def get_intersection(a, b):
    """
    Get intersection of two bounding boxes, xyxy
    @param a:
    @param b:
    @return:
    """
    x_min = max(a[0], b[0])
    y_min = max(a[1], b[1])
    x_max = min(a[2], b[2])
    y_max = min(a[3], b[3])
    if x_min < x_max and y_min < y_max:
        return (x_max - x_min) * (y_max - y_min)
    return 0


def get_union(bbox1, bbox2):
    """
    Get the union of two bounding boxes
    @param bbox1:
    @param bbox2:
    @return:
    """
    x1, y1, x2, y2 = bbox1
    x3, y3, x4, y4 = bbox2
    area1 = (x2 - x1) * (y2 - y1)
    area2 = (x4 - x3) * (y4 - y3)
    intersection = get_intersection(bbox1, bbox2)
    return area1 + area2 - intersection


def get_iou(bbox1, bbox2, /):
    """
    Get IOU of two bounding boxes
    """
    _intersection = get_intersection(bbox1, bbox2)
    _union = get_union(bbox1, bbox2)
    _union = max([_union, 1])
    return _intersection / _union


def parent_bounding_box(bounding_box_list):
    """
    Get the parent bounding box from a list of bounding boxes
    @param bounding_box_list:
    @return:
    """
    x1, y1, x2, y2 = bounding_box_list[0]
    for _bounding_box in bounding_box_list:
        x1 = min(x1, _bounding_box[0])
        y1 = min(y1, _bounding_box[1])
        x2 = max(x2, _bounding_box[2])
        y2 = max(y2, _bounding_box[3])
    return [x1, y1, x2, y2]


def get_normalized_bounding_box(bounding_box, page_size):
    """
    Get the normalized bounding box
    @param bounding_box:
    @param page_size: height, width
    @return:
    """
    x1, y1, x2, y2 = bounding_box
    h, w = page_size
    return [x1 / w, y1 / h, x2 / w, y2 / h]


def get_denormalized_bounding_box(bounding_box, page_size):
    """
    Get the denormalized bounding box
    @param bounding_box:
    @param page_size: height, width
    @return:
    """
    x1, y1, x2, y2 = bounding_box
    h, w = page_size
    return [int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)]


def smaller_iou(b_box1, b_box2, threshold=None):
    _intersection = get_intersection(b_box1, b_box2)
    _bb_area1 = (b_box1[2] - b_box1[0]) * (b_box1[3] - b_box1[1])
    _bb_area2 = (b_box2[2] - b_box2[0]) * (b_box2[3] - b_box2[1])
    _min_area = min(_bb_area1, _bb_area2)
    small_iou = 0
    if _min_area > 0:
        small_iou = _intersection / _min_area

    return small_iou > threshold if threshold else small_iou


def remove_overlapping_words(word_list: ndarray[Word]):
    word_list = list(word_list)
    new_word_list = []
    skip_indexes = []
    for index_1, word_1 in enumerate(word_list):
        if index_1 in skip_indexes:
            continue
        for word_2 in word_list[index_1 + 1 :]:
            index_2 = word_list.index(word_2)
            word_1_text = word_1.text
            word_2_text = word_2.text
            word_1_bbox = word_1.bbox
            word_2_bbox = word_2.bbox
            threshold = 0.75
            iou = smaller_iou(word_1_bbox, word_2_bbox)
            if iou > threshold:
                len_word_1 = len(word_1.text)
                len_word_2 = len(word_2.text)
                if len_word_1 == len_word_2:
                    new_word_list.append(word_1)
                    logger.info(
                        f"Removing overlapping word '{word_2_text}' , keeping '{word_1_text}' "
                        f"because word lengths are equal[{len_word_1}]"
                    )
                elif len_word_1 > len_word_2:
                    new_word_list.append(word_1)
                    logger.info(
                        f"Removing overlapping word '{word_2_text}' , keeping '{word_1_text}' "
                        f"because word1_len[{len_word_1}] > word2_len[{len_word_2}]"
                    )
                else:
                    new_word_list.append(word_2)
                    logger.info(
                        f"Removing overlapping word '{word_1_text}' , keeping '{word_2_text}' "
                        f"because word2_len[{len_word_2}] > word1_len[{len_word_1}]"
                    )
                skip_indexes.append(index_2)
                break
        else:
            new_word_list.append(word_1)

    return np.array(new_word_list)


def get_denormalized_bounding_box(bounding_box, page_size):
    """
    Get the denormalized bounding box
    @param bounding_box:
    @param page_size: height, width
    @return:
    """
    x1, y1, x2, y2 = bounding_box
    h, w = page_size
    return [int(x1 * w), int(y1 * h), int(x2 * w), int(y2 * h)]
