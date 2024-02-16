import json
from enum import Enum
from typing import Dict

import boto3
from loguru import logger

from utils.custom_exceptions import RaiseCustomException


class CustomEventSources(str, Enum):
    SIGNIN = "signin"
    SIGNUP = "signup"
    OCR = "ocr"


class CustomEventDetailTypes(str, Enum):
    SUCCESS = "success"
    FAILURE = "failure"
    SPOT = "spot"


class EBWrapper:
    def __init__(self):
        self.event_client = boto3.client("events")

    def send_event(self, source: CustomEventSources, detail_type: CustomEventDetailTypes, detail: Dict,
                   event_bus_name="default"):
        # Define the custom event
        custom_event = {
            "Source": f"custom.{source.value}",
            "DetailType": f"{detail_type.value}",
            "Detail": json.dumps(detail),  # Custom details of the event
            "EventBusName": f"{event_bus_name}"  # Specify your custom event bus name if not using default
        }

        try:
            # Send the event to EventBridge
            response = self.event_client.put_events(
                Entries=[custom_event]
            )

            # Print the response from EventBridge
            logger.info(response)
        except Exception as e:
            logger.error(f"Failed to send event- {e}")
            raise RaiseCustomException(500, "Failed to send event")
        return response
