from django.db import models
from django.contrib.auth.models import User

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

class ItemImage(models.Model):
    item = models.ForeignKey(Items, related_name='images', on_delete=models.CASCADE)
    image = models.ImageField(upload_to='item_images')

    def __str__(self):
        return f"Image for {self.item.name}"