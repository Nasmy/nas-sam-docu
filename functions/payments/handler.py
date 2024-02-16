import json
import uuid
from datetime import datetime
from pprint import pprint

from loguru import logger

# Lambda layer
from db.database import Database
from db.tables import Users, Documents
from utils.util import object_as_dict


def handler(event, _):
    try:
        database = Database()
        with database.get_session() as session:
            username = event["requestContext"]["authorizer"]["lambda"]["user"]
            logger.info(f"username: {username}")
            if username:
                user = session.query(Users).filter(Users.username == username).first()
                if user:
                    # order by updated_at desc
                    docs = (
                        session.query(Documents)
                        .filter(Documents.user_id == user.id)
                        .order_by(Documents.uploaded_at.desc())
                        .all()
                    )
                    docs_dict_list = object_as_dict(docs)
                    keys_to_delete = ["user_id", "updated_at", "id", "is_deleted"]
                    # remove keys from dict list
                    for doc in docs_dict_list:
                        for key in keys_to_delete:
                            doc.pop(key, None)

                    status_code, msg = 200, {
                        "status": "success",
                        "message": "Fetched all documents",
                        "details": {
                            "user_id": user.id,
                            "timestamp": datetime.utcnow().isoformat(),
                            "document_list": docs_dict_list,
                        },
                    }
                else:
                    logger.error(f"unknown user: {username}")
                    status_code, msg = 404, {"status": "failed", "message": "unknown user", "details": {}}
            else:
                logger.error(f"unknown user: {username}")
                status_code, msg = 404, {"status": "failed", "message": "Authorizer unknown user", "details": {}}

        database.close_connection()
        return {
            "isBase64Encoded": False,
            "statusCode": status_code,
            "body": json.dumps(msg),
            "headers": {"content-type": "application/json"},
        }
    except Exception as exception:
        database.close_connection()
        error_id = uuid.uuid4()
        logger.error(f"an error occured, id: {error_id} error: {exception}")
        return {
            "isBase64Encoded": False,
            "statusCode": 500,
            "body": exception,
            "headers": {"content-type": "application/json"},
        }


import stripe

stripe.api_key = (
    "sk_test_51NrE8NLaEADorz8fN9rTbZRus1fzLlnshLavoZkjQ7QUV2W7tPFWjdSydIYJAISQszd9wk6qS9aCuK89TWngx5HS00u3gdU0Ot"
)


def create_product():
    response = stripe.Product.create(name="Gold Special")
    print(response)
    return response["id"]


def list_all_products():
    import stripe

    stripe.api_key = (
        "sk_test_51NrE8NLaEADorz8fN9rTbZRus1fzLlnshLavoZkjQ7QUV2W7tPFWjdSydIYJAISQszd9wk6qS9aCuK89TWngx5HS00u3gdU0Ot"
    )

    ret = stripe.Product.list(limit=3)
    pprint(ret)


def product_price(product_id):
    # Set your secret key. Remember to switch to your live secret key in production.
    # See your keys here: https://dashboard.stripe.com/apikeys

    ret = stripe.Price.create(
        currency="usd",
        unit_amount=1100,
        product=f"{product_id}",
    )
    print(ret)
    return ret["id"]


def payment_link(price_id):
    # Set your secret key. Remember to switch to your live secret key in production.
    # See your keys here: https://dashboard.stripe.com/apikeys
    import stripe

    stripe.api_key = (
        "sk_test_51NrE8NLaEADorz8fN9rTbZRus1fzLlnshLavoZkjQ7QUV2W7tPFWjdSydIYJAISQszd9wk6qS9aCuK89TWngx5HS00u3gdU0Ot"
    )

    ret = stripe.PaymentLink.create(line_items=[{"price": f"{price_id}", "quantity": 1}])
    print(ret)


if __name__ == "__main__":
    product_id = create_product()
    print(product_id)
    price_id = product_price(product_id)
    payment_link(price_id)

    # list_all_products()
