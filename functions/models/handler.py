from db.database import Database


def handler(event, context):
    try:
        print(event)
        database = Database()
        database.create_all_tables()
        database.close_connection()
        return {
            "isBase64Encoded": False,
            "statusCode": 200,
            "body": "Meta created",
            "headers": {"content-type": "application/json"},
        }
    except Exception as exception:
        database.close_connection()
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": exception,
            "headers": {"content-type": "application/json"},
        }
