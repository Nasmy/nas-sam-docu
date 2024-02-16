import os
from datetime import datetime

import stripe
from loguru import logger

from utils.custom_exceptions import RaiseCustomException

# For every user a customer ID should be created in Stripe and the stripe customer ID should be stored in DB.
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def create_stripe_customer(email=None, name=None, description=None, metadata=None) -> str:
    """
    :param email: str - Email address of the customer.
    :param name: str - Full name of the customer.
    :param description: str - Optional description for the customer.
    :param metadata: dict - Optional metadata for the customer.
    :return: dict - Details of the created customer or None if there was an error.
    """
    try:
        customer = stripe.Customer.create(email=email, name=name, description=description, metadata=metadata)
        return customer["id"]
    except stripe.error.StripeError as e:
        logger.error(f"Failed to create stripe customer: {e}")
        raise RaiseCustomException(
            status_code=500, message="Failed to create stripe customer", details={"stripe_error": f"{e}"}
        )


def add_payment_method(customer_id, token_id):
    """
    Add a payment method (card/bank_account) to a Stripe customer.
    :param customer_id: str - The Stripe customer ID.
    :param payment_type: str - Type of payment method ('card' or 'bank_account').
    :param payment_details: dict - The payment details.
    :return: str - ID of the added payment method or None if there was an error.
    """
    try:
        # Add token as a payment method to the customer
        payment_method = stripe.PaymentMethod.attach(token_id, customer=customer_id)
        logger.info(f"stripe: added payment method: {payment_method.id} for customer: {customer_id}")
        return payment_method.id
    except stripe.error.StripeError as e:
        logger.error(f"Failed to add payment method: {e}")
        raise RaiseCustomException(
            status_code=500, message="Failed to add payment method", details={"stripe_error": f"{e}"}
        )


def retrieve_all_payment_methods(customer_id):
    """
    Retrieve all payment methods associated with a specific Stripe customer.
    :param customer_id: str - ID of the Stripe customer.
    :return: list - List of payment methods or None if there was an error.
    """
    try:
        payment_methods = stripe.PaymentMethod.list(customer=customer_id).get("data")
        logger.info(f"stripe: retrieved payment methods for customer: {customer_id}")
        return payment_methods
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve payment methods: {e}")
        raise RaiseCustomException(
            status_code=500, message="Failed to retrieve payment methods", details={"stripe_error": f"{e}"}
        )


def delete_payment_method(payment_method_id):
    """
    Strip uses unique payment method id globally; So customer id is not required
    Delete a specific payment method using its ID.
    :param payment_method_id: str - ID of the Stripe payment method to be deleted.
    :return: dict - Details of the deleted payment method or None if there was an error.
    """
    try:
        deleted_payment_method = stripe.PaymentMethod.detach(payment_method_id)
        logger.info(f"stripe: deleted payment method: {payment_method_id}")
        return deleted_payment_method
    except stripe.error.StripeError as e:
        logger.error(f"Failed to delete payment method: {e}")
        raise RaiseCustomException(
            status_code=500, message="Failed to delete payment method", details={"stripe_error": f"{e}"}
        )


def get_invoices_for_customer(customer_id, limit=12):
    """
    Retrieve a list of invoices for a specific customer with required details.
    :param customer_id: str - The Stripe customer ID.
    :param limit: int - The number of records to retrieve (maximum is 100).
    :return: list - List of invoices with specified details.
    """
    try:
        limit = 10 if limit is None else int(limit)
        invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
    except stripe.error.StripeError as e:
        logger.error(f"Failed to retrieve invoices: {e}")
        raise RaiseCustomException(
            status_code=500, message="Failed to retrieve invoices", details={"stripe_error": f"{e}"}
        )

    invoice_detail_list = []

    for invoice in invoices:
        detail = {
            "invoice_number": invoice.number,
            "amount_due": invoice.amount_due / 100.0,
            "currency": invoice.currency,
            "status": invoice.status,
            "created_date": datetime.fromtimestamp(invoice.created).isoformat(),
            "pdf_link": invoice.invoice_pdf,
        }
        invoice_detail_list.append(detail)

    return invoice_detail_list


def update_customer_billing_details(customer_id, billing_details):
    """
    Update the billing details for a specific Stripe customer.
    :param customer_id: str - The Stripe customer ID.
    :param billing_details: dict - A dictionary containing billing details like name, address, email, etc.
    :return: dict - Updated customer object or None if there was an error.
    """
    try:
        customer = stripe.Customer.modify(
            customer_id,
            name=billing_details.get("billing_name", ""),
            email=billing_details.get("billing_email", ""),
            phone=billing_details.get("billing_phone", ""),
            address={
                "line1": billing_details.get("billing_line1", ""),
                "line2": billing_details.get("billing_line2", ""),
                "city": billing_details.get("billing_city", ""),
                "state": billing_details.get("billing_state", ""),
                "postal_code": billing_details.get("billing_postal_code", ""),
                "country": billing_details.get("billing_country", "")
            }
        )
        logger.info(f"stripe: updated customer billing details for customer: {customer_id}")
        return customer
    except stripe.error.StripeError as e:
        logger.error(f"Failed to update billing details: {e}")
        raise RaiseCustomException(
            status_code=500, message="Failed to update billing details", details={"stripe_error": f"{e}"}
        )


def create_subscription(customer_id, price_id, default_payment_method):
    """
    Create a subscription for a customer based on a price.
    :param customer_id: The Stripe ID of the customer.
    :param price_id: The Stripe ID of the price associated with the product. Displayed in the product details page
    :return: The subscription object if successful, otherwise an error.
    """
    try:
        subscription = stripe.Subscription.create(
            customer=customer_id,
            items=[{'price': price_id}],
            default_payment_method=default_payment_method
        )
        return subscription #this subscription item id should be stored in DB. This will be used in report_usage() function
    except stripe.error.StripeError as _:
        raise RaiseCustomException(
            status_code=500, message="Failed to create subscription", details={"customer_id": customer_id}
        )


def cancel_subscription(subscription_id):
    """
    Cancel a subscription.
    :param subscription_id: The Stripe ID of the subscription.
    :return: The subscription object if successful, otherwise an error.
    """
    try:
        subscription = stripe.Subscription.cancel(subscription_id)
        return subscription
    except stripe.error.StripeError as _:
        raise RaiseCustomException(
            status_code=500, message="Failed to cancel subscription", details={"subscription_id": subscription_id}
        )