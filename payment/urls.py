from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'payment'

urlpatterns = [
    path('payment_success', views.payment_success, name='payment_success'),
    path('checkout', views.checkout, name='checkout'),
    path('billing_info', views.billing_info, name='billing_info'),
    
    

]