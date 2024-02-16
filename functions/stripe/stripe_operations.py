import os
import time
import stripe

from utils.custom_exceptions import RaiseCustomException

# For every user a customer ID should be created in Stripe and the stripe customer ID should be stored in DB.
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")


def create_stripe_customer(email=None, name=None, description=None, metadata=None):
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
    except stripe.error.StripeError as _:
        raise RaiseCustomException(
            status_code=500, message="Failed to create stripe customer", details={"username": email}
        )


def add_payment_method(customer_id, payment_type, payment_details):
    """
    Add a payment method (card/bank_account) to a Stripe customer.
    :param customer_id: str - The Stripe customer ID.
    :param payment_type: str - Type of payment method ('card' or 'bank_account').
    :param payment_details: dict - The payment details.
    :return: str - ID of the added payment method or None if there was an error.
    """
    try:
        # Convert payment details to a token
        token = stripe.Token.create(
            payment_type, payment_details
        )
        
        # Add token as a payment method to the customer
        payment_method = stripe.PaymentMethod.attach(
            token.id,
            customer=customer_id
        )

        return payment_method.id
    except stripe.error.StripeError as _:
        raise RaiseCustomException(
            status_code=500, message="Failed to add payment method", details={"customer_id": customer_id}
        )


def retrieve_all_payment_methods(customer_id):
    """
    Retrieve all payment methods associated with a specific Stripe customer.
    :param customer_id: str - ID of the Stripe customer.
    :return: list - List of payment methods or None if there was an error.
    """
    try:
        payment_methods = stripe.PaymentMethod.list(customer=customer_id).get("data")
        return payment_methods
    except stripe.error.StripeError as _:
        raise RaiseCustomException(
            status_code=500, message="Failed to retrieve payment methods", details={"customer_id": customer_id}
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
        return deleted_payment_method
    except stripe.error.StripeError as _:
        raise RaiseCustomException(
            status_code=500, message="Failed to delete payment method", details={"payment_method_id": payment_method_id}
        )


def get_invoices_for_customer(customer_id, limit=12):
    """
    Retrieve a list of invoices for a specific customer with required details.
    :param customer_id: str - The Stripe customer ID.
    :param limit: int - The number of records to retrieve (maximum is 100).
    :return: list - List of invoices with specified details.
    """
    try:
        invoices = stripe.Invoice.list(customer=customer_id, limit=limit)
    except stripe.error.StripeError as _:
        raise RaiseCustomException(
            status_code=500, message="Failed to retrieve invoices", details={"customer_id": customer_id}
        )

    invoice_details = []

    for invoice in invoices:
        detail = {
            'invoice_number': invoice.number,
            'amount_due': invoice.amount_due / 100.0,
            'currency': invoice.currency,
            'status': invoice.status,
            'created_date': invoice.created,
            'pdf_link': invoice.invoice_pdf
        }
        invoice_details.append(detail)

    return invoice_details


def create_subscription(customer_id, price_id):
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
            expand=['latest_invoice.payment_intent']
        )
        return subscription #this subscription item id should be stored in DB. This will be used in report_usage() function
    except stripe.error.StripeError as _:
        raise RaiseCustomException(
            status_code=500, message="Failed to create subscription", details={"customer_id": customer_id}
        )

def report_usage(subscription_item_id, quantity, timestamp=None): #This should be fired everyday
    """
    Report usage for a metered billing subscription.
    :param subscription_item_id: str - The ID of the subscription item.
    :param quantity: int - The quantity/amount of usage to report.
    :param timestamp: int (optional) - The timestamp at which the usage occurred (in Unix time). Defaults to current time.
    :return: dict - Details of the created usage record.
    """
    try:
        usage_record = stripe.UsageRecord.create(
            subscription_item=subscription_item_id,
            quantity=quantity,
            timestamp=timestamp or int(time.time())
        )
        return usage_record
    except stripe.error.StripeError as _:
        raise RaiseCustomException(
            status_code=500, message="Failed to report usage", details={"subscription_item_id": subscription_item_id}
        )

def create_payment_intent(amount, currency, customer_id, payment_method_id):
    """
    Create a PaymentIntent for a specific customer and payment method type.
    :param amount: int - The amount to be charged in the smallest currency unit (e.g., cents).
    :param currency: str - The currency for the charge (e.g., 'aud' for Australian Dollars).
    :param payment_method_id: retrived from the function retrieve_all_payment_methods()/add_payment_method()
    :param customer_id: str - The Stripe customer ID.
    :return: dict - Details of the created PaymentIntent.
    """
    try:
        payment_intent = stripe.PaymentIntent.create(
            amount=amount,
            currency=currency,
            customer=customer_id,
            payment_method=payment_method_id,
            confirm=True,  # Automatically confirm the payment
        )
        return payment_intent
    except stripe.error.StripeError as _:
        raise RaiseCustomException(
            status_code=500, message="Failed to create PaymentIntent", details={"customer_id": customer_id}
        )

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
            name=billing_details.get("name"),
            email=billing_details.get("email"),
            phone=billing_details.get("phone"),
            address={
                "line1": billing_details.get("line1"),
                "line2": billing_details.get("line2"),
                "city": billing_details.get("city"),
                "state": billing_details.get("state"),
                "postal_code": billing_details.get("postal_code"),
                "country": billing_details.get("country")
            }
        )
        return customer
    except stripe.error.StripeError as _:
        raise RaiseCustomException(
            status_code=500, message="Failed to update billing details", details={"customer_id": customer_id}
        )

############################create_payment_intent()######################################
""" payment_intent = create_payment_intent(1000, 'usd', 'cus_XXXXX', 'pm_XXXXX', billing_details)
if payment_intent['status'] == 'succeeded':
    print("Payment succeeded!")
else:
    print(f"Payment failed with status: {payment_intent['status']}") 

billing_details = {
    "address": {
        "city": "San Francisco",
        "country": "US",
        "line1": "1234 Main St",
        "line2": "Apt 4B",
        "postal_code": "94111",
        "state": "CA"
    },
    "email": "johndoe@example.com",
    "name": "John Doe",
    "phone": "+1234567890"
}

"""


############################create_stripe_customer()######################################
""" create_stripe_customer(email="k2@k.com", name="k m", description="Test customer", metadata={"user_id": "docudive id"})
print(customer_details["id"])  # create DB record across docudive customer id """


############################add_payment_method()######################################

""" card_details = {
    "number": "4242424242424242",
    "exp_month": 12,
    "exp_year": 2023,
    "cvc": "123"
}

bank_account_details = {
    "country": "US",
    "currency": "usd",
    "account_holder_name": "John Doe",
    "account_holder_type": "individual",
    "routing_number": "110000000",
    "account_number": "000123456789"
}

# To add a card:
add_payment_method("cus_XXXXX", "card", card_details)

# To add a bank account:
add_payment_method("cus_XXXXX", "bank_account", bank_account_details) """


############################report_usage()######################################
""" subscription_item_id = "si_XXXXXX"  # You get this ID when you create a subscription for the customer
quantity = 100  # The actual usage amount, e.g., the number of API calls, GB of data, hours of service, etc.
report_usage(subscription_item_id, quantity) """


############################retrieve_all_payment_methods()######################################

""" payment_methods = retrieve_all_payment_methods(customer_id)
if payment_methods:
    for method in payment_methods:
        if method.type == "card":
            card = method.card
            print(f"Card Details:")
            print(f"Brand: {card.brand}")
            print(f"Expiry Month: {card.exp_month}")
            print(f"Expiry Year: {card.exp_year}")
            print(f"Last 4 Digits: {card.last4}")
            print("\n")
        elif method.type == "bank_account":
            bank_account = method.bank_account
            print(f"Bank Account Details:")
            print(f"Bank Name: {bank_account.bank_name}")
            print(f"Country: {bank_account.country}")
            print(f"Last 4 Digits: {bank_account.last4}")
            print(f"Routing Number: {bank_account.routing_number}")
            print("\n")
 """

############################update_customer_billing_details()######################################
""" billing_info = {
    "name": "John Doe",
    "email": "john@example.com",
    "phone": "+1234567890",
    "line1": "123 Street Ave",
    "line2": "Apt 4B",
    "city": "City",
    "state": "State",
    "postal_code": "12345",
    "country": "US"
}

updated_customer = update_customer_billing_details("cus_XXXXXXX", billing_info) """
