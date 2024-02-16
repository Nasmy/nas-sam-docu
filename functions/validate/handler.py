from datetime import datetime

from loguru import logger

from utils.util import json_return, get_request_user


def handler(event, _):
    logger.info(event)
    status_code, msg = 200, {
        "status": "success",
        "message": "Authorized user",
        "details": {
            "username": get_request_user(event),
            "timestamp": datetime.utcnow().isoformat(),
        },
    }
    return json_return(status_code, msg)
