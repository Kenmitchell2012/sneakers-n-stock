from django.contrib import admin

# Register your models here.

from .models import Notification
@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = ('user', 'order', 'message', 'is_read', 'created_at')
    list_filter = ('is_read', 'created_at', 'user')
    search_fields = ('message', 'user__username', 'order__id')
    readonly_fields = ('created_at',)
    
    def has_add_permission(self, request):
        return False