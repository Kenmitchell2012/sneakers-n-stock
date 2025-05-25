from django.db import models
from django.contrib.auth.models import User
from django.db.models import Sum

# Create your models here.
class Category(models.Model):
    name = models.CharField(max_length=255)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Categories'

    def __str__(self):
        return self.name
    
class Items(models.Model):
    category = models.ForeignKey(Category, related_name='items', on_delete=models.CASCADE)
    name = models.CharField(max_length=255)
    description = models.CharField(max_length=455, blank=True, null=True)
    price = models.FloatField()
    quantity = models.PositiveIntegerField(default=0)
    is_sold = models.BooleanField(default=False)
    created_by = models.ForeignKey(User, related_name='items', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ('name',)
        verbose_name_plural = 'Items'

    def __str__(self):
        return self.name
    
class SizeVariant(models.Model):
    item = models.ForeignKey(Items, related_name='size_variants', on_delete=models.CASCADE)
    size = models.CharField(max_length=50)
    quantity = models.PositiveIntegerField(default=0)

    def __str__(self):
        return f"{self.item.name} - {self.size}"

    # Override the save method to update the parent Item's quantity
    def save(self, *args, **kwargs):
        # Call the original save method to save the SizeVariant instance first
        super().save(*args, **kwargs)
        
        # Recalculate the total quantity for the related Item
        # item.size_variants.aggregate(Sum('quantity')) returns a dictionary like {'quantity__sum': 10}
        total_quantity = self.item.size_variants.aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        # Update the Item's quantity
        self.item.quantity = total_quantity
        self.item.save(update_fields=['quantity']) # Use update_fields for efficiency

    # Optional: Override the delete method to update the parent Item's quantity
    def delete(self, *args, **kwargs):
        # Get the item before deletion so we can access it after the delete call
        related_item = self.item 
        
        # Call the original delete method to delete the SizeVariant instance
        super().delete(*args, **kwargs)
        
        # Recalculate the total quantity for the related Item after deletion
        total_quantity = related_item.size_variants.aggregate(Sum('quantity'))['quantity__sum'] or 0
        
        # Update the Item's quantity
        related_item.quantity = total_quantity
        related_item.save(update_fields=['quantity']) # Use update_fields for efficiency


class ItemImage(models.Model):
    item = models.ForeignKey(Items, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='item_images')

    def __str__(self):
        return f"Image for {self.item.name}"