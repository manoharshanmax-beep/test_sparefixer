"""
Payment gateway wrapper. Selects Stripe or Razorpay via PAYMENT_PROVIDER,
so the orders route layer stays gateway-agnostic.
"""
import logging

import stripe
import razorpay

logger = logging.getLogger("sparefixer")


def create_payment_intent(order, config):
    """
    Kicks off a payment for the given Order.
    Returns a dict the frontend uses to complete checkout:
      - stripe: {"provider": "stripe", "client_secret": ..., "payment_ref": ...}
      - razorpay: {"provider": "razorpay", "razorpay_order_id": ..., "key_id": ...}
    """
    provider = config.get("PAYMENT_PROVIDER", "stripe")
    amount_minor_units = int(round(float(order.total_price) * 100))  # paise / cents
    currency = config.get("CURRENCY", "INR").lower()

    if provider == "stripe":
        return _create_stripe_intent(order, amount_minor_units, currency, config)
    if provider == "razorpay":
        return _create_razorpay_order(order, amount_minor_units, currency, config)

    raise ValueError(f"Unsupported PAYMENT_PROVIDER: {provider}")


def _create_stripe_intent(order, amount_minor_units, currency, config):
    stripe.api_key = config.get("STRIPE_SECRET_KEY")
    intent = stripe.PaymentIntent.create(
        amount=amount_minor_units,
        currency=currency,
        metadata={"order_id": order.id, "user_id": order.user_id},
        automatic_payment_methods={"enabled": True},
    )
    return {
        "provider": "stripe",
        "client_secret": intent["client_secret"],
        "payment_ref": intent["id"],
    }


def _create_razorpay_order(order, amount_minor_units, currency, config):
    client = razorpay.Client(auth=(config.get("RAZORPAY_KEY_ID"), config.get("RAZORPAY_KEY_SECRET")))
    rp_order = client.order.create({
        "amount": amount_minor_units,
        "currency": currency.upper(),
        "receipt": order.id,
        "notes": {"order_id": order.id, "user_id": order.user_id},
    })
    return {
        "provider": "razorpay",
        "razorpay_order_id": rp_order["id"],
        "key_id": config.get("RAZORPAY_KEY_ID"),
        "amount": amount_minor_units,
        "currency": currency.upper(),
    }


def verify_stripe_webhook(payload, sig_header, config):
    return stripe.Webhook.construct_event(payload, sig_header, config.get("STRIPE_WEBHOOK_SECRET"))


def verify_razorpay_signature(params, config):
    client = razorpay.Client(auth=(config.get("RAZORPAY_KEY_ID"), config.get("RAZORPAY_KEY_SECRET")))
    client.utility.verify_payment_signature(params)  # raises SignatureVerificationError on failure
