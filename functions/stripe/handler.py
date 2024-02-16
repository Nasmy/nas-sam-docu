import json
import uuid
from datetime import datetime

from loguru import logger
from sqlalchemy import func

from db.database import Database
from db.tables import Users, Payments, Subscriptions, PaymentMethods
from stripe_operations_v2 import (
    create_stripe_customer,
    add_payment_method,
    retrieve_all_payment_methods,
    delete_payment_method,
    get_invoices_for_customer,
    update_customer_billing_details,
    create_subscription,
    cancel_subscription,
)
from user.user_details import get_user_details, set_user_details
from utils.custom_exceptions import (
    UserNotFoundError,
    RaiseCustomException,
    MissingBodyParameter,
    MissingQueryParameterError,
)
from utils.subscriptions import SubscriptionTypes
from utils.util import json_return, get_request_method, get_http_path, get_body_parameter, get_query_parameter


def handler(event, _):
    logger.info(event)
    database = Database()
    with database.get_session() as session:
        try:
            http_path = get_http_path(event)
            request_method = get_request_method(event)
            if http_path == "/api/subscription-list":
                """Get subscription details"""
                status_code = 200
                if request_method == "GET":
                    all_subs = session.query(Subscriptions).filter(Subscriptions.is_active == True).all()
                    list_of_subs = []
                    for sub in all_subs:
                        list_of_subs.append(
                            {
                                "name": sub.name,
                                "display_name": sub.display_name,
                                "description": sub.description,
                                "amount": sub.amount,
                                "interval": sub.interval,
                                "credits": sub.credits,
                                "details": sub.details.split(":"),
                                "is_popular": sub.is_popular,
                            }
                        )
                    # sort by amount
                    list_of_subs.sort(key=lambda x: x["amount"], reverse=False)
                    api_response = {"status": "success", "message": "Subscriptions retrieved", "details": list_of_subs}
            else:
                username = event["requestContext"]["authorizer"]["lambda"]["user"]
                body = event.get("body", None)

                logger.info(f"username: {username} request method: {request_method} http_path: {http_path}")
                if not username:
                    raise UserNotFoundError(username)

                user = session.query(Users).filter(Users.username == username).first()
                if not user:
                    raise UserNotFoundError(username)

                """Check stripe customer exists"""
                payment_user = session.query(Payments).filter(Payments.user_id == user.id).first()

                if not payment_user or not payment_user.stripe_customer_id:
                    """Create stripe customer if not exists"""
                    logger.info(f"creating stripe customer for user: {user.username}")
                    metadata = {"user_id": user.id}
                    stripe_customer_id = create_stripe_customer(
                        email=user.username,
                        name=user.username,
                        metadata=metadata,
                    )
                    if not payment_user:
                        logger.info(f"creating stripe customer for user: {user.username} with id: {stripe_customer_id}")
                        free_sub_id = (
                            session.query(Subscriptions)
                            .filter(Subscriptions.name == SubscriptionTypes.FREE.value)
                            .first()
                            .id
                        )
                        payment_user = Payments(
                            user_id=user.id, subscription_id=free_sub_id, stripe_customer_id=stripe_customer_id
                        )
                        session.add(payment_user)
                        session.commit()
                    else:
                        logger.info(f"updating stripe customer for user: {user.username} with id: {stripe_customer_id}")
                        payment_user.stripe_customer_id = stripe_customer_id
                        session.commit()

            if http_path == "/api/payment-methods":
                """Create, List, Update and Delete a payment method to the customer"""
                status_code = 200
                if request_method == "POST":
                    logger.info(f"adding payment method for user: {user.username}")
                    body = json.loads(body)
                    token_id = get_body_parameter(body, "stripe_payment_method_id")
                    is_default = bool(get_body_parameter(body, "is_default", required=False))

                    is_existing_payment_method = (
                        session.query(PaymentMethods)
                        .filter(PaymentMethods.user_id == user.id)
                        .filter(PaymentMethods.payment_method_id == token_id)
                        .first()
                    )
                    if is_existing_payment_method:
                        raise RaiseCustomException(
                            400, f"Stripe payment method id already exists - {token_id} for user - {user.username}"
                        )

                    if is_default:
                        all_default_payment_methods = (
                            session.query(PaymentMethods)
                            .filter(PaymentMethods.user_id == user.id)
                            .filter(PaymentMethods.is_default == True)
                            .all()
                        )
                        for default_payment in all_default_payment_methods:
                            default_payment.is_default = False
                            logger.info(
                                f"removed default payment method: {default_payment.id} for user: {user.username}"
                            )

                    stripe_payment_method_id = add_payment_method(
                        customer_id=payment_user.stripe_customer_id, token_id=token_id
                    )
                    new_pay = PaymentMethods(
                        user_id=user.id, payment_method_id=stripe_payment_method_id, is_default=is_default
                    )
                    session.add(new_pay)
                    session.flush()
                    logger.info(f"added new payment method: {stripe_payment_method_id} for user: {user.username}")
                    api_response = {
                        "status": "success",
                        "message": "Payment method added",
                        "details": {"payment_method_id": str(new_pay.id)},
                    }
                elif request_method == "GET":
                    """Get all payment methods for the customer"""
                    logger.info(f"retrieving payment methods for user: {user.username}")
                    all_payment_methods = (
                        session.query(PaymentMethods.id, PaymentMethods.payment_method_id, PaymentMethods.is_default)
                        .filter(PaymentMethods.user_id == user.id)
                        .all()
                    )
                    payment_dict = {
                        pay_meth_id: {"is_default": is_default, "pay_id": pay_id}
                        for pay_id, pay_meth_id, is_default in all_payment_methods
                    }

                    all_payments = retrieve_all_payment_methods(payment_user.stripe_customer_id)
                    d_all_payments = []
                    for index, s_payment in enumerate(all_payments):
                        logger.info(f"payment: {index} - {s_payment}")
                        stripe_payment_method_id = s_payment["id"]
                        if stripe_payment_method_id not in payment_dict:
                            new_pay = PaymentMethods(user_id=user.id, payment_method_id=stripe_payment_method_id)
                            session.add(new_pay)
                            session.flush()
                            logger.info(
                                f"added new payment method: {stripe_payment_method_id} for user: {user.username}"
                            )
                            payment_dict[stripe_payment_method_id] = {
                                "is_default": False,
                                "pay_id": str(new_pay.id),
                            }
                        d_payment = {
                            "id": payment_dict[stripe_payment_method_id]["pay_id"],
                            "type": "card",
                            "card_name": s_payment["billing_details"]["name"],
                            "brand": s_payment["card"]["brand"],
                            "last4": s_payment["card"]["last4"],
                            "exp_month": s_payment["card"]["exp_month"],
                            "exp_year": s_payment["card"]["exp_year"],
                            "is_default": payment_dict[stripe_payment_method_id]["is_default"],
                        }
                        d_all_payments.append(d_payment)

                    # d_all_payments sort such that is_default True is first
                    d_all_payments.sort(key=lambda x: x["is_default"], reverse=True)
                    api_response = {
                        "status": "success",
                        "message": "Payment methods retrieved",
                        "details": {"payment_methods": d_all_payments},
                    }
                elif request_method == "DELETE":
                    """Delete a payment method for the customer"""
                    logger.info(f"deleting payment method for user: {user.username}")
                    payment_method_id = get_query_parameter(event, "payment_method_id")
                    payment_method = (
                        session.query(PaymentMethods)
                        .filter(PaymentMethods.user_id == user.id)
                        .filter(PaymentMethods.id == payment_method_id)
                        .first()
                    )
                    if not payment_method:
                        raise RaiseCustomException(400, f"payment method not found - {payment_method_id}")

                    if payment_method.is_default:
                        # count no of payment methods
                        payment_methods_count = (
                            session.query(func.count(PaymentMethods.id))
                            .filter(PaymentMethods.user_id == user.id)
                            .scalar()
                        )
                        if payment_methods_count > 1:
                            raise RaiseCustomException(
                                400, f"cannot delete default payment method - {payment_method_id}"
                            )

                    logger.info(f"deleting payment method: {payment_method_id} for user: {user.username}")
                    delete_payment_method(payment_method_id=payment_method.payment_method_id)
                    session.delete(payment_method)
                    api_response = {
                        "status": "success",
                        "message": "Payment method deleted",
                        "details": {"payment_method_id": payment_method_id},
                    }
                elif request_method == "PATCH":
                    """Set a payment method as default for the customer"""
                    logger.info(f"setting default payment method for user: {user.username}")
                    default_payment_id = get_body_parameter(body, "default_payment_method_id")
                    all_default_payment_methods = (
                        session.query(PaymentMethods)
                        .filter(PaymentMethods.user_id == user.id)
                        .filter(PaymentMethods.is_default == True)
                        .all()
                    )
                    for default_payment in all_default_payment_methods:
                        default_payment.is_default = False
                        logger.info(f"removed default payment method: {default_payment.id} for user: {user.username}")

                    default_payment = (
                        session.query(PaymentMethods)
                        .filter(PaymentMethods.user_id == user.id)
                        .filter(PaymentMethods.id == default_payment_id)
                        .first()
                    )
                    default_payment.is_default = True
                    logger.info(f"added default payment method: {default_payment.id} for user: {user.username}")
                    api_response = {
                        "status": "success",
                        "message": "Payment method set to default",
                        "details": {"payment_method_id": default_payment_id},
                    }
                else:
                    raise RaiseCustomException(400, f"invalid request method - {request_method}")
            elif http_path == "/api/invoices":
                """Get all invoices for the customer"""
                limit = get_query_parameter(event, "invoice_limit", required=False)
                if request_method == "GET":
                    list_of_invoice_details = get_invoices_for_customer(
                        customer_id=payment_user.stripe_customer_id, limit=limit
                    )
                else:
                    raise RaiseCustomException(400, f"invalid request method - {request_method}")
                status_code = 200
                api_response = {
                    "status": "success",
                    "message": "Payment invoices retrieved",
                    "details": {
                        "invoice_limit": limit,
                        "invoices": list_of_invoice_details,
                        "timestamp": datetime.utcnow().isoformat(),
                    },
                }
            elif http_path == "/api/billing":
                """Get billing details for the customer"""
                status_code = 200
                if request_method == "PUT":
                    body = json.loads(body)
                    billing_details = get_body_parameter(body, "billing_details")
                    if not isinstance(billing_details, dict):
                        raise RaiseCustomException(400, "invalid billing details")

                    """update user details"""
                    logger.info(f"billing details: {billing_details}")
                    logger.info(f"updating billing details for user: {user.username}")
                    created_attributes_list, updated_attributes_list = set_user_details(
                        session, user.id, billing_details
                    )

                    """update stripe customer"""
                    billing_data = get_user_details(session, username, filter_str="billing_")
                    update_customer_billing_details(
                        customer_id=payment_user.stripe_customer_id, billing_details=billing_data
                    )
                    api_response = {
                        "status": "success",
                        "message": "Payment billing details updated",
                        "details": {
                            "created_attributes": created_attributes_list,
                            "updated_attributes": updated_attributes_list,
                        },
                    }

                elif request_method == "GET":
                    user_data = get_user_details(session, username, filter_str="billing_")
                    api_response = {
                        "status": "success",
                        "message": "Payment billing details retrieved",
                        "details": {"user_billing_data": user_data},
                    }
                else:
                    raise RaiseCustomException(400, f"invalid request method - {request_method}")
            elif http_path == "/api/subscriptions":
                """Get subscription details"""
                status_code = 200
                if request_method == "GET":
                    all_subs = session.query(Subscriptions).filter(Subscriptions.is_active == True).all()
                    list_of_subs = []
                    for sub in all_subs:
                        is_subscribed = sub.id == payment_user.subscription_id
                        list_of_subs.append(
                            {
                                "name": sub.name,
                                "display_name": sub.display_name,
                                "description": sub.description,
                                "amount": sub.amount,
                                "interval": sub.interval,
                                "credits": sub.credits,
                                "details": sub.details.split(":"),
                                "is_popular": sub.is_popular,
                                "is_subscribed": is_subscribed,
                                "subscribed_at": payment_user.subscribed_at.isoformat() if is_subscribed else None,
                            }
                        )
                    # sort by amount
                    list_of_subs.sort(key=lambda x: x["amount"], reverse=False)
                    api_response = {
                        "status": "success",
                        "message": "User subscriptions retrieved",
                        "details": list_of_subs,
                    }
                elif request_method == "POST":
                    """Subscribe to a plan"""
                    body = json.loads(body)
                    subscription_name = get_body_parameter(body, "subscription_name")
                    if subscription_name != "free":
                        """
                        Check whether the user has a default payment method
                        """
                        default_payment_method = (
                            session.query(PaymentMethods)
                            .filter(PaymentMethods.user_id == user.id)
                            .filter(PaymentMethods.is_default == True)
                            .first()
                        )
                        if not default_payment_method:
                            raise RaiseCustomException(
                                400,
                                "Please add a default payment method to subscribe to a plan",
                                details={
                                    "username": user.username,
                                    "plan": subscription_name,
                                },
                            )

                    sub = (
                        session.query(Subscriptions)
                        .filter(Subscriptions.name == subscription_name)
                        .filter(Subscriptions.is_active == True)
                        .first()
                    )
                    if not sub:
                        raise RaiseCustomException(400, f"invalid subscription name - {subscription_name}")

                    if payment_user.subscription_id != sub.id:
                        """update stripe customer"""
                        logger.info(f"updating stripe customer for user: {user.username}")
                        """Cancel the current subscription"""
                        if payment_user.stripe_subscription_id:
                            ret = cancel_subscription(payment_user.stripe_subscription_id)
                            if ret["status"] != "canceled":
                                raise RaiseCustomException(
                                    400,
                                    "Failed to cancel the current subscription",
                                    details={
                                        "username": user.username,
                                        "plan": subscription_name,
                                        "response": ret,
                                    },
                                )
                            logger.info("Cancelled the current subscription")

                        if subscription_name != "free":
                            """
                            If user is selecting a paid plan, then subscribe to the plan
                            """
                            response = create_subscription(
                                customer_id=payment_user.stripe_customer_id,
                                price_id=sub.stripe_price_id,
                                default_payment_method=default_payment_method.payment_method_id,
                            )
                            if response["status"] != "active":
                                raise RaiseCustomException(
                                    400,
                                    "Failed to subscribe to the plan",
                                    details={
                                        "username": user.username,
                                        "plan": subscription_name,
                                        "response": response,
                                    },
                                )
                            stripe_subscription_id = response["id"]
                            payment_user.stripe_subscription_id = stripe_subscription_id
                            logger.info(
                                f"subscribed to plan: {subscription_name} for user: {user.username} with id: {stripe_subscription_id}"
                            )

                        else:
                            """
                            If user is selecting a free plan, then no need to call stripe
                            """
                            payment_user.stripe_subscription_id = None

                        payment_user.subscription_id = sub.id
                        payment_user.subscribed_at = datetime.utcnow()
                        session.commit()
                        api_response = {
                            "status": "success",
                            "message": "User subscribed to a new plan",
                            "details": {"subscription_name": subscription_name},
                        }
                    else:
                        status_code = 202
                        api_response = {
                            "status": "success",
                            "message": "User already subscribed to the plan",
                            "details": {"subscription_name": subscription_name},
                        }

        except (UserNotFoundError, RaiseCustomException, MissingBodyParameter, MissingQueryParameterError) as e:
            return json_return(
                e.status_code,
                {"status": "failed", "message": e.message, "details": e.details},
            )
        except FileExistsError as exception:
            error_id = uuid.uuid4()
            logger.exception(exception)
            logger.error(f"an error occurred, id: {error_id} error: {exception}")
            return {
                "isBase64Encoded": False,
                "statusCode": 500,
                "body": exception,
                "headers": {"content-type": "application/json"},
            }
        else:
            session.commit()
            return json_return(status_code, api_response)
