import enum

from prompts.insights import InsightTypes


class AnnotationTypes(str, enum.Enum):
    BOUNDING_BOX = "blocks"
    SPANS = "spans"
    PAGE_TEXT = "page_text"
    ALL_TEXT = "full_text"
    QUESTIONS = "questions"
    HEADINGS = "headings"
    SUMMARIES = "summary"
    TIMELINE = "timeline"
    CITED_EXAMPLES = "cited_examples"
    CITATIONS = "citations"
    TOPICS = "topics"
    INFO_SNIPPETS = "info_snippets"
    CUSTOM = "custom"
    NER = "ner"
    CHAT = "chat"
    LEGAL_INFO = "legal_info"
    EDUCATIONAL_INFO = "educational_info"
    FINANCIAL_INFO = "financial_info"
    EDITORIAL_INFO = "editorial_info"


def get_insight_type(annotation_type_name: str):
    if annotation_type_name in [
        AnnotationTypes.LEGAL_INFO.value, AnnotationTypes.FINANCIAL_INFO.value, AnnotationTypes.EDITORIAL_INFO.value,
        AnnotationTypes.EDUCATIONAL_INFO.value
    ]:
        return InsightTypes.BUSINESS
    if annotation_type_name in [
        AnnotationTypes.HEADINGS.value, AnnotationTypes.CITED_EXAMPLES.value, AnnotationTypes.CITATIONS.value,
        AnnotationTypes.TOPICS.value, AnnotationTypes.INFO_SNIPPETS.value, AnnotationTypes.NER.value,
        AnnotationTypes.SUMMARIES.value, AnnotationTypes.TIMELINE.value
    ]:
        return InsightTypes.ESSENTIAL
    return InsightTypes.BASIC


class AnnotationStatus(str, enum.Enum):
    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    EMPTY = "empty"
    TIMEOUT = "timeout"


def get_annotation_types(value: str) -> AnnotationTypes:
    if value in AnnotationTypes._value2member_map_:
        # return correct enum type
        return AnnotationTypes(value)
    else:
        return AnnotationTypes.BOUNDING_BOX
