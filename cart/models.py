from django.db import models
from items.models import SizeVariant  
from django.contrib.auth.models import User
from items.models import Items  # Assuming your Items model is imported correctly

class Cart(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def calculate_total_price(self):
        total_price = 0
        for cart_item in self.items.all():  # Iterate over CartItem instances
            total_price += cart_item.item.price * cart_item.quantity
        return total_price

    def __str__(self):
        return f"Cart for {self.user.username}"

class CartItem(models.Model):
    cart = models.ForeignKey(Cart, related_name='items', on_delete=models.CASCADE)
    item = models.ForeignKey(Items, on_delete=models.CASCADE)
    size_variant = models.ForeignKey(SizeVariant, on_delete=models.CASCADE, null=True, blank=True)
    quantity = models.PositiveIntegerField(default=1) # Ensure this default is set

    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        # This is the crucial part to prevent duplicates
        # A cart can only have one of a specific item with a specific size variant
        unique_together = ('cart', 'item', 'size_variant')
        ordering = ('added_at',) # Optional: keep items in order of addition

    def calculate_item_price(self):
        return self.quantity * self.item.price

    def __str__(self):
        # Handle cases where size_variant might be null (e.g., old data or items without size)
        if self.size_variant:
            return f"{self.item.name} ({self.size_variant.size}) in {self.cart.user.username}'s cart"
        return f"{self.item.name} in {self.cart.user.username}'s cart"
