from django.contrib import admin
from .models import Category, Items, ItemImage

@admin.register(Items)
class ItemsAdmin(admin.ModelAdmin):
    # Show ID on the list page
    list_display = ['id', 'name', 'price']

    # Make ID visible on the item change page (read-only)
    readonly_fields = ['id']

    # Ensure ID is shown at the top of the form
    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if 'id' not in fields:
            fields = ['id'] + list(fields)
        return fields

admin.site.register(Category)
admin.site.register(ItemImage)