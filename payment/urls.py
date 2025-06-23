from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'payment'

urlpatterns = [
    path('payment_success', views.payment_success, name='payment_success'),
    path('checkout', views.checkout, name='checkout'),
    # path('billing_info', views.billing_info, name='billing_info'),
    # path("process_order", views.process_order, name="process_order"),
    path('shipped_dashboard', views.shipped_dashboard, name='shipped_dashboard'),
    path('not_shipped_dashboard', views.not_shipped_dashboard, name='not_shipped_dashboard'),
    path('admin_dashboard', views.admin_dashboard, name='admin_dashboard'),
    path('order_detail/<int:order_id>/', views.order_detail, name='order_detail'),
    path('user_orders/', views.user_orders, name='user_orders'),
    path('orders/<int:order_id>/', views.user_order_detail, name='user_order_detail'),
    path('order/<int:order_id>/request_cancellation/', views.request_order_cancellation, name='request_order_cancellation'),


# --- PATTERN FOR STRIPE CHECKOUT ---
    # path('create-checkout-session/', views.create_checkout_session, name='create_checkout_session'),
    # --- END STRIPE URL PATTERN ---

    # --- Add placeholder URLs for success and cancel pages ---
    path('webhook/', views.stripe_webhook, name='stripe_webhook'),
    path('success/', views.payment_success, name='success'),
    path('cancel/', views.payment_cancel, name='cancel'),
    # --- END PLACEHOLDER URLS ---
    
    

]