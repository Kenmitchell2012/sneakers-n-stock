from django.shortcuts import render, redirect, get_object_or_404
from cart.models import Cart, CartItem
from conversation.models import Conversation
from .forms import ShippingAddressForm, PaymentForm
from payment.models import ShippingAddress, Order, OrderItem
from django.contrib.auth.models import User
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt

from items.models import Items
from django.db.models import Sum, DecimalField
from django.db.models.functions import Coalesce

from django.db import transaction, IntegrityError

import stripe
import json
from django.conf import settings
from django.urls import reverse
from django.views.decorators.http import require_POST
import logging
# Initialize Stripe with your secret key
stripe.api_key = settings.STRIPE_SECRET_KEY
# Create your views here.

logger = logging.getLogger(__name__)

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
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty and cannot proceed to checkout.')
        return redirect('cart:view_cart')

    total_price = sum(ci.quantity * ci.item.price for ci in cart_items)
    cart_item_count = sum(item.quantity for item in cart_items)

    current_user = request.user
    shipping_user, created_shipping_address = ShippingAddress.objects.get_or_create(user=current_user)

    if request.method == 'POST':
        print(f"\n--- Checkout POST Debug Start ---")
        shipping_form = ShippingAddressForm(request.POST, instance=shipping_user) 
        
        if shipping_form.is_valid():
            print(f"DEBUG: Shipping form is valid.")
            shipping_address_instance = shipping_form.save(commit=False)
            shipping_address_instance.user = current_user
            shipping_address_instance.save() 
            print(f"DEBUG: Shipping address saved to DB.")

            # --- Call the internal Stripe session creation function ---
            print(f"DEBUG: Calling _create_stripe_checkout_session_internal...")
            checkout_session, response_redirect = _create_stripe_checkout_session_internal(request, cart, shipping_form.cleaned_data)
            print(f"DEBUG: _create_stripe_checkout_session_internal returned checkout_session: {checkout_session}, response_redirect: {response_redirect}")
            
            if response_redirect: 
                print(f"DEBUG: Redirecting based on response_redirect: {response_redirect.url}")
                return response_redirect 
            elif checkout_session: 
                print(f"DEBUG: Successfully created checkout_session: {checkout_session.id}. Preparing redirect to Stripe.")
                request.session['stripe_checkout_session_id'] = checkout_session.id
                print(f"DEBUG: Stored session ID in Django session. Redirecting to Stripe URL: {checkout_session.url}")
                return redirect(checkout_session.url, code=303) 
            else: 
                print(f"DEBUG: _create_stripe_checkout_session_internal returned None for both. Falling back to cart view.")
                messages.error(request, "Failed to initiate payment. Please try again.")
                return redirect('cart:view_cart')

        else: # Form is not valid for POST request
            print(f"DEBUG: Shipping form is NOT valid. Errors: {shipping_form.errors.as_json()}")
            messages.error(request, 'Please correct the errors in the shipping information.')
            # Fall through to render the page with shipping_form containing errors
        print(f"--- Checkout POST Debug End (Form Invalid/Fallthrough) ---")
    else: # GET request for initial page load
        # ... (existing GET request logic) ...
        print(f"--- Checkout GET Debug Start ---")
        shipping_form = ShippingAddressForm(instance=shipping_user)
        print(f"--- Checkout GET Debug End ---")

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'cart_item_count': cart_item_count,
        'shipping_form': shipping_form, 
    }
    print(f"--- Rendering Checkout Page ---")
    return render(request, 'payment/checkout.html', context)

# --- INTERNAL HELPER FUNCTION: create_stripe_checkout_session ---
# This function is now called internally by the checkout view after shipping is saved.
def _create_stripe_checkout_session_internal(request, cart, shipping_info):
    """
    Internal helper to create a Stripe Checkout Session.
    Assumes cart and shipping_info are already validated.
    """
    line_items = []
    for cart_item in cart.items.all():
        unit_amount = int(cart_item.item.price * 100) 

        # Final stock validation before sending to Stripe Checkout
        if cart_item.quantity > cart_item.size_variant.quantity:
            messages.error(request, f"One or more items in your cart are now out of stock: {cart_item.item.name} (Size {cart_item.size_variant.size}). Please adjust your cart.")
            return None, redirect('cart:view_cart') # Return None for session, and a redirect response

        line_items.append({
            'price_data': {
                'currency': 'usd', 
                'product_data': {
                    'name': f"{cart_item.item.name} (Size: {cart_item.size_variant.size})",
                    'images': [request.build_absolute_uri(cart_item.item.images.first().image.url)] if cart_item.item.images.exists() and cart_item.item.images.first().image else [],
                },
                'unit_amount': unit_amount,
            },
            'quantity': cart_item.quantity,
        })
    
    success_url = request.build_absolute_uri(settings.STRIPE_SUCCESS_URL)
    cancel_url = request.build_absolute_uri(settings.STRIPE_CANCEL_URL)

    metadata = {
        'user_id': request.user.id,
        'cart_id': cart.id,
        'shipping_full_name': shipping_info.get('shipping_full_name', ''),
        'shipping_email': shipping_info.get('shipping_email', request.user.email if request.user.is_authenticated else ''),
        'shipping_address_line1': shipping_info.get('shipping_address', ''),
        'shipping_city': shipping_info.get('shipping_city', ''),
        'shipping_state': shipping_info.get('shipping_state', ''),
        'shipping_zip_code': shipping_info.get('shipping_zip_code', ''),
        'shipping_country': shipping_info.get('shipping_country', ''),
        'shipping_phone_number': shipping_info.get('shipping_phone_number', ''),
    }

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=line_items,
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=request.user.email if request.user.is_authenticated else None,
            client_reference_id=request.user.id if request.user.is_authenticated else None,
            metadata=metadata, 
            shipping_address_collection={
                'allowed_countries': ['US', 'CA', 'GB', 'AU'], # Customize
            },
        )
        return checkout_session, None # Return session object and None for redirect
    except stripe.error.StripeError as e:
        logger.error(f"Error creating Stripe Checkout Session for user {request.user.id}, cart {cart.id}: {e}")
        messages.error(request, f"A problem occurred with payment: {e}. Please try again.")
        return None, redirect('cart:view_cart') # Return None for session, and a redirect response
    except Exception as e:
        logger.error(f"Unexpected error in _create_stripe_checkout_session_internal for user {request.user.id}, cart {cart.id}: {e}", exc_info=True)
        messages.error(request, "An unexpected error occurred. Please try again.")
        return None, redirect('cart:view_cart')

# --- END INTERNAL HELPER FUNCTION ---

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
    
# webhook endpoint
@csrf_exempt 
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META['HTTP_STRIPE_SIGNATURE']
    event = None # Initialized to None

    try:
        # Verify webhook signature
        # This is a critical security step to ensure the request is from Stripe
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        # Invalid payload (e.g., not valid JSON)
        logger.error(f"Webhook Error: Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        logger.error(f"Webhook Error: Invalid signature: {e}")
        return HttpResponse(status=400)
    except Exception as e: # Catch any other general exceptions during construct_event
        logger.error(f"Webhook Error: Unhandled exception during event construction: {e}")
        return HttpResponse(status=400)

    # --- ADD THIS CRUCIAL CHECK ---
    # If event somehow became None (which shouldn't happen with proper construct_event, but defensive)
    if event is None:
        logger.error("Webhook Error: 'event' object is None after construction. Payload might be malformed or unhandled.")
        return HttpResponse(status=400) # Bad Request
    # --- END ADD THIS CRUCIAL CHECK ---


    # access event['type']
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        
        user_id = session.metadata.get('user_id')
        cart_id = session.metadata.get('cart_id')
        amount_total = session['amount_total'] / 100 

        logger.info(f"Checkout Session Completed event received for user {user_id}, cart {cart_id}, total {amount_total}")

        try:
            with transaction.atomic():
                user = User.objects.get(id=user_id)
                cart = Cart.objects.get(id=cart_id) # Ensure this is 'id=cart_id'
                cart_items = cart.items.all()

                if Order.objects.filter(payment_intent_id=session.payment_intent).exists(): 
                    logger.info(f"Order for payment_intent_id {session.payment_intent} already exists. Skipping duplicate fulfillment.")
                    return HttpResponse(status=200)

                # ... (rest of webhook logic for shipping address retrieval, Order creation, OrderItem creation, stock decrement, cart clear) ...
                shipping_full_name = session.metadata.get('shipping_full_name', 'N/A')
                shipping_email = session.metadata.get('shipping_email', session.customer_details.get('email', 'N/A'))
                
                shipping_address_parts = []
                if session.metadata.get('shipping_address_line1'): shipping_address_parts.append(session.metadata.get('shipping_address_line1'))
                if session.metadata.get('shipping_address_line2'): shipping_address_parts.append(session.metadata.get('shipping_address_line2'))
                if session.metadata.get('shipping_city'): shipping_address_parts.append(session.metadata.get('shipping_city'))
                if session.metadata.get('shipping_state'): shipping_address_parts.append(session.metadata.get('shipping_state'))
                if session.metadata.get('shipping_zip_code'): shipping_address_parts.append(session.metadata.get('shipping_zip_code'))
                if session.metadata.get('shipping_country'): shipping_address_parts.append(session.metadata.get('shipping_country'))
                if session.metadata.get('shipping_phone_number'): shipping_address_parts.append(f"Phone: {session.metadata.get('shipping_phone_number')}")

                if not shipping_address_parts and session.shipping_details and session.shipping_details.address:
                    address = session.shipping_details.address
                    if session.shipping_details.name:
                        shipping_full_name = session.shipping_details.name
                    if address.line1: shipping_address_parts.append(address.line1)
                    if address.line2: shipping_address_parts.append(address.line2)
                    if address.city: shipping_address_parts.append(address.city)
                    if address.state: shipping_address_parts.append(address.state)
                    if address.postal_code: shipping_address_parts.append(address.postal_code)
                    if address.country: shipping_address_parts.append(address.country)
                
                shipping_address_str = "\n".join(filter(None, shipping_address_parts)) or "No shipping address provided."


                create_order = Order(
                    user=user,
                    full_name=shipping_full_name,
                    email=shipping_email,
                    shipping_address=shipping_address_str, 
                    amount_paid=amount_total,
                    payment_intent_id=session.payment_intent, 
                    stripe_checkout_session_id=session.id 
                )
                create_order.save()

                for cart_item in cart_items: 
                    size_variant = cart_item.size_variant
                    item_quantity = cart_item.quantity

                    if size_variant: 
                        if size_variant.quantity >= item_quantity:
                            size_variant.quantity -= item_quantity
                            size_variant.save(update_fields=['quantity']) 
                            
                            order_item = OrderItem(
                                order=create_order,
                                item=cart_item.item, 
                                size_variant=size_variant, 
                                user=user, 
                                quantity=item_quantity,
                                price=cart_item.item.price 
                            )
                            order_item.save()
                        else:
                            logger.error(f"Overselling detected! Item {cart_item.item.name} (Size {size_variant.size}) out of stock during webhook fulfillment. Order {create_order.id}, Cart {cart.id}")
                            pass 
                    else:
                        logger.warning(f"CartItem ID {cart_item.id} has no associated SizeVariant during webhook fulfillment. Item not added to order.")

                cart.items.all().delete()
                
                logger.info(f"Order {create_order.id} for user {user.username} fulfilled successfully via webhook.")
                return HttpResponse(status=200) 
        
        except Exception as e: 
            logger.error(f"Error during webhook order processing for user {user_id}, cart {cart_id}: {e}", exc_info=True) 
            return HttpResponse(status=500) 

    else:
        logger.warning(f"Unhandled webhook event type: {event['type']}")
        return HttpResponse(status=200)



# --- Placeholder Success and Cancel Views  ---
def payment_success(request):
    """
    Page displayed to user after successful payment redirect from Stripe.
    Note: Order fulfillment happens via webhook, not here.
    """
    messages.success(request, "Payment successful! Your order has been placed.")
    return render(request, 'payment/success.html') # Create this template

def payment_cancel(request):
    """
    Page displayed to user if payment is canceled or fails on Stripe.
    """
    messages.error(request, "Payment canceled or failed. Please try again.")
    return render(request, 'payment/cancel.html') # Create this template

# --- End Placeholder Views ---

@require_POST # Ensure this view only accepts POST requests
def create_checkout_session(request):
    """
    Creates a Stripe Checkout Session based on the user's current cart.
    Passes shipping details from the session as metadata.
    """
    if not request.user.is_authenticated:
        messages.error(request, "You must be logged in to proceed to checkout.")
        return redirect('core:login') # Redirect to login if not authenticated

    cart = get_object_or_404(Cart, user=request.user)
    cart_items = cart.items.all()

    if not cart_items.exists():
        messages.error(request, 'Your cart is empty and cannot proceed to checkout.')
        return redirect('cart:view_cart')

    line_items = []
    for cart_item in cart_items:
        # Stripe expects prices in cents (or smallest currency unit)
        # item.price is a FloatField, ensure it's converted correctly
        unit_amount = int(cart_item.item.price * 100) 

        # Final stock validation before sending to Stripe Checkout
        # This prevents over-selling if stock dwindled since cart was populated
        if cart_item.quantity > cart_item.size_variant.quantity:
            messages.error(request, f"One or more items in your cart are now out of stock: {cart_item.item.name} (Size {cart_item.size_variant.size}). Please adjust your cart.")
            return redirect('cart:view_cart')

        line_items.append({
            'price_data': {
                'currency': 'usd', # Set your currency
                'product_data': {
                    'name': f"{cart_item.item.name} (Size: {cart_item.size_variant.size})",
                    # Optional: Add images if your products have public URLs accessible by Stripe
                    'images': [request.build_absolute_uri(cart_item.item.images.first().image.url)] if cart_item.item.images.exists() and cart_item.item.images.first().image else [],
                },
                'unit_amount': unit_amount,
            },
            'quantity': cart_item.quantity,
        })
    
    # Define success and cancel URLs
    # Use request.build_absolute_uri to ensure full URL for Stripe
    success_url = request.build_absolute_uri(settings.STRIPE_SUCCESS_URL)
    cancel_url = request.build_absolute_uri(settings.STRIPE_CANCEL_URL)

    # --- Retrieve shipping info from session and pass to Stripe metadata ---
    # This ensures shipping data is available in the webhook event
    shipping_info = request.session.get('shipping_address', {})
    metadata = {
        'user_id': request.user.id,
        'cart_id': cart.id,
        'shipping_full_name': shipping_info.get('shipping_full_name', ''),
        'shipping_email': shipping_info.get('shipping_email', request.user.email if request.user.is_authenticated else ''),
        'shipping_address_line1': shipping_info.get('shipping_address', ''), # Your form's address field
        'shipping_city': shipping_info.get('shipping_city', ''),
        'shipping_state': shipping_info.get('shipping_state', ''),
        'shipping_zip_code': shipping_info.get('shipping_zip_code', ''),
        'shipping_country': shipping_info.get('shipping_country', ''),
        'shipping_phone_number': shipping_info.get('shipping_phone_number', ''),
        # Add any other shipping fields you collect that are simple key-value pairs
    }
    # --- END NEW: METADATA FOR SHIPPING ---

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=line_items,
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=request.user.email if request.user.is_authenticated else None, # Pre-fill customer email
            client_reference_id=request.user.id if request.user.is_authenticated else None, # Link session to your user ID
            metadata=metadata, # Pass all your collected metadata here
            # --- ADD THIS PARAMETER TO COLLECT SHIPPING ADDRESSES ON STRIPE CHECKOUT PAGE ---
            shipping_address_collection={
                'allowed_countries': ['US', 'CA', 'GB', 'AU'], # Customize with countries you ship to
            },
            # --- END ADD PARAMETER ---
        )
        return redirect(checkout_session.url, code=303) # Redirect to Stripe Checkout
    except stripe.error.StripeError as e:
        logger.error(f"Error creating Stripe Checkout Session for user {request.user.id}, cart {cart.id}: {e}")
        messages.error(request, f"A problem occurred with payment: {e}. Please try again.")
        return redirect('cart:view_cart')
    except Exception as e:
        logger.error(f"Unexpected error in create_checkout_session for user {request.user.id}, cart {cart.id}: {e}", exc_info=True) # Log traceback
        messages.error(request, "An unexpected error occurred. Please try again.")
        return redirect('cart:view_cart')
