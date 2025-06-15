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
        message = f"Your order #{instance.id} has been placed successfully and is currently '{instance.get_status_display()}'. Thank you!"
        Notification.objects.create(user=instance.user, order=instance, message=message)
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
        notification_message = ""
        if instance.status == 'shipped':
            notification_message = f"Your order #{instance.id} has been shipped! Tracking: {instance.tracking_number if instance.tracking_number else 'N/A'}"
        elif instance.status == 'delivered':
            notification_message = f"Your order #{instance.id} has been delivered! Enjoy your items!"
        elif instance.status == 'canceled':
            notification_message = f"Your order #{instance.id} has been canceled. Please contact support for more details."
        elif instance.status == 'pending' and old_instance.status != 'pending': # Status changed back to pending
             notification_message = f"Your order #{instance.id} status has been updated to '{instance.get_status_display()}'."

        if notification_message: # Only create notification if a specific message was set
            Notification.objects.create(user=instance.user, order=instance, message=notification_message)