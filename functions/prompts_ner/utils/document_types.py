from enum import Enum


class DocumentTypes(str, Enum):
    PDF = "pdf"
    IMAGE_JPG = "jpeg"
    IMAGE_PNG = "png"
    DOC = "doc"
    TXT = "txt"
    UNKNOWN = "unknown"


def get_document_type_from_extension(extension: str):
    if extension.startswith("."):
        extension = extension[1:]

    if extension.lower() in ["pdf"]:
        return DocumentTypes.PDF
    elif extension.lower() in ["txt"]:
        return DocumentTypes.TXT
    elif extension.lower() in ["jpg", "jpeg"]:
        return DocumentTypes.IMAGE_JPG
    elif extension.lower() in ["png"]:
        return DocumentTypes.IMAGE_PNG
    elif extension.lower() in ["doc", "docx"]:
        return DocumentTypes.DOC
    else:
        return DocumentTypes.UNKNOWN


def doc_type_to_mime_type(doc_type: DocumentTypes):
    if doc_type == DocumentTypes.PDF:
        return "application/pdf"
    elif doc_type == DocumentTypes.TXT:
        return "text/plain"
    elif doc_type == DocumentTypes.IMAGE_JPG:
        return "image/jpeg"
    elif doc_type == DocumentTypes.IMAGE_PNG:
        return "image/png"
    elif doc_type == DocumentTypes.DOC:
        return "application/msword"
    else:
        return "application/octet-stream"


def get_doc_type_to_supported_extensions(doc_type: DocumentTypes):
    if doc_type == DocumentTypes.PDF:
        return ["pdf"]
    elif doc_type == DocumentTypes.TXT:
        return ["txt"]
    elif doc_type == DocumentTypes.IMAGE_JPG:
        return ["jpg", "jpeg"]
    elif doc_type == DocumentTypes.IMAGE_PNG:
        return ["png"]
    elif doc_type == DocumentTypes.DOC:
        return ["doc", "docx"]
    else:
        return ["unknown"]
