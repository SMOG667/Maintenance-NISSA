"""Integration Stripe pour la facturation mensuelle."""

import os
import logging
import stripe

logger = logging.getLogger("nissa.stripe")

PRICE_AMOUNT = 50000  # 500.00 USD en cents
PRICE_CURRENCY = "usd"
PRICE_INTERVAL = "month"


def _get_stripe():
    """Configure et retourne le module stripe."""
    stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
    return stripe


def get_or_create_product():
    """Recupere ou cree le produit Nissa sur Stripe."""
    s = _get_stripe()

    # Chercher un produit existant
    products = s.Product.list(limit=10)
    for p in products.data:
        if p.name == "Nissa Maintenance Platform":
            return p

    # Creer le produit
    product = s.Product.create(
        name="Nissa Maintenance Platform",
        description="Abonnement mensuel a la plateforme de maintenance des stations-service Nissa",
    )
    logger.info(f"Produit Stripe cree: {product.id}")
    return product


def get_or_create_price(product_id: str):
    """Recupere ou cree le prix mensuel de 500$/mois."""
    s = _get_stripe()

    # Chercher un prix existant
    prices = s.Price.list(product=product_id, active=True, limit=10)
    for p in prices.data:
        if (p.unit_amount == PRICE_AMOUNT
                and p.currency == PRICE_CURRENCY
                and p.recurring
                and p.recurring.interval == PRICE_INTERVAL):
            return p

    # Creer le prix
    price = s.Price.create(
        product=product_id,
        unit_amount=PRICE_AMOUNT,
        currency=PRICE_CURRENCY,
        recurring={"interval": PRICE_INTERVAL},
    )
    logger.info(f"Prix Stripe cree: {price.id} ({PRICE_AMOUNT/100} {PRICE_CURRENCY}/mois)")
    return price


def create_checkout_session(base_url: str) -> str:
    """Cree une session Stripe Checkout pour l'abonnement.

    Retourne l'URL de paiement.
    """
    s = _get_stripe()
    product = get_or_create_product()
    price = get_or_create_price(product.id)

    session = s.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": price.id, "quantity": 1}],
        success_url=f"{base_url}/admin?tab=abonnement&success=Abonnement+active",
        cancel_url=f"{base_url}/admin?tab=abonnement&error=Paiement+annule",
    )
    return session.url


def create_portal_session(customer_id: str, base_url: str) -> str:
    """Cree une session portail client Stripe pour gerer l'abonnement."""
    s = _get_stripe()
    session = s.billing_portal.Session.create(
        customer=customer_id,
        return_url=f"{base_url}/admin?tab=abonnement",
    )
    return session.url


def get_subscription_status() -> dict:
    """Recupere le statut de l'abonnement actuel."""
    s = _get_stripe()

    # Chercher les abonnements actifs
    subscriptions = s.Subscription.list(limit=5, status="all")

    if not subscriptions.data:
        return {"active": False, "status": "aucun", "subscription": None}

    # Prendre le plus recent
    sub = subscriptions.data[0]

    # Recuperer les infos client
    customer = s.Customer.retrieve(sub.customer)

    return {
        "active": sub.status in ("active", "trialing"),
        "status": sub.status,
        "customer_id": sub.customer,
        "customer_email": customer.email,
        "current_period_start": sub.current_period_start,
        "current_period_end": sub.current_period_end,
        "cancel_at_period_end": sub.cancel_at_period_end,
        "subscription_id": sub.id,
    }


def get_invoices(limit: int = 20) -> list[dict]:
    """Recupere les dernieres factures."""
    s = _get_stripe()

    invoices = s.Invoice.list(limit=limit)

    results = []
    for inv in invoices.data:
        results.append({
            "id": inv.id,
            "number": inv.number,
            "date": inv.created,
            "amount": inv.amount_paid / 100,
            "currency": inv.currency.upper(),
            "status": inv.status,
            "pdf_url": inv.invoice_pdf,
            "hosted_url": inv.hosted_invoice_url,
        })

    return results
