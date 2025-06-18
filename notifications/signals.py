from django.db.models.signals import post_save # Signal sent after a model is saved
from django.dispatch import receiver # Decorator to connect signals
from django.contrib.auth.models import User # Required if not already imported by Order
from .models import Notification # Your Notification model
from payment.models import Order # The model we are listening to


@receiver(post_save, sender=Order)
def create_order_status_notification(sender, instance, created, **kwargs):
    """
    Creates an in-app notification when an Order's status changes.
    """
    if created:
        # If a new order is created, send a 'new order' notification
        content_message = f"Your order #{instance.id} has been placed successfully and is currently '{instance.get_status_display()}'. Thank you!"
        Notification.objects.create(
            user=instance.user,
            order=instance,
            content=content_message, # Changed 'message' to 'content'
            notification_type='order_placed' # Added notification type for new orders
        )
        return

    # If the order is being updated (not created for the first time)
    try:
        # Get the old instance from the database to compare status
        old_instance = sender.objects.get(pk=instance.pk)
    except sender.DoesNotExist:
        # This case should ideally not happen for an 'updated' instance, but good to handle
        return

    # Check if the 'status' field has actually changed
    if old_instance.status != instance.status:
        notification_content = ""
        notification_type = 'general' # Default type

        if instance.status == 'shipped':
            notification_content = f"Your order #{instance.id} has been shipped! Tracking: {instance.tracking_number if instance.tracking_number else 'N/A'}"
            notification_type = 'order_shipped'
        elif instance.status == 'delivered':
            notification_content = f"Your order #{instance.id} has been delivered! Enjoy your items!"
            notification_type = 'order_delivered' # Added new type for delivered
        elif instance.status == 'canceled':
            notification_content = f"Your order #{instance.id} has been canceled. Please contact support for more details."
            notification_type = 'order_canceled'
        elif instance.status == 'pending' and old_instance.status != 'pending': # Status changed back to pending
             notification_content = f"Your order #{instance.id} status has been updated to '{instance.get_status_display()}'."
             notification_type = 'order_status_update' # Added new type for general status updates

        # Only create notification if a specific content was set
        if notification_content:
            Notification.objects.create(
                user=instance.user,
                order=instance,
                content=notification_content, # Changed 'message' to 'content'
                notification_type=notification_type # Added notification type
            )

    # Consider adding a check for tracking_number change here if not handled elsewhere
    # (though your views.py already handles tracking_update when order is 'shipped')
    # If old_instance.tracking_number != instance.tracking_number and instance.tracking_number:
    #     Notification.objects.create(
    #         user=instance.user,
    #         order=instance,
    #         content=f"The tracking number for your order #{instance.id} has been updated to: {instance.tracking_number}.",
    #         notification_type='tracking_update'
    #     )