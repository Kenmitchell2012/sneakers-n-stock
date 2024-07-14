from django import template

register = template.Library()

@register.filter(name='calculate_cart_total')
def calculate_cart_total(cart):
    total = sum(item.item.price * item.quantity for item in cart.items.all())
    return total