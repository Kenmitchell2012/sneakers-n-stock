from django.db import models
from django.contrib.auth.models import User
from payment.models import Order

# Create your models here.

class Notification(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='notifications')
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name='notifications', null=True, blank=True)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('-created_at',)
        verbose_name_plural = 'Notifications'

    def __str__(self):
        return f"Notification for {self.user.username} - {self.message[:50]}..."
