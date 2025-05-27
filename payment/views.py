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

from django.db import transaction, IntegrityError
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

import logging
logger = logging.getLogger(__name__)


def process_order(request):
    if request.method == 'POST': # Use request.method == 'POST' for clarity
        # Get the cart and its items
        cart = get_object_or_404(Cart, user=request.user) # Assume cart exists if POSTing from checkout
        cart_items = cart.items.all()
        
        if not cart_items.exists(): # Ensure cart is not empty
            messages.error(request, 'Your cart is empty.')
            return redirect('cart:view_cart')

        total_price = sum(ci.quantity * ci.item.price for ci in cart_items)

        # Shipping info from session
        my_shipping = request.session.get('shipping_address')
        if my_shipping is None:
            messages.error(request, 'Shipping information is missing. Please re-enter your shipping details.')
            return redirect('core:index') # Redirect to a page where shipping can be re-entered, e.g., checkout

        full_name = my_shipping.get('shipping_full_name', '')
        email = my_shipping.get('shipping_email', '')
        # Construct shipping address robustly, handling missing fields
        shipping_address_parts = [
            my_shipping.get('shipping_full_name'),
            my_shipping.get('shipping_email'),
            my_shipping.get('shipping_address'),
            my_shipping.get('shipping_city'),
            my_shipping.get('shipping_state'),
            my_shipping.get('shipping_zip_code'),
            my_shipping.get('shipping_country'),
            my_shipping.get('shipping_phone_number')
        ]
        # Filter out None values and join with newline
        shipping_address = "\n".join(filter(None, shipping_address_parts))
        
        amount_paid = total_price # Assuming payment processed and matched total_price

        # Use a transaction for the entire order creation process
        # This ensures that either the order and all its items are created AND stock is updated,
        # OR everything is rolled back if any step (like stock check) fails.
        try:
            with transaction.atomic():
                # Create order
                create_order = Order(
                    user=request.user if request.user.is_authenticated else None,
                    full_name=full_name,
                    email=email,
                    shipping_address=shipping_address,
                    amount_paid=amount_paid # Assuming this comes from successful payment
                )
                create_order.save()

                items_out_of_stock = [] # To collect items that couldn't be fulfilled

                # Process each item in the cart to create order items and update stock
                for cart_item in cart_items:
                    size_variant = cart_item.size_variant
                    item_quantity = cart_item.quantity

                    # --- FINAL STOCK VALIDATION AND DECREMENT ---
                    if size_variant: # Should always be true if cart item is valid
                        # Check if enough stock is available AT THIS VERY MOMENT
                        if size_variant.quantity >= item_quantity:
                            # Decrement stock
                            size_variant.quantity -= item_quantity
                            size_variant.save(update_fields=['quantity']) # This will also update Item.quantity
                            
                            # Create OrderItem
                            order_item = OrderItem(
                                order=create_order,
                                item=cart_item.item, # Use cart_item.item for the Items instance
                                size_variant=size_variant, # Link to the specific SizeVariant
                                user=request.user if request.user.is_authenticated else None,
                                quantity=item_quantity,
                                price=cart_item.item.price # Use actual price from Item
                            )
                            order_item.save()
                        else:
                            # Item is out of stock or not enough quantity for this size variant
                            items_out_of_stock.append(f"{cart_item.item.name} (Size {size_variant.size}, requested {item_quantity}, available {size_variant.quantity})")
                            # Optionally: remove this specific item from cart so user can re-order less
                            cart_item.delete() 
                    else:
                        # Should not happen if data is clean, but handles missing size_variant
                        items_out_of_stock.append(f"{cart_item.item.name} (Error: Size variant missing)")
                        cart_item.delete() # Remove problematic item from cart

                if items_out_of_stock:
                    # If any items were out of stock, roll back the entire order or notify user
                    # Option A: Rollback entire order and notify user (Recommended for simplicity)
                    transaction.set_rollback(True) # Force rollback of the transaction
                    messages.error(request, f"Order could not be placed fully. Some items were out of stock: {'; '.join(items_out_out_stock)}. Please review your cart.")
                    logger.warning(f"Order failed for user {request.user.username} due to out of stock items: {items_out_out_stock}")
                    return redirect('cart:view_cart') # Redirect to cart to show updated state

                    # Option B: (More complex) Create partial order and notify.
                    # This would involve more sophisticated logic and partial order status.
                    # For now, rolling back is safer.
                
                # If all items were in stock and order created successfully, clear the cart
                cart.items.all().delete()
                
                messages.success(request, 'Order Placed Successfully!')
                return redirect('core:index') # Redirect to a thank you page or order confirmation page
        
        except IntegrityError as e:
            logger.error(f"IntegrityError during order processing for user {request.user.username}: {e}")
            messages.error(request, 'A database error occurred during order processing. Please try again.')
            return redirect('cart:view_cart')
        except Exception as e:
            logger.error(f"Unexpected error during order processing for user {request.user.username}: {e}")
            messages.error(request, 'An unexpected error occurred while placing your order. Please try again.')
            return redirect('cart:view_cart')
    else:
        messages.error(request, 'Invalid request method. Access denied.')
        return redirect('core:index')


def payment_success(request):
    return render(request, 'payment/payment_success.html',{})

