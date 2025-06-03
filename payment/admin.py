from django.contrib import admin
from django.db.models import Sum 
from .models import ShippingAddress, Order, OrderItem # Make sure all models are imported
from django.contrib.auth.models import User # For user related fields/filters

# Register ShippingAddress 
admin.site.register(ShippingAddress)

# create order item inline
class OrderItemInline(admin.TabularInline): 
    model = OrderItem
    extra = 0 # No extra empty forms by default
    # specify readonly fields for OrderItem inlines if you don't want them edited here
    # readonly_fields = ('item', 'size_variant', 'quantity', 'price') 

# Extend Order model and register using the decorator
@admin.register(Order) # <--- Using decorator to register Order with OrderAdmin
class OrderAdmin(admin.ModelAdmin):
    # Display fields in the list view of the admin
    list_display = (
        'id', 
        'user', 
        'full_name', 
        'amount_paid', 
        'status', 
        'created_at', 
        'stripe_checkout_session_id' # Useful for debugging Stripe
    )
    
    # Fields to filter by in the right sidebar of the admin list view
    list_filter = ('status', 'created_at', 'user') 
    
    # Fields to search by
    search_fields = ('id', 'full_name', 'email', 'shipping_address', 'payment_intent_id') 
    
    # Fields that should be read-only in the detailed order view
    readonly_fields = (
        'id', 
        'user', 
        'amount_paid', 
        'created_at', 
        'payment_intent_id', 
        'stripe_checkout_session_id'
    )
    
    # Fields to show/edit in the detailed order view (excluding readonly_fields here)
    # Order of fields in the form
    fields = (
        'user', 
        'full_name', 
        'email', 
        'shipping_address', 
        'amount_paid', 
        'status', 
        'created_at', 
        'payment_intent_id', 
        'stripe_checkout_session_id'
    )
    
    # Link OrderItems directly below the Order details
    inlines = [OrderItemInline]

    # Custom Admin Actions (for bulk updating order status)
    actions = ['mark_as_shipped', 'mark_as_pending']

    @admin.action(description='Mark selected orders as Shipped')
    def mark_as_shipped(self, request, queryset):
        queryset.update(status='shipped')
        self.message_user(request, f"{queryset.count()} orders marked as Shipped.", level=admin.messages.SUCCESS)

    @admin.action(description='Mark selected orders as Pending')
    def mark_as_pending(self, request, queryset):
        queryset.update(status='pending')
        self.message_user(request, f"{queryset.count()} orders marked as Pending.", level=admin.messages.INFO)


# Register OrderItem 
admin.site.register(OrderItem)
