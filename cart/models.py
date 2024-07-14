from django.db import models
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
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name='items')
    item = models.ForeignKey(Items, on_delete=models.CASCADE)  # Link to your Items model
    quantity = models.PositiveIntegerField(default=1)
    added_at = models.DateTimeField(auto_now_add=True)

    def calculate_item_price(self):
        return self.item.price * self.quantity

    def __str__(self):
        return f"{self.item.name} in cart for {self.cart.user.username}"
