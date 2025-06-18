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
from django.db.models import Sum, F
from django.db import models
from django.db.models import Prefetch

import stripe
import json
import logging

from conversation.models import Conversation
from items.models import Items, SizeVariant, ItemImage
from cart.models import Cart, CartItem
from payment.models import Order, OrderItem, ShippingAddress
from .forms import ShippingAddressForm, PaymentForm
from notifications.models import Notification # Ensure this import is present

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

    # debug logging will show the correct data if the form populated it
    logger.info(f"DEBUG: Metadata being sent to Stripe: {metadata}")
    logger.info(f"DEBUG: Line items being sent to Stripe: {line_items}")
    logger.info(f"DEBUG: Success URL: {success_url}, Cancel URL: {cancel_url}")

    customer_email_for_stripe = request.user.email if request.user.is_authenticated and request.user.email else None

    if customer_email_for_stripe == '':
        customer_email_for_stripe = None

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=line_items,
            mode='payment',
            success_url=success_url,
            cancel_url=cancel_url,
            customer_email=customer_email_for_stripe,
            # Use the authenticated user's email if available, otherwise None
            # customer_email=request.user.email if request.user.is_authenticated else None,
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
    # notification_count = request.user.notifications.filter(is_read=False).count() if request.user.is_authenticated else 0
        # Get unread notification count for navbar (even for this page)
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()


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
                # debug logging to confirm session ID is stored
                logger.info(f"DEBUG: Stored Stripe Checkout Session ID in session: {request.session.get('stripe_checkout_session_id')}")
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
        'unread_notifications_count': unread_notifications_count,  # For navbar
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

    # Handle the 'checkout.session.completed' event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']

        user_id = session.metadata.get('user_id')
        cart_id = session.metadata.get('cart_id')
        amount_total = session['amount_total'] / 100

        logger.info(f"Checkout Session Completed event received for user {user_id}, cart {cart_id}, total {amount_total}, Payment Intent ID: {session.payment_intent}")

        try:
            with transaction.atomic():
                # 1. Prevent Duplicate Orders: Check if an order with this payment_intent_id already exists.
                if Order.objects.filter(payment_intent_id=session.payment_intent).exists():
                    logger.info(f"Order for payment_intent_id {session.payment_intent} already exists. Skipping duplicate fulfillment.")
                    return HttpResponse(status=200)

                # 2. Get User (Required)
                try:
                    user = User.objects.get(id=user_id)
                except User.DoesNotExist:
                    logger.error(f"User with ID {user_id} not found during webhook processing for session {session.id}. Cannot fulfill order.")
                    return HttpResponse(status=400) # User must exist for order to be valid

                # 3. Get Cart and its items (Robustly)
                cart = None
                cart_items = []
                if cart_id: # Ensure cart_id exists from metadata
                    try:
                        cart = Cart.objects.get(id=cart_id)
                        cart_items = cart.items.all()
                    except Cart.DoesNotExist:
                        logger.warning(f"Cart with ID {cart_id} for user {user_id} not found during webhook processing. "
                                       f"This might happen if the cart was already cleared/deleted. Proceeding without cart items for order details.")
                        # If cart is gone, we can't use cart_items to populate order items.
                        # This scenario is problematic for accurate order item creation.
                        # Ideally, cart items should be fetched from Stripe's line_items if possible,
                        # but your current model relies on the cart_items.

                if not cart_items.exists():
                     logger.warning(f"Cart {cart_id} for user {user_id} is empty or not found during webhook processing. "
                                    f"Cannot create OrderItems without cart contents. Assuming already processed or invalid state for this webhook.")
                     # If the cart is empty or not found and thus no cart_items, and no order exists yet
                     # (checked by payment_intent_id earlier), this indicates a problem.
                     # We return 200 to acknowledge the webhook, but the order won't be fully created.
                     # If you need to create order items even if the cart is gone, you'd parse Stripe's session.line_items.
                     # For now, we're assuming cart_items is the source.
                     return HttpResponse(status=200)


                # 4. Extract Shipping Details (Robustly from Stripe data or metadata)
                shipping_full_name = session.metadata.get('shipping_full_name', 'N/A')
                shipping_email = session.metadata.get('shipping_email', session.customer_details.get('email', 'N/A'))
                shipping_phone_number = session.metadata.get('shipping_phone_number', '')

                shipping_address_parts = []
                stripe_shipping_details = session.get('shipping_details')

                if stripe_shipping_details and stripe_shipping_details.get('address'):
                    address = stripe_shipping_details['address']
                    if stripe_shipping_details.get('name'):
                        shipping_full_name = stripe_shipping_details['name']
                    if session.customer_details and session.customer_details.get('email'):
                        shipping_email = session.customer_details.get('email')

                    if address.get('line1'): shipping_address_parts.append(address['line1'])
                    if address.get('line2'): shipping_address_parts.append(address['line2'])
                    if address.get('city'): shipping_address_parts.append(address['city'])
                    if address.get('state'): shipping_address_parts.append(address['state'])
                    if address.get('postal_code'): shipping_address_parts.append(address['postal_code'])
                    if address.get('country'): shipping_address_parts.append(address['country'])
                else:
                    if session.metadata.get('shipping_address_line1'): shipping_address_parts.append(session.metadata.get('shipping_address_line1'))
                    if session.metadata.get('shipping_address_line2'): shipping_address_parts.append(session.metadata.get('shipping_address_line2'))
                    if session.metadata.get('shipping_city'): shipping_address_parts.append(session.metadata.get('shipping_city'))
                    if session.metadata.get('shipping_state'): shipping_address_parts.append(session.metadata.get('shipping_state'))
                    if session.metadata.get('shipping_zip_code'): shipping_address_parts.append(session.metadata.get('shipping_zip_code'))
                    if session.metadata.get('shipping_country'): shipping_address_parts.append(session.metadata.get('shipping_country'))

                shipping_address_str = "\n".join(filter(None, shipping_address_parts)) or "No shipping address provided."


                # 5. Create the Order
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
                create_order.save() # <-- If you have a post_save signal here, it will fire

                # 6. Create Order Items and Update Stock
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
                        logger.error(f"Overselling detected! Item {cart_item.item.name} (Size {size_variant.size}) out of stock during webhook fulfillment for Order {create_order.id}, Cart {cart.id}")
                        # This scenario should ideally be caught before checkout, but if it happens,
                        # you might need to implement a refund or manual intervention here.
                        pass

                # 7. Clear the User's Cart Items (but not the cart itself)
                if cart: # Only if cart object was successfully retrieved
                    cart.items.all().delete()

                logger.info(f"Order {create_order.id} for user {user.username} fulfilled successfully via webhook.")
                return HttpResponse(status=200)

        except Exception as e:
            logger.error(f"Error during webhook order processing for user {user_id}, cart {cart_id}: {e}", exc_info=True)
            return HttpResponse(status=500)

    # Log and respond to unhandled event types
    else:
        logger.warning(f"Unhandled webhook event type: {event['type']}")
        return HttpResponse(status=200)

# --- User-Facing Payment Status Views ---

def payment_success(request):
    logger.info(f"DEBUG: payment_success hit. Session ID received: {request.session.get('stripe_checkout_session_id')}")
    """
    Renders the success page after a payment is confirmed by Stripe.
    Attempts to retrieve and display details of the most recent successful order.
    """
    unread_notifications_count = 0
    if request.user.is_authenticated:
        unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    order = None
    order_items = None
    items_total = 0

    # Try to retrieve the Stripe Checkout Session ID from the session
    stripe_checkout_session_id = request.session.get('stripe_checkout_session_id')

    if request.user.is_authenticated and stripe_checkout_session_id:
        try:
            logger.info(f"DEBUG: Attempting to find Order for user {request.user.id} with session ID {stripe_checkout_session_id}")
            # Find the order associated with this checkout session ID
            order = Order.objects.select_related('user').prefetch_related('order_items__item').get(
                user=request.user,
                stripe_checkout_session_id=stripe_checkout_session_id
            )
            # ADD THIS LINE HERE:
            logger.info(f"DEBUG: Order found! Order ID: {order.id}, Payment Intent ID: {order.payment_intent_id}")

            order_items = order.order_items.all()
            items_total = sum(item.price * item.quantity for item in order_items)

            # Optional: Clear the session variable after use
            if 'stripe_checkout_session_id' in request.session:
                logger.info(f"DEBUG: Deleting stripe_checkout_session_id from session.")
                del request.session['stripe_checkout_session_id']

        except Order.DoesNotExist:
            messages.warning(request, "Could not find details for your recent order. Please check your order history.")
            logger.warning(f"DEBUG: Payment success page: Order not found for user {request.user.id} with session ID {stripe_checkout_session_id}. Order.DoesNotExist.")
        except Exception as e:
            messages.error(request, "An error occurred while fetching your order details.")
            logger.error(f"DEBUG: Payment success page: Error fetching order for user {request.user.id}, session {stripe_checkout_session_id}: {e}", exc_info=True)
    elif not request.user.is_authenticated:
        messages.info(request, "Please log in to view your order history and details.")
        logger.info(f"DEBUG: User not authenticated on payment_success page.")


    # Always show a success message
    messages.success(request, "Payment successful! Your order has been placed.")

    context = {
        'unread_notifications_count': unread_notifications_count,
        'order': order,
        'order_items': order_items,
        'items_total': items_total,
    }
    return render(request, 'payment/success.html', context)


def payment_cancel(request):
    """
    Renders the cancellation page after a payment is canceled by the user.
    """
    unread_notifications_count = 0
    if request.user.is_authenticated:
        unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    # Always show a cancellation message
    messages.info(request, "Payment canceled. Your order was not processed.")

    context = {
        'unread_notifications_count': unread_notifications_count,
    }
    return render(request, 'payment/cancel.html', context)

# --- User and Admin Order Dashboard Views ---

@login_required
def user_orders(request):
    """
    Displays a list of all orders for the logged-in user.
    """
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()
    orders = Order.objects.filter(user=request.user).order_by('-created_at').annotate(
        total_items_in_order=Sum('order_items__quantity', default=0) # Sum of all OrderItem quantities
    ).prefetch_related(
        Prefetch('order_items__item__images', queryset=ItemImage.objects.filter(image__isnull=False)) # Prefetch images, optionally filter out null image links
    )

    context = {
        'orders': orders,
        'conversation_count': conversation_count,  # Pass the count to the template
    }
    return render(request, 'payment/user_orders.html', context)

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

    # --- 1. Get Filter Parameter ---
    # Default to showing 'pending' orders if no filter or 'all' is explicitly requested
    status_filter = request.GET.get('status', 'pending') # Default filter

    # --- 2. Calculate Summary Metrics (for the top cards) ---
    all_orders_queryset = Order.objects.all()
    shipped_orders_queryset = Order.objects.filter(status='shipped')
    unshipped_orders_queryset = Order.objects.filter(status='pending') # Or 'delivered', 'canceled'

    total_orders_count = all_orders_queryset.count()
    shipped_orders_count = shipped_orders_queryset.count()
    unshipped_orders_count = unshipped_orders_queryset.count()

    total_revenue_value = all_orders_queryset.aggregate(total_sum=Sum('amount_paid'))['total_sum'] or 0.0
    total_shipped_sales_value = shipped_orders_queryset.aggregate(total_sum=Sum('amount_paid'))['total_sum'] or 0.0
    total_pending_sales_value = unshipped_orders_queryset.aggregate(total_sum=Sum('amount_paid'))['total_sum'] or 0.0

    # --- 3. Filter Orders for the List Display (bottom half) ---
    orders_for_list = Order.objects.all().order_by('-created_at') # Start with all orders

    if status_filter == 'shipped':
        orders_for_list = orders_for_list.filter(status='shipped')
    elif status_filter == 'pending':
        orders_for_list = orders_for_list.filter(status='pending')
    elif status_filter == 'delivered': # Add if you plan to filter by delivered
        orders_for_list = orders_for_list.filter(status='delivered')
    elif status_filter == 'canceled': # Add if you plan to filter by canceled
        orders_for_list = orders_for_list.filter(status='canceled')
    # If status_filter is 'all' or an invalid value, it will show all orders by default (which is good)

    context = {
        # Summary Metrics
        'total_orders_count': total_orders_count, # Renamed for clarity with _count suffix
        'shipped_orders_count': shipped_orders_count,
        'unshipped_orders_count': unshipped_orders_count,
        'total_revenue': total_revenue_value,
        'total_shipped_sales_value': total_shipped_sales_value,
        'total_pending_sales_value': total_pending_sales_value,

        # For the Order List
        'orders_for_list': orders_for_list, # The filtered list of orders
        'current_status_filter': status_filter, # To highlight active filter in template
    }
    return render(request, 'payment/admin_dashboard.html', context)

# --- Order Detail View for Admins ---
@login_required
def order_detail(request, order_id):
    """
    Displays the details of a specific order for superusers,
    allowing them to update the order's shipping status and tracking number.
    """
    if not request.user.is_superuser:
        messages.error(request, 'Access denied. You must be logged in as an admin.')
        return redirect('core:index')

    order = get_object_or_404(Order, id=order_id)
    order_items_queryset = OrderItem.objects.filter(order=order)
    items_total = sum(item.price * item.quantity for item in order_items_queryset)

    items = [order_item.item for order_item in order_items_queryset]


    if request.method == 'POST':
        # Retrieve the new status value and tracking number from the form submission
        new_status = request.POST.get('shipping_status')
        tracking_number_input = request.POST.get('tracking_number', '').strip() # Get tracking number, default to empty string

        try:
            with transaction.atomic(): # Ensure both updates are atomic
                status_updated = False
                tracking_updated = False
                old_status = order.status # Store old status before potential update

                # Update order status if provided and valid
                valid_statuses = [choice[0] for choice in Order.STATUS_CHOICES]
                if new_status and new_status in valid_statuses:
                    # Only update if the status is actually changing
                    if order.status != new_status:
                        order.status = new_status
                        order.save(update_fields=['status'])
                        messages.success(request, f'Order status updated to {order.get_status_display()}.')
                        status_updated = True

                        # --- Notification Logic for Status Change ---
                        if new_status == 'shipped':
                            Notification.objects.create(
                                user=order.user,
                                order=order, # Link the notification directly to the order
                                notification_type='order_shipped',
                                content=f'Your order #{order.id} has been shipped! Tracking Number: {order.tracking_number if order.tracking_number else "N/A"}.'
                            )
                            messages.info(request, "Customer has been notified that the order is shipped.")
                        elif new_status == 'canceled':
                            Notification.objects.create(
                                user=order.user,
                                order=order, # Link the notification directly to the order
                                notification_type='order_canceled',
                                content=f'Your order #{order.id} has been canceled. Please contact support for more details.'
                            )
                            messages.info(request, "Customer has been notified that the order is canceled.")
                        # --- End Notification Logic ---

                elif new_status: # If new_status was provided but invalid
                    messages.error(request, 'Invalid status provided.')

                # Update tracking number if it's different from current
                if 'tracking_number' in request.POST and order.tracking_number != tracking_number_input:
                    order.tracking_number = tracking_number_input if tracking_number_input else None # Save None if empty string
                    order.save(update_fields=['tracking_number'])
                    if tracking_number_input:
                        messages.success(request, 'Tracking number updated.')
                    else:
                        messages.info(request, 'Tracking number cleared.')
                    tracking_updated = True

                    # --- Notification Logic for Tracking Number Update (if status is already shipped) ---
                    # This is optional, but useful if tracking number is added *after* initial "shipped" status
                    if order.status == 'shipped' and status_updated is False: # Only if status wasn't just set to shipped
                         Notification.objects.create(
                            user=order.user,
                            order=order, # Link the notification directly to the order
                            notification_type='tracking_update',
                            content=f'The tracking number for your order #{order.id} has been updated to: {order.tracking_number}.'
                        )
                         messages.info(request, "Customer has been notified about tracking number update.")
                    # --- End Notification Logic ---

                if not (status_updated or tracking_updated):
                    messages.info(request, 'No changes detected for update.')


        except Exception as e:
            logger.error(f"Error updating order {order_id} details: {e}", exc_info=True)
            messages.error(request, "An error occurred while updating order details.")

        return redirect('payment:order_detail', order_id=order_id)

    # For GET requests, render the detail page
    context = {
        'order': order,
        'order_items': order_items_queryset,
        'items': items,
        'items_total': items_total,
    }
    return render(request, 'payment/order_detail.html', context)

# --- Shipped and Not Shipped Dashboards for Superusers ---
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

# --- Not Shipped Dashboard for Superusers ---
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