import json

import stripe

stripe.api_key = (
    "sk_test_51O21ZuEIx0QzrdrDkRpaZAixfOxeamUkUp18LW2IxRorplnTTjC2Fd7lMZHwqBVNMKkl3pV6cPFR4Wuq4KGS34Fm003470GztC"
)


def write_to_file(text):
    with open("test.txt", "a") as f:
        text = json.dumps(text, indent=4) if isinstance(text, dict) else str(text)
        f.write(f"{text}\n")


CUS_ID = "cus_PDEt1AsBojkJlx"


def create_subscription():
    ret = stripe.Subscription.create(
        customer=CUS_ID,
        items=[{"price": "price_1ONx8iEIx0QzrdrD9BtixDkp"}],
        default_payment_method="pm_1OP3dDEIx0QzrdrDPUKxxzRY",
    )
    print(ret)
    write_to_file(ret)


def cancel_subscription():
    ret = stripe.Subscription.cancel("sub_1OP4VKEIx0QzrdrDu5clTepi")
    print(ret)
    write_to_file(ret)

def create_invoice():
    ret = stripe.Invoice.create(customer=CUS_ID, default_payment_method="pm_1OP3dDEIx0QzrdrDPUKxxzRY")
    print(ret)
    write_to_file(ret)


if __name__ == "__main__":
    # create_invoice()
    # create_subscription()
    cancel_subscription()
