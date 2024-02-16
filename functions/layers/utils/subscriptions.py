from enum import Enum


class SubscriptionTypes(str, Enum):
    FREE = "free"
    BASIC = "basic"
    PRO = "pro"


def get_monthly_limit(subscription_type: SubscriptionTypes):
    if subscription_type == SubscriptionTypes.FREE:
        return 1000
    elif subscription_type == SubscriptionTypes.BASIC:
        return 10000
    elif subscription_type == SubscriptionTypes.PRO:
        return 100000
    else:
        raise ValueError(f"Invalid subscription type {subscription_type}")