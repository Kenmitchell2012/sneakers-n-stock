from django.contrib import admin
from .models import Notification

class NotificationAdmin(admin.ModelAdmin):
    # Change 'message' to 'content' here
    list_display = ('user', 'notification_type', 'content', 'is_read', 'created_at')
    list_filter = ('notification_type', 'is_read', 'created_at')
    search_fields = ('user__username', 'content', 'order__id') # Also update search_fields if it used 'message'

admin.site.register(Notification, NotificationAdmin)