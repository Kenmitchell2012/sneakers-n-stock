from django.shortcuts import render

from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.contrib import messages
from django.http import JsonResponse # For potential AJAX marking as read
from django.db.models import Count # For unread count

from .models import Notification
from cart.models import Cart # For cart_item_count in base template
from conversation.models import Conversation # For conversation_count in base template


@login_required
def notification_list(request):
    """
    Displays a list of all notifications for the logged-in user.
    """
    notifications = Notification.objects.filter(user=request.user).order_by('-created_at')

    # Optionally, automatically mark all viewed notifications as read
    # This is a common pattern: when the user visits the notification list, they are "read"
    # Or you can have a separate 'Mark All As Read' button.
    # notifications.update(is_read=True) # Decide if you want this automatic update

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
    return render(request, 'notifications/notification_list.html', context)


@login_required
@require_POST # Ensure it only accepts POST requests
def mark_notification_as_read(request, notification_id):
    """
    Marks a specific notification as read. Can be called via AJAX.
    """
    notification = get_object_or_404(Notification, id=notification_id, user=request.user)
    notification.is_read = True
    notification.save(update_fields=['is_read'])
    
    # Return a success response for AJAX calls
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    else:
        # If not AJAX, redirect back to notification list
        messages.success(request, 'Notification marked as read.')
        return redirect('notifications:list')

@login_required
@require_POST
def mark_all_notifications_as_read(request):
    """
    Marks all notifications for the logged-in user as read.
    """
    Notification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    
    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'success': True})
    else:
        messages.success(request, 'All notifications marked as read.')
        return redirect('notifications:list')

