""" Commone lambda authorizer """
import logging
import base64

def handler(event, context):
    return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "body": "Hello Docker!",
            "headers": {
                "content-type": "application/json"
            }
        }
