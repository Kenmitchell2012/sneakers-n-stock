# notifications/urls.py

from django.urls import path
from . import views

app_name = 'notifications'

urlpatterns = [
    path('', views.notification_list, name='list'),
    path('<int:notification_id>/read_and_redirect/', views.mark_read_and_redirect, name='mark_read'),
    path('mark-all-read/', views.mark_all_notifications_as_read, name='mark_all_read'),
    path('<int:notification_id>/read_and_redirect/', views.mark_read_and_redirect, name='read_and_redirect'),

]