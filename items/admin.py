from django.contrib import admin

# Register your models here.

from . models import Category, Items

admin.site.register(Category)
admin.site.register(Items)

