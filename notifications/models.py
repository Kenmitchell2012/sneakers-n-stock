from django.db import models
from django.contrib.auth.models import User
from payment.models import Order
from conversation.models import Conversation

# Create your models here.

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)

    # New field: Type of notification (e.g., 'order_shipped', 'order_canceled')
    NOTIFICATION_TYPES = (
        ('order_shipped', 'Order Shipped'),
        ('order_canceled', 'Order Canceled'),
        ('tracking_update', 'Tracking Number Updated'), # For when tracking is added/changed
        ('general', 'General Notification'), # For other future notifications
        ('order_placed', 'Order Placed'), # For new orders
        ('new_message', 'New Message'), # For new messages in conversations
        # Add more types as needed
    )
    notification_type = models.CharField(max_length=50, choices=NOTIFICATION_TYPES, default='general')

    # Renamed from 'message' to 'content' for clarity and consistency
    content = models.TextField()

    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"Notification for {self.user.username} - {self.content[:50]}..."

    # Optional: Add a method to mark as read
    def mark_as_read(self):
        self.is_read = True
        self.save()

    def get_absolute_url(self):
        from django.urls import reverse # Import here to avoid circular imports

        if self.notification_type in ['order_shipped', 'order_canceled', 'tracking_update', 'order_placed', 'order_delivered', 'order_status_update'] and self.order:
            return reverse('payment:user_order_detail', args=[self.order.id])
        elif self.notification_type == 'new_message' and self.conversation: # NEW URL LOGIC
            return reverse('conversations:detail', args=[self.conversation.id])
        return '#'

