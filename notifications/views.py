# notifications/views.py

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse # For potential AJAX marking as read
from django.db.models import Count # For unread count

from .models import Notification
from cart.models import Cart # For cart_item_count in base template
from conversation.models import Conversation # For conversation_count in base template
from payment.models import Order # Import the Order model to get redirect URLs

import logging
logger = logging.getLogger(__name__)


@login_required
def notification_list(request): # Renamed from original for clarity
    """
    Displays a list of all notifications for the logged-in user.
    """
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    # Get counts for navbar context
    cart, created_cart = Cart.objects.get_or_create(user=request.user)
    cart_item_count = sum(item_in_cart.quantity for item_in_cart in cart.items.all())
    conversations_for_count = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations_for_count.count()

    # Get unread notification count for navbar (even for this page)
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()


    context = {
        'notifications': notifications,
        'cart_item_count': cart_item_count, # For navbar
        'conversation_count': conversation_count, # For navbar
        'unread_notifications_count': unread_notifications_count, # For navbar
    }
    return render(request, 'notifications/notification_list.html', context) # Ensure this matches your template filename

@login_required
def mark_read_and_redirect(request, notification_id):
    """
    Marks a specific notification as read and redirects the user to the
    associated object's detail page (e.g., an order or conversation).
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)

    if not notification.is_read:
        notification.is_read = True
        notification.save(update_fields=['is_read'])
        messages.success(request, f"Notification marked as read.")
    # No 'else' block for messages.info as per previous fix

    redirect_url = None

    # --- Debugging starts here ---
    logger.info(f"DEBUG: Processing notification ID: {notification.id}, Type: {notification.notification_type}, Is Read: {notification.is_read}")

    if notification.order:
        logger.info(f"DEBUG: Notification linked to Order ID: {notification.order.id}")
        redirect_url = redirect('payment:user_order_detail', order_id=notification.order.id)
    elif notification.conversation: # Check if conversation is linked
        logger.info(f"DEBUG: Notification linked to Conversation ID: {notification.conversation.id}")
        redirect_url = redirect('conversations:detail', pk=notification.conversation.id)
    else:
        logger.warning(f"DEBUG: Notification ID: {notification.id} is not linked to an Order or Conversation. Redirecting to notification list.")
    # --- Debugging ends here ---

    # Fallback if no specific redirect URL is determined
    final_redirect = redirect_url or redirect('notifications:list')

    logger.info(f"DEBUG: Final redirect URL for notification ID {notification.id}: {final_redirect.url if final_redirect else 'None'}")
    return final_redirect


@login_required
@require_POST
def mark_all_notifications_as_read(request):
    """
    Marks all notifications for the logged-in user as read.
    """
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)

    # No JSONResponse needed here based on previous conversation, always redirect
    messages.success(request, 'All notifications marked as read.')
    return redirect('notifications:list')
