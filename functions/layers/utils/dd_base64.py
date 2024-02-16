import base64


import base64

import cv2
import numpy as np


def get_base_64_string_from_image(image):
    _, im_arr = cv2.imencode(".jpg", image)  # im_arr: image in Numpy one-dim array format.
    im_bytes = im_arr.tobytes()
    base64_content = base64.b64encode(im_bytes)
    return base64_content.decode("utf-8")


def get_image_from_base_64_string(base64_string):
    if 'base64,' in base64_string:
        base64_string = base64_string.split('base64,')[1]
    base64_content = base64_string.encode("utf-8")
    image = base64.b64decode(base64_content)
    nparr = np.frombuffer(image, np.uint8)
    img_np = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    return img_np


def encode_base64_string(text):
    sample_string_bytes = text.encode("ascii")
    base64_bytes = base64.b64encode(sample_string_bytes)
    base64_string = base64_bytes.decode("ascii")
    return base64_string


def decode_base64_string(base64_string):
    base64_bytes = base64_string.encode("ascii")

    sample_string_bytes = base64.b64decode(base64_bytes)
    sample_string = sample_string_bytes.decode("ascii")
    return sample_string


def is_base64(sb):
    try:
        if isinstance(sb, str):
            # If there's any unicode here, an exception will be thrown and the function will return false
            if 'base64,' in sb:
                sb = sb.split('base64,')[1]
            sb_bytes = bytes(sb, "ascii")
        elif isinstance(sb, bytes):
            sb_bytes = sb
        else:
            raise ValueError("Argument must be string or bytes")
        return base64.b64encode(base64.b64decode(sb_bytes)) == sb_bytes
    except Exception:
        return False



