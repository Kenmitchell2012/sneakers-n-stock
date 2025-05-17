from django.shortcuts import render, redirect, get_object_or_404
from cart.models import Cart
from conversation.models import Conversation
from .forms import ShippingAddressForm, PaymentForm
from payment.models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required

from items.models import Items
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce
# Create your views here.

@login_required
def user_orders(request):
    orders = Order.objects.filter(user=request.user).order_by('-date_ordered')
    return render(request, 'payment/user_orders.html', {'orders': orders})

@login_required
def user_order_detail(request, order_id):
    order = get_object_or_404(Order, id=order_id, user=request.user)
    return render(request, 'payment/user_order_detail.html', {'order': order})


# Create a view for the admin dashboard
def admin_dashboard(request):
    if request.user.is_authenticated and request.user.is_superuser:
        # Get all orders
        orders = Order.objects.all()
        order_items = OrderItem.objects.all()
        # Get all items in the order
        items = []
        for item in order_items:
            item.total_price = item.price * item.quantity
        for order in orders:
            order_items = OrderItem.objects.filter(order=order)
            for order_item in order_items:
                items.append(order_item.item)

        # get total revenue of orders sold
        total_revenue = Order.objects.aggregate(Sum('amount_paid'))['amount_paid__sum']
        # get total number of orders
        total_orders = Order.objects.count()
        

        return render(request, 'payment/admin_dashboard.html', {'orders': orders, 'order_items': order_items, 'items': items , 'total_revenue': total_revenue, 'total_orders': total_orders})
    else:
 
        messages.error(request, 'Access denied. You must be logged in as an admin.')
        return redirect('core:index')

def order_detail(request, order_id):
    if request.user.is_authenticated and request.user.is_superuser:
        order = get_object_or_404(Order, id=order_id)
        order_items = OrderItem.objects.filter(order=order)
        items = [item.item for item in order_items]
        order_items = OrderItem.objects.filter(order=order)
        items_total = sum(item.price * item.quantity for item in order_items)

        if request.method == 'POST':
            status = request.POST['shipping_status']
            order.shipped = True if status == 'true' else False
            order.save()
            messages.success(request, 'Shipping status updated')
            return redirect('payment:order_detail', order_id=order_id)

        return render(request, 'payment/order_detail.html', {
            'order': order,
            'order_items': order_items,
            'items': items,
            'items_total': items_total,
        })
    else:
        messages.error(request, 'Access denied. You must be logged in as an admin.')
        return redirect('core:index')


# Create a view for the shipped dashboard
def shipped_dashboard(request):
    if request.user.is_authenticated and request.user.is_superuser:
        orders = Order.objects.filter(shipped=True)
        order_items = OrderItem.objects.all()
        # Get all items in the order
        items = []
        for order in orders:
            order_items = OrderItem.objects.filter(order=order)
            for order_item in order_items:
                items.append(order_item.item)
        return render(request, 'payment/shipped_dashboard.html', {'orders': orders, 'order_items': order_items, 'items': items})
    else:
        messages.error(request, 'Access denied. You must be logged in as an admin.')
        return redirect('core:index')

# Create a view for the not shipped dashboard
def not_shipped_dashboard(request):
    if request.user.is_authenticated and request.user.is_superuser:
        # Get all orders that are not shipped
        orders = Order.objects.filter(shipped=False)
        order_items = OrderItem.objects.all()
        # Get all items in the order
        items = []
        for order in orders:
            order_items = OrderItem.objects.filter(order=order)
            for order_item in order_items:
                items.append(order_item.item)
        return render(request, 'payment/not_shipped_dashboard.html', {'orders': orders, 'order_items': order_items})
    else:
        messages.error(request, 'Access denied. You must be logged in as an admin.')
        return redirect('core:index')

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
        # Get the cart and its items
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        cart_item_count = sum(item.quantity for item in cart_items)
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()
        total_price = cart.calculate_total_price()

        # Shipping info from session
        my_shipping = request.session.get('shipping_address')
        if my_shipping is None:
            messages.error(request, 'Shipping information is missing.')
            return redirect('core:index')

        full_name = my_shipping.get('shipping_full_name')
        email = my_shipping.get('shipping_email')
        shipping_address = f"{my_shipping['shipping_full_name']}\n{my_shipping['shipping_email']}\n{my_shipping['shipping_address']}\n{my_shipping['shipping_city']}\n{my_shipping['shipping_state']}\n{my_shipping['shipping_zip_code']}\n{my_shipping['shipping_country']}\n{my_shipping['shipping_phone_number']}"
        amount_paid = total_price

        # Create order
        create_order = Order(
            user=request.user if request.user.is_authenticated else None,
            full_name=full_name,
            email=email,
            shipping_address=shipping_address,
            amount_paid=amount_paid
        )
        create_order.save()

        # Create order items and update stock
        for item in cart_items:
            item_id = item.item.id
            item_price = item.item.price
            item_quantity = item.quantity

            order_item = OrderItem(
                order=create_order,
                item=item.item,
                user=request.user if request.user.is_authenticated else None,
                quantity=item_quantity,
                price=item_price
            )
            order_item.save()

            # Update stock
            item_instance = item.item
            if item_instance.quantity >= item_quantity:
                item_instance.quantity -= item_quantity
            else:
                item_instance.quantity = 0  # Prevent negative stock
            item_instance.save()

        # Clear cart
        cart.items.all().delete()

        messages.success(request, 'Order Placed!')
        return redirect('core:index')
    else:
        messages.error(request, 'Access denied')
        return redirect('core:index')


def payment_success(request):
    return render(request, 'payment/payment_success.html',{})

