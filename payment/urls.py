from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'payment'

urlpatterns = [
    path('payment_success', views.payment_success, name='payment_success'),
    path('checkout', views.checkout, name='checkout'),
    path('billing_info', views.billing_info, name='billing_info'),
    path("process_order", views.process_order, name="process_order"),
    path('shipped_dashboard', views.shipped_dashboard, name='shipped_dashboard'),
    path('not_shipped_dashboard', views.not_shipped_dashboard, name='not_shipped_dashboard'),
    path('admin_dashboard', views.admin_dashboard, name='admin_dashboard'),
    path('order_detail/<int:order_id>/', views.order_detail, name='order_detail'),


    
    

]