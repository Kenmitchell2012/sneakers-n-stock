from django.contrib import admin

# Register your models here.

from . models import Category, Items, ItemImage

admin.site.register(Category)
admin.site.register(Items)

admin.site.register(ItemImage)



