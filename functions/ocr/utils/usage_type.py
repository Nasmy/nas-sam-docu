from enum import Enum


class UsageTypes(str, Enum):
    USER_CHAT = "user_chat"
    ANNOTATIONS = "annotations"
    PAGES = "pages"


def get_credit_cost(usage_type: UsageTypes):
    if usage_type == UsageTypes.USER_CHAT:
        return 1
    elif usage_type == UsageTypes.ANNOTATIONS:
        return 1
    elif usage_type == UsageTypes.PAGES:
        return 1
    else:
        raise ValueError(f"Invalid usage type {usage_type}")
