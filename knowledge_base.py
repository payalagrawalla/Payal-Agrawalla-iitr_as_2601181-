"""Nykaa knowledge base documents."""

KNOWLEDGE_BASE = [
    {
        "doc_id": "doc_01",
        "topic": "return window by product category",
        "text": (
            "Apparel items can be returned within 15 days of delivery if they are unworn and carry the original tags. "
            "Electronics and beauty appliances have a 7-day return window because these products are more likely to be used quickly. "
            "Home and footwear products generally qualify for a 10-day return window, provided they are unused and still in original packaging."
        ),
    },
    {
        "doc_id": "doc_02",
        "topic": "COD refund timelines",
        "text": (
            "Cash-on-delivery orders are refunded back to the customer within 5 to 7 business days after the return is accepted. "
            "The exact timeline depends on the bank and the payment processor, so customers should allow up to one week for the amount to reflect. "
            "Any failed refund after this period should be escalated to the finance support desk for verification."
        ),
    },
    {
        "doc_id": "doc_03",
        "topic": "delivery SLAs",
        "text": (
            "Standard metro deliveries are fulfilled within 3 to 5 business days for in-stock items. "
            "Non-metro delivery windows extend to 5 to 7 business days depending on the pin code and courier load. "
            "If a shipment is delayed beyond the promised SLA, customers can request a review and a redelivery update from the shipping desk."
        ),
    },
    {
        "doc_id": "doc_04",
        "topic": "reverse-pickup eligibility",
        "text": (
            "Reverse pickup is available for eligible items that are in a saleable or unopened condition at the time of return. "
            "Customers located in serviceable pin codes can request a doorstep collection if the product is not oversized or hazardous. "
            "For bulky orders, international shipments, or damaged items, self-shipment or a store drop is recommended instead."
        ),
    },
    {
        "doc_id": "doc_05",
        "topic": "warranty terms by category",
        "text": (
            "Electronics typically have a 12-month warranty from the date of delivery for manufacturing defects. "
            "Beauty tools and appliances usually come with a 6-month warranty, while apparel has no formal manufacturer warranty. "
            "Any warranty claim requires the original invoice and evidence of a defect, not normal wear and tear."
        ),
    },
    {
        "doc_id": "doc_06",
        "topic": "order-cancellation policy",
        "text": (
            "Orders can be canceled only while they remain in the Placed or Packed state. "
            "Once a shipment is marked Shipped, the cancellation request is no longer accepted by default. "
            "If the order is already in transit, customers may be advised to reject the package at delivery or initiate a return after receipt."
        ),
    },
    {
        "doc_id": "doc_07",
        "topic": "loyalty-points redemption policy",
        "text": (
            "Nykaa loyalty points can be redeemed only on eligible products and cannot be combined with a coupon on the same item in most cases. "
            "Redemption is generally available at checkout when the customer has a minimum balance threshold for the order value. "
            "Points are not transferable between accounts and expire after a fixed inactivity period, which is communicated in the wallet section."
        ),
    },
    {
        "doc_id": "doc_08",
        "topic": "payment-failure/retry policy",
        "text": (
            "If a payment attempt fails, the system automatically releases the authorization and initiates a retry link for the customer. "
            "No additional charge is created unless the retry is successful, and any failed transaction is generally settled in 3 to 5 business days. "
            "Customers are encouraged to avoid repeated retries on the same card if the bank has already declined the authorization."
        ),
    },
    {
        "doc_id": "doc_09",
        "topic": "size-exchange policy",
        "text": (
            "Size exchanges are permitted when the product is unused, unwashed, and within the same category and item type. "
            "It is not a full refund; the exchange uses a size replacement on the original product value, subject to stock availability. "
            "Any size exchange request must be raised within the standard return window for that category."
        ),
    },
    {
        "doc_id": "doc_10",
        "topic": "damaged-item claim process",
        "text": (
            "Customers reporting a damaged item must share clear photographs of the packaging and the product defect within 48 hours of delivery. "
            "The claim is reviewed against the invoice and the courier condition report before a replacement or refund is approved. "
            "If the damage is severe or the item is unsafe to use, the customer should stop using it and escalate the issue immediately."
        ),
    },
    {
        "doc_id": "doc_11",
        "topic": "international shipping restrictions",
        "text": (
            "International shipping is restricted for certain beauty items, liquids, and restricted categories due to customs and airline safety rules. "
            "Some destinations may require a customs declaration and additional duties before delivery can complete. "
            "Orders to unsupported countries are blocked before checkout and are not eligible for fulfillment."
        ),
    },
    {
        "doc_id": "doc_12",
        "topic": "customer-support escalation matrix",
        "text": (
            "The first line of support handles standard order, return, and delivery questions. "
            "Escalation is recommended when the case concerns a repeated payment failure, a damaged claim dispute, or a delayed shipment with a high risk score. "
            "Senior support and finance review the case if the issue remains unresolved, and a manager can finalise exceptions or refunds."
        ),
    },
]


def get_knowledge_base() -> list[dict]:
    return [document.copy() for document in KNOWLEDGE_BASE]
