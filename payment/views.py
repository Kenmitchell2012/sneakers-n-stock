from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.conf import settings
from django.urls import reverse
from django.views.decorators.http import require_POST
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse
from django.contrib.auth.models import User
from django.db import transaction, IntegrityError
from django.db.models import Sum
from django.contrib.auth.decorators import login_required

import stripe
import json
import logging

from items.models import Items, SizeVariant
from cart.models import Cart, CartItem
from payment.models import Order, OrderItem, ShippingAddress
from .forms import ShippingAddressForm, PaymentForm # Assuming these are in payment.forms

logger = logging.getLogger(__name__)

stripe.api_key = settings.STRIPE_SECRET_KEY

# --- Internal Helper Functions ---

def _create_stripe_checkout_session_internal(request, cart, shipping_info_cleaned_data):
    """
    Creates a Stripe Checkout Session.
    Validates item stock before session creation.
    """
    line_items = []
    for cart_item in cart.items.all():
        unit_amount = int(cart_item.item.price * 100)

        # Final stock validation to prevent overselling
        if cart_item.quantity > cart_item.size_variant.quantity:
            messages.error(request, f"One or more items in your cart are now out of stock: {cart_item.item.name} (Size {cart_item.size_variant.size}). Please adjust your cart.")
            return None, redirect('cart:view_cart')

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
        # CORRECTED MAPPING: Use the actual field names from your ShippingAddress model/form
        'shipping_full_name': shipping_info_cleaned_data.get('shipping_full_name', ''),
        'shipping_email': shipping_info_cleaned_data.get('shipping_email', request.user.email if request.user.is_authenticated else ''),
        'shipping_address_line1': shipping_info_cleaned_data.get('shipping_address', ''), # This maps to your model's 'shipping_address'
        'shipping_city': shipping_info_cleaned_data.get('shipping_city', ''),
        'shipping_state': shipping_info_cleaned_data.get('shipping_state', ''),
        'shipping_zip_code': shipping_info_cleaned_data.get('shipping_zip_code', ''),
        'shipping_country': shipping_info_cleaned_data.get('shipping_country', ''),
        'shipping_phone_number': shipping_info_cleaned_data.get('shipping_phone_number', ''),
    }

    # Your debug logging will now show the correct data if the form populated it
    logger.info(f"DEBUG: Metadata being sent to Stripe: {metadata}")
    logger.info(f"DEBUG: Line items being sent to Stripe: {line_items}")
    logger.info(f"DEBUG: Success URL: {success_url}, Cancel URL: {cancel_url}")

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
                'allowed_countries': ['US', 'CA', 'GB', 'AU'],
            },
        )
        return checkout_session, None
    except stripe.error.StripeError as e:
        logger.error(f"Error creating Stripe Checkout Session for user {request.user.id}, cart {cart.id}: {e}")
        messages.error(request, f"A problem occurred with payment: {e}. Please try again.")
        return None, redirect('cart:view_cart')
    except Exception as e:
        logger.error(f"Unexpected error in _create_stripe_checkout_session_internal for user {request.user.id}, cart {cart.id}: {e}", exc_info=True)
        messages.error(request, "An unexpected error occurred. Please try again.")
        return None, redirect('cart:view_cart')

# --- Checkout View ---

@login_required
def checkout(request):
    """
    Handles the checkout process, including displaying the cart,
    shipping address form, and initiating the Stripe Checkout session.
    """
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
        shipping_form = ShippingAddressForm(request.POST, instance=shipping_user)

        if shipping_form.is_valid():
            shipping_address_instance = shipping_form.save(commit=False)
            shipping_address_instance.user = current_user
            shipping_address_instance.save()

            checkout_session, response_redirect = _create_stripe_checkout_session_internal(request, cart, shipping_form.cleaned_data)

            if response_redirect:
                return response_redirect
            elif checkout_session:
                request.session['stripe_checkout_session_id'] = checkout_session.id
                return redirect(checkout_session.url, code=303)
            else:
                messages.error(request, "Failed to initiate payment. Please try again.")
                return redirect('cart:view_cart')
        else:
            messages.error(request, 'Please correct the errors in the shipping information.')
    else:
        shipping_form = ShippingAddressForm(instance=shipping_user)

    context = {
        'cart_items': cart_items,
        'total_price': total_price,
        'cart_item_count': cart_item_count,
        'shipping_form': shipping_form,
    }
    return render(request, 'payment/checkout.html', context)

# --- Stripe Webhook Endpoint ---

# payment/views.py (within your existing file)

# ... (imports and other views remain the same) ...

@csrf_exempt
def stripe_webhook(request):
    payload = request.body
    sig_header = request.META.get('HTTP_STRIPE_SIGNATURE')
    event = None

    if not sig_header:
        logger.error("Webhook Error: Missing Stripe signature header.")
        return HttpResponse(status=400)

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, settings.STRIPE_WEBHOOK_SECRET
        )
    except ValueError as e:
        logger.error(f"Webhook Error: Invalid payload: {e}")
        return HttpResponse(status=400)
    except stripe.error.SignatureVerificationError as e:
        logger.error(f"Webhook Error: Invalid signature: {e}")
        return HttpResponse(status=400)
    except Exception as e:
        logger.error(f"Webhook Error: Unhandled exception during event construction: {e}")
        return HttpResponse(status=400)

    if event is None:
        logger.error("'event' object is None after construction. Payload might be malformed or unhandled.")
        return HttpResponse(status=400)

    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        user_id = session.metadata.get('user_id')
        cart_id = session.metadata.get('cart_id')
        amount_total = session['amount_total'] / 100

        logger.info(f"Checkout Session Completed event received for user {user_id}, cart {cart_id}, total {amount_total}")

        try:
            with transaction.atomic():
                user = User.objects.get(id=user_id)
                cart = Cart.objects.get(id=cart_id)
                cart_items = cart.items.all()

                if Order.objects.filter(payment_intent_id=session.payment_intent).exists():
                    logger.info(f"Order for payment_intent_id {session.payment_intent} already exists. Skipping duplicate fulfillment.")
                    return HttpResponse(status=200)

                shipping_full_name = session.metadata.get('shipping_full_name', 'N/A')
                shipping_email = session.metadata.get('shipping_email', session.customer_details.get('email', 'N/A'))
                shipping_phone_number = session.metadata.get('shipping_phone_number', '')

                shipping_address_parts = []

                # --- START: MORE ROBUST SHIPPING DETAILS EXTRACTION ---
                # Safely get shipping_details, which might be None or not present at all.
                stripe_shipping_details = session.get('shipping_details')

                # Prefer Stripe's collected shipping details if available and complete.
                if stripe_shipping_details and stripe_shipping_details.get('address'):
                    address = stripe_shipping_details['address'] # Access as dict for safety
                    
                    # Update name and email from Stripe's collected details if available
                    if stripe_shipping_details.get('name'):
                        shipping_full_name = stripe_shipping_details['name']
                    if session.customer_details and session.customer_details.get('email'):
                        shipping_email = session.customer_details.get('email')

                    # Build address parts from Stripe's shipping_details
                    if address.get('line1'): shipping_address_parts.append(address['line1'])
                    if address.get('line2'): shipping_address_parts.append(address['line2'])
                    if address.get('city'): shipping_address_parts.append(address['city'])
                    if address.get('state'): shipping_address_parts.append(address['state'])
                    if address.get('postal_code'): shipping_address_parts.append(address['postal_code'])
                    if address.get('country'): shipping_address_parts.append(address['country'])
                else:
                    # Fallback to metadata if Stripe didn't collect sufficient shipping address
                    if session.metadata.get('shipping_address_line1'): shipping_address_parts.append(session.metadata.get('shipping_address_line1'))
                    if session.metadata.get('shipping_address_line2'): shipping_address_parts.append(session.metadata.get('shipping_address_line2'))
                    if session.metadata.get('shipping_city'): shipping_address_parts.append(session.metadata.get('shipping_city'))
                    if session.metadata.get('shipping_state'): shipping_address_parts.append(session.metadata.get('shipping_state'))
                    if session.metadata.get('shipping_zip_code'): shipping_address_parts.append(session.metadata.get('shipping_zip_code'))
                    if session.metadata.get('shipping_country'): shipping_address_parts.append(session.metadata.get('shipping_country'))

                shipping_address_str = "\n".join(filter(None, shipping_address_parts)) or "No shipping address provided."
                # --- END: MORE ROBUST SHIPPING DETAILS EXTRACTION ---

                create_order = Order(
                    user=user,
                    full_name=shipping_full_name,
                    email=shipping_email,
                    shipping_address=shipping_address_str,
                    shipping_phone_number=shipping_phone_number,
                    amount_paid=amount_total,
                    status='pending',
                    payment_intent_id=session.payment_intent,
                    stripe_checkout_session_id=session.id
                )
                create_order.save()

                for cart_item in cart_items:
                    size_variant = cart_item.size_variant
                    item_quantity = cart_item.quantity

                    if size_variant and size_variant.quantity >= item_quantity:
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

                cart.items.all().delete()

                logger.info(f"Order {create_order.id} for user {user.username} fulfilled successfully via webhook.")
                return HttpResponse(status=200)

        except Exception as e:
            logger.error(f"Error during webhook order processing for user {user_id}, cart {cart_id}: {e}", exc_info=True)
            return HttpResponse(status=500)

    else:
        logger.warning(f"Unhandled webhook event type: {event['type']}")
        return HttpResponse(status=200)

# --- User-Facing Payment Status Views ---

def payment_success(request):
    """
    Renders the success page after a payment is confirmed by Stripe.
    Order fulfillment is handled by the webhook, not this view.
    """
    messages.success(request, "Payment successful! Your order has been placed.")
    return render(request, 'payment/success.html')

def payment_cancel(request):
    """
    Renders the cancel page if a payment is not completed or is canceled on Stripe.
    """
    messages.error(request, "Payment canceled or failed. Please try again.")
    return render(request, 'payment/cancel.html')

# --- User and Admin Order Dashboard Views ---

@login_required
def user_orders(request):
    """
    Displays a list of all orders for the logged-in user.
    """
    orders = Order.objects.filter(user=request.user).order_by('-created_at')
    return render(request, 'payment/user_orders.html', {'orders': orders})

@login_required
def user_order_detail(request, order_id):
    """
    Displays the detailed information for a specific order belonging to the logged-in user.
    """
    order = get_object_or_404(Order, id=order_id, user=request.user)
    order_items_queryset = OrderItem.objects.filter(order=order)
    items_total = sum(item.price * item.quantity for item in order_items_queryset)

    context = {
        'order': order,
        'order_items': order_items_queryset,
        'items_total': items_total,
    }
    return render(request, 'payment/user_order_detail.html', context)

@login_required
def admin_dashboard(request):
    """
    Provides an overview dashboard for superusers, displaying order statistics.
    """
    if not request.user.is_superuser:
        messages.error(request, "Access denied. You must be a superuser to view this page.")
        return redirect('core:index')

    all_orders = Order.objects.all()
    shipped_orders_queryset = Order.objects.filter(status='shipped')
    unshipped_orders_queryset = Order.objects.filter(status='pending')

    total_orders = all_orders.count()
    shipped_orders_count = shipped_orders_queryset.count()
    unshipped_orders_count = unshipped_orders_queryset.count()

    total_revenue_value = all_orders.aggregate(total_sum=Sum('amount_paid'))['total_sum'] or 0.0
    total_shipped_sales_value = shipped_orders_queryset.aggregate(total_sum=Sum('amount_paid'))['total_sum'] or 0.0
    total_pending_sales_value = unshipped_orders_queryset.aggregate(total_sum=Sum('amount_paid'))['total_sum'] or 0.0

    context = {
        'total_orders': total_orders,
        'shipped_orders': shipped_orders_count,
        'unshipped_orders': unshipped_orders_count,
        'total_revenue': total_revenue_value,
        'total_shipped_sales_value': total_shipped_sales_value,
        'total_pending_sales_value': total_pending_sales_value,
    }
    return render(request, 'payment/admin_dashboard.html', context)

@login_required
def order_detail(request, order_id):
    """
    Displays the details of a specific order for superusers,
    allowing them to update the order's shipping status.
    """
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. You must be logged in as an admin.')
        return redirect('core:index')

    order = get_object_or_404(Order, id=order_id)
    order_items_queryset = OrderItem.objects.filter(order=order)
    items_total = sum(item.price * item.quantity for item in order_items_queryset)

    # `items` list is prepared for template iteration, if required.
    items = [order_item.item for order_item in order_items_queryset]

    if request.method == 'POST':
        new_status = request.POST.get('shipping_status')

        valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
        if new_status and new_status in valid_statuses:
            order.status = new_status
            order.save(update_fields=['status'])
            messages.success(request, f'Order status updated to {order.get_status_display()}.')
        else:
            messages.error(request, 'Invalid status provided.')

        return redirect('payment:order_detail', order_id=order_id)

    context = {
        'order': order,
        'order_items': order_items_queryset,
        'items': items,
        'items_total': items_total,
    }
    return render(request, 'payment/order_detail.html', context)

@login_required
def shipped_dashboard(request):
    """
    Displays a dashboard for superusers showing only shipped orders.
    """
    if not request.user.is_superuser:
        messages.error(request, "Access denied. You must be a superuser to view this page.")
        return redirect('core:index')

    shipped_orders_queryset = Order.objects.filter(status='shipped').order_by('-created_at')
    shipped_orders_count = shipped_orders_queryset.count()
    total_shipped_sales_value = shipped_orders_queryset.aggregate(total_sum=Sum('amount_paid'))['total_sum'] or 0.0

    context = {
        'orders': shipped_orders_queryset,
        'shipped_orders_count': shipped_orders_count,
        'total_shipped_sales_value': total_shipped_sales_value,
    }
    return render(request, 'payment/shipped_dashboard.html', context)

@login_required
def not_shipped_dashboard(request):
    """
    Displays a dashboard for superusers showing only pending (unshipped) orders.
    """
    if not request.user.is_superuser:
        messages.error(request, "Access denied. You must be a superuser to view this page.")
        return redirect('core:index')

    unshipped_orders_queryset = Order.objects.filter(status='pending').order_by('-created_at')

    unshipped_orders_count = unshipped_orders_queryset.count()
    total_pending_sales_value = unshipped_orders_queryset.aggregate(total_sum=Sum('amount_paid'))['total_sum'] or 0.0

    context = {
        'orders': unshipped_orders_queryset,
        'unshipped_orders_count': unshipped_orders_count,
        'total_pending_sales_value': total_pending_sales_value,
    }
    return render(request, 'payment/not_shipped_dashboard.html', context)