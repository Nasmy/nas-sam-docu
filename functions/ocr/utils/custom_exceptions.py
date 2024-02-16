class MissingQueryParameterError(Exception):
    def __init__(self, key):
        self.key = key
        self.status_code = 400
        self.message = "Missing query parameter"
        self.details = {"query_parameter": self.key}
        super().__init__(self.message)


class MissingBodyParameter(Exception):
    def __init__(self, key):
        self.key = key
        self.status_code = 400
        self.message = "Missing body parameter"
        self.details = {"body_parameter": self.key}
        super().__init__(self.message)


class MissingPathParameterError(Exception):
    def __init__(self, key):
        self.key = key
        self.status_code = 400
        self.message = "Missing path parameter"
        self.details = {"path_parameter": self.key}
        super().__init__(self.message)


class UserNotFoundError(Exception):
    def __init__(self, username):
        self.username = username
        self.status_code = 401
        self.message = "User not found"
        self.details = {"username": self.username}
        super().__init__(self.message)


class DocumentNotFoundError(Exception):
    def __init__(self, document_id):
        self.document_id = document_id
        self.status_code = 404
        self.message = "Document not found"
        self.details = {"document_id": self.document_id}
        super().__init__(self.message)


class ChatNotFoundError(Exception):
    def __init__(self, chat_id):
        self.chat_id = chat_id
        self.status_code = 404
        self.message = "Chat not found"
        self.details = {"chat_id": self.chat_id}
        super().__init__(self.message)


class EmailSendError(Exception):
    def __init__(self, to_address):
        self.to_address = to_address
        self.status_code = 500
        self.message = "Failed to send email"
        self.details = {"to_address": self.to_address}
        super().__init__(self.message)


class RaiseCustomException(Exception):
    """Raise custom exception"""

    def __init__(self, status_code, message, details=None):
        self.status_code = status_code
        self.message = message
        self.details = details if details else {}
        super().__init__(self.message)


class MissingEnvironmentVariableError(Exception):
    """Missing environment variable error"""

    def __init__(self, key):
        self.key = key
        self.status_code = 500
        self.message = f"Missing environment variable, {key}"
        self.details = {"key": self.key}
        super().__init__(self.message)