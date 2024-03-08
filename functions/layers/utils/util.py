import json
import os
from datetime import datetime, date

from loguru import logger
from sqlalchemy.inspection import inspect
from sqlalchemy.orm import class_mapper

from utils.custom_exceptions import MissingQueryParameterError, MissingBodyParameter, MissingPathParameterError
from utils.event_types import LambdaTriggerEventTypes


def sqlalchemy_obj_to_dict(obj):
    """Convert sqlalchemy objet to dict"""
    mapper = class_mapper(obj.__class__)
    columns = [column.key for column in mapper.columns]
    result = {}

    for column in columns:
        result[column] = getattr(obj, column)

    return result


def format_value(value):
    """Formats the value to make it JSON serializable."""
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    elif isinstance(value, bytes):
        return value.decode("utf-8")
    else:
        return value


def object_as_dict(obj):
    """Converts an SQLAlchemy object to a dictionary."""
    # Convert a single instance
    if not isinstance(obj, list):
        return {c.key: format_value(getattr(obj, c.key)) for c in inspect(obj).mapper.column_attrs}

    # Convert a list of instances
    return [{c.key: format_value(getattr(item, c.key)) for c in inspect(item).mapper.column_attrs} for item in obj]


def json_return(status_code, body):
    """Returns json response"""
    return {
        "isBase64Encoded": False,
        "statusCode": status_code,
        "body": json.dumps(body) if isinstance(body, dict) else {"message": f"{body}"},
        "headers": {"content-type": "application/json"},
    }


def get_event_type(event):
    """Returns the event type from the event."""
    if 'routeKey' in event:
        event_type = LambdaTriggerEventTypes.API_GATEWAY
    elif 'detail-type' in event:
        event_type = LambdaTriggerEventTypes.EVENT_BRIDGE
    else:
        event_type = LambdaTriggerEventTypes.UNKNOWN
    logger.info(f"event_type: {event_type}")
    return event_type


def get_query_parameter(event, key, required=True):
    """Returns the query parameter value from the event."""
    if "queryStringParameters" not in event:
        if not required:
            return None
        raise MissingQueryParameterError("queryStringParameters")
    query_parameter_value = event["queryStringParameters"].get(key, None)
    if required and query_parameter_value is None:
        raise MissingQueryParameterError(key)
    return query_parameter_value


def get_body_parameter(body, key, required=True):
    """Returns the body parameter value from the event."""
    if not isinstance(body, dict):
        try:
            body = json.loads(body)
        except Exception:
            if not required:
                return None
            raise MissingBodyParameter("body")
    body_parameter_value = body.get(key, None)
    if required and body_parameter_value is None:
        raise MissingBodyParameter(key)
    return body_parameter_value


def get_path_parameter(event, key, required=True):
    """Returns the path parameter value from the event."""
    if "pathParameters" not in event:
        if not required:
            return None
        raise MissingPathParameterError("pathParameters")
    path_parameter_value = event["pathParameters"].get(key, None)
    if required and path_parameter_value is None:
        raise MissingPathParameterError(key)
    return path_parameter_value


def get_host_url(event):
    """Returns the request method from the event."""
    request_method = event.get("headers", None).get("origin", None)
    if not request_method:
        request_method = os.getenv("verification_url", "https://docudive.vercel.app")
    logger.info(f"request_method: {request_method}")
    return request_method


def get_request_method(event):
    """Returns the request method from the event."""
    request_method = event["requestContext"]["http"]["method"]
    logger.info(f"request_method: {request_method}")
    return request_method


def get_request_user(event):
    """Returns the request user from the event."""
    username = event["requestContext"]["authorizer"]["lambda"]["user"]
    logger.info(f"username: {username}")
    return username


def get_http_path(event):
    """Returns the http path from the event."""
    http_path = event.get("requestContext", None).get("http", None).get("path", None).replace("/dev", "").replace("/prod", "")
    logger.info(f"http_path: {http_path}")
    return http_path


def iso_to_datetime(iso_string):
    """Converts ISO string to datetime object"""
    try:
        return datetime.strptime(iso_string, "%Y-%m-%dT%H:%M:%S.%fZ")
    except Exception:
        raise ValueError(f"invalid iso string - {iso_string}")


def load_multiple_json_files(data_string):
    """
    # Input format example
    data_string = '{"name": "Alice", "age": 25}{"country": "USA", "capital": "Washington"}'
    """
    import json

    parsed_data = []

    while data_string:
        try:
            obj, idx = json.JSONDecoder().raw_decode(data_string)
            parsed_data.append(obj)
            data_string = data_string[idx:].lstrip()
        except json.JSONDecodeError:
            break

    return parsed_data