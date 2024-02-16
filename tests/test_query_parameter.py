from utils.custom_exceptions import MissingQueryParameterError
from utils.util import get_query_parameter


def test_query_param():
    event = {
        "queryStringParameters": {
            "document_id_missing": "1234",
            "chat_id": "1234",
        }
    }
    try:
        get_query_parameter(event, "document_id")
    except MissingQueryParameterError as e:
        assert e.key == "document_id"
        assert e.message == "Missing query parameter"
        assert e.status_code == 400
        assert e.details == {"query_parameter": "document_id"}
