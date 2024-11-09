from django.shortcuts import render, redirect
from cart.models import Cart
from conversation.models import Conversation
from .forms import ShippingAddressForm
from payment.models import ShippingAddress
from django.contrib.auth.models import User
# Create your views here.



def checkout(request):
    # Get the cart item count for the authenticated user
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()
    total_price = cart.calculate_total_price()

    current_user = request.user
    shipping_user, created = ShippingAddress.objects.get_or_create(user=current_user)

    if request.method == 'POST':
        shipping_form = ShippingAddressForm(request.POST, instance=shipping_user)
        if shipping_form.is_valid():
            shipping_address = shipping_form.save(commit=False)
            shipping_address.user = current_user
            shipping_address.save()
            return redirect('payment:checkout')
    else:
        shipping_form = ShippingAddressForm(instance=shipping_user)

    return render(request, 'payment/checkout.html', {
        'cart': cart, 
        'conversation_count': conversation_count, 
        'total_price': total_price, 
        'cart_item_count': cart_item_count,
        'cart_items': cart_items,
        'shipping_form': shipping_form
    })



def payment_success(request):
    return render(request, 'payment/payment_success.html',{})