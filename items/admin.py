from django.contrib import admin
from .models import Category, Items, ItemImage, SizeVariant


class SizeVariantInline(admin.TabularInline):
    model = SizeVariant
    extra = 1


@admin.register(Items)
class ItemsAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'category', 'price', 'quantity', 'is_sold']
    list_filter = ('category', 'is_sold')
    search_fields = ('name', 'description')
    readonly_fields = ['id']
    inlines = [SizeVariantInline]

    def get_fields(self, request, obj=None):
        fields = super().get_fields(request, obj)
        if 'id' in fields:
            fields.remove('id')
            fields = ['id'] + fields
        return fields


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ('name',)
    search_fields = ('name',)


@admin.register(ItemImage)
class ItemImageAdmin(admin.ModelAdmin):
    list_display = ('item', 'image')
    list_filter = ('item',)
    search_fields = ('item__name',)


@admin.register(SizeVariant)
class SizeVariantAdmin(admin.ModelAdmin):
    list_display = ('item', 'size', 'quantity')
    list_filter = ('item', 'size')
    search_fields = ('item__name', 'size')