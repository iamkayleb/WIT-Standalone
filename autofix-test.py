def calculate_total(
    items, tax_rate, discount_percentage, apply_shipping, shipping_flat_rate, use_express_delivery
):
    subtotal = sum(item["price"] * item["quantity"] for item in items)
    tax = subtotal * tax_rate
    discount = subtotal * discount_percentage
    total = subtotal + tax - discount
    if apply_shipping:
        total += shipping_flat_rate
    return total


def greet(name):
    msg = "Hello, " + name + "!"
    return msg
