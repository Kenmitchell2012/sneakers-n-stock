from django.db import models
from django.contrib.auth.models import User
from items.models import Items, SizeVariant
from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver
from django.utils import timezone

import datetime
# Create your models here.

# Create shipping address model for user
class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    shipping_full_name = models.CharField(max_length=255)
    shipping_email = models.EmailField(max_length=255)
    shipping_address = models.CharField(max_length=255)
    shipping_city = models.CharField(max_length=255)
    shipping_state = models.CharField(max_length=255)
    shipping_zip_code = models.CharField(max_length=10)
    shipping_phone_number = models.CharField(max_length=20, null=True, blank=True)
    shipping_country = models.CharField(max_length=255)

    # dont pluralize address
    class Meta:
        verbose_name_plural = 'Shipping Address'

    def __str__(self):
        return f'Shipping Address - {str(self.id)}'
    
# order model

class Order(models.Model):
    # --- Status Choices ---
    STATUS_CHOICES = (
        ('pending', 'Pending'),
        ('shipped', 'Shipped'),
        ('delivered', 'Delivered'), # Optional: Add more statuses as needed
        ('canceled', 'Canceled'),
    )
    # --- END STATUS CHOICES ---

    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=255)
    email = models.EmailField()
    shipping_address = models.TextField()
    amount_paid = models.FloatField()
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    shipping_phone_number = models.CharField(max_length=20, blank=True, null=True) # Max length for phone number
    date_shipped = models.DateTimeField(null=True, blank=True) # To store when it was shipped
    tracking_number = models.CharField(max_length=255, blank=True, null=True) 

    payment_intent_id = models.CharField(max_length=255, null=True, blank=True, unique=True)
    stripe_checkout_session_id = models.CharField(max_length=255, null=True, blank=True, unique=True)

    class Meta:
        ordering = ('-created_at',)

    def __str__(self):
        return f"Order {self.id} by {self.full_name} ({self.get_status_display()})" # Added status to __str__


# @receiver(post_save, sender=Order) # This decorator should be above your function
def det_shipped_date_on_update(sender, instance, created, **kwargs):
    # This signal listener updates the 'date_shipped' field
    # when an Order's status changes to 'shipped'.

    # This logic should only run on updates to existing orders.
    if not created:
        # Check if the 'status' field is being updated to 'shipped'
        # To make this check more robust and prevent setting date_shipped multiple times,
        # we check if the new status is 'shipped' AND the 'date_shipped' field is currently None.
        if instance.status == 'shipped' and instance.date_shipped is None:
            instance.date_shipped = timezone.now()
            try:
                # Save only the 'date_shipped' field to avoid infinite recursion
                # when saving from within a signal.
                instance.save(update_fields=['date_shipped'])
                # logger.info(f"Order {instance.id} status changed to 'shipped'. date_shipped set to {instance.date_shipped}")
                # (Uncomment the logger if you have logger imported and configured)
            except Exception as e:
                # logger.error(f"Error saving date_shipped for Order {instance.id}: {e}", exc_info=True)
                # (Uncomment the logger if you have logger imported and configured)
                pass # Or handle the exception appropriately

# order model items

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="order_items", null=True)
    item = models.ForeignKey(Items, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    size_variant = models.ForeignKey(SizeVariant, on_delete=models.SET_NULL, null=True, blank=True)

    quantity = models.PositiveBigIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        total = self.quantity * self.price
        return f'{self.quantity} × {self.item} @ ${self.price:.2f} each = ${total:.2f} (Order #{self.order.id})'
    
@receiver(post_save, sender=Order)
def set_shipped_date_on_status_change(sender, instance, created, **kwargs):
    # This signal listener updates the 'date_shipped' field
    # when an Order's status changes to 'shipped'.

    # This logic should only run on updates to existing orders.
    if not created:
        # Crucially, check if the status just became 'shipped' AND date_shipped is not already set
        if instance.status == 'shipped' and instance.date_shipped is None:
            instance.date_shipped = timezone.now()
            try:
                # Save only the 'date_shipped' field to avoid infinite recursion
                instance.save(update_fields=['date_shipped'])
                # Uncomment for debugging:
                # import logging
                # logger = logging.getLogger(__name__)
                # logger.info(f"Order {instance.id} status changed to 'shipped'. date_shipped set to {instance.date_shipped}")
            except Exception as e:
                # Uncomment for debugging:
                # import logging
                # logger = logging.getLogger(__name__)
                # logger.error(f"Error saving date_shipped for Order {instance.id}: {e}", exc_info=True)
                pass # Or handle the exception appropriately