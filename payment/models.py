from django.db import models
from django.contrib.auth.models import User
from items.models import Items
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
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    full_name = models.CharField(max_length=250, null=True, blank=True)
    email = models.EmailField(max_length=255)
    shipping_address = models.TextField(max_length=15000)
    amount_paid = models.DecimalField(max_digits=8, decimal_places=2)
    date_ordered = models.DateTimeField(auto_now_add=True)

    def __str__(self):
         return f'Order #{self.id} - ${self.amount_paid:.2f}'


# order model items

class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, null=True)
    item = models.ForeignKey(Items, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)

    quantity = models.PositiveBigIntegerField(default=1)
    price = models.DecimalField(max_digits=8, decimal_places=2)

    def __str__(self):
        total = self.quantity * self.price
        return f'{self.quantity} × {self.item} @ ${self.price:.2f} each = ${total:.2f} (Order #{self.order.id})'