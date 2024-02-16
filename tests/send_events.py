
import json

import boto3

aws_access_key_id = "key"
aws_secret_access_key = "akey"


def send_custom_event():
    # Initialize the EventBridge client
    client = boto3.client('events', aws_access_key_id=aws_access_key_id, aws_secret_access_key=aws_secret_access_key, region_name="us-east-2")

    # Define the custom event
    custom_event = {
        "Source": "custom.source",
        "DetailType": "CustomEvent",
        "Detail": json.dumps({"username": "docudive@yopmail.com"}),  # Custom details of the event
        "EventBusName": "default"  # Specify your custom event bus name if not using default
    }

    # Send the event to EventBridge
    response = client.put_events(
        Entries=[custom_event]
    )

    # Print the response from EventBridge
    print(response)

# def send_event_class():



if __name__ == '__main__':

    # Execute the function to send the event
    send_custom_event()
