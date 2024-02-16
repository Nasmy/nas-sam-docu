from enum import Enum


class LambdaTriggerEventTypes(str, Enum):
    API_GATEWAY = "api_gateway"
    EVENT_BRIDGE = "event_bridge"
    UNKNOWN = "unknown"
