import enum


class AnnotationTypes(str, enum.Enum):
    BOUNDING_BOX = "blocks"
    SPANS = "spans"
    PAGE_TEXT = "page_text"
    ALL_TEXT = "full_text"
    QUESTIONS = "questions"
    HEADINGS = "headings"
    SUMMARIES = "summary"
    TIMELINE = "timeline"
    NER = "ner"
    CHAT = "chat"


def get_annotation_types(value: str) -> AnnotationTypes:
    if value in AnnotationTypes._value2member_map_:
        # return correct enum type
        return AnnotationTypes(value)
    else:
        return AnnotationTypes.BOUNDING_BOX
