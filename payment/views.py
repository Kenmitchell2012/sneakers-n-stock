from django.shortcuts import render, redirect
from cart.models import Cart
from conversation.models import Conversation
from .forms import ShippingAddressForm, PaymentForm
from payment.models import ShippingAddress
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
# Create your views here.


@login_required
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

def billing_info(request):
    if request.method == 'POST':
        if not request.user.is_authenticated:
            messages.error(request, 'Access denied. You must be logged in.')
            return redirect('core:index')

        # Get or create cart and related data
        cart, _ = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        cart_item_count = sum(item.quantity for item in cart_items)
        total_price = cart.calculate_total_price()

        # Count user's conversations
        conversation_count = Conversation.objects.filter(members__in=[request.user.id]).count()

        # Store shipping address in session (converted to dict)
        shipping_data = request.POST.dict()
        request.session['shipping_address'] = shipping_data
        request.session.modified = True  # explicitly mark session as changed

        # Initialize the billing form
        payment_form = PaymentForm(request.POST)

        # Optional: print debug info
        print("Session shipping_address:", request.session.get('shipping_address'))

        return render(request, 'payment/billing_info.html', {
            'cart': cart,
            'cart_items': cart_items,
            'cart_item_count': cart_item_count,
            'conversation_count': conversation_count,
            'total_price': total_price,
            'shipping_info': shipping_data,
            'billing_form': payment_form,
        })

    else:
        messages.error(request, 'Access denied. Invalid request method.')
        return redirect('core:index')
    
def process_order(request):
    if request.POST:
        # Get the cart item count for the authenticated user
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        cart_item_count = sum(item.quantity for item in cart_items)
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()
        total_price = cart.calculate_total_price()

        # Get shipping info from previous step
        payment_form = PaymentForm(request.POST or None)
        # Get shipping session data
        my_shipping = request.session.get('my_shipping')
        print(request.session.get('shipping_address'))  # Should return a dict       
        messages.success(request, 'Order Placed!')
        return redirect('core:index')






    else:
        messages.success(request, 'Access denied')
        return redirect('core:index')


def payment_success(request):
    return render(request, 'payment/payment_success.html',{})

