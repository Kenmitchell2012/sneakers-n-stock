from django.db import models
from django.contrib.auth.models import User
# Create your models here.

# Create shipping adress model for user
class ShippingAddress(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)
    shipping_full_name = models.CharField(max_length=255)
    shipping_email = models.EmailField(max_length=255)
    shipping_address = models.CharField(max_length=255)
    shipping_city = models.CharField(max_length=255)
    shipping_state = models.CharField(max_length=255)
    shipping_zip_code = models.CharField(max_length=10)
    shipping_phone_number = models.CharField(max_length=20)
    shipping_country = models.CharField(max_length=255)

    # dont pluralize address
    class Meta:
        verbose_name_plural = 'Shipping Address'

    def __str__(self):
        return f'Shipping Address - {str(self.id)}'
