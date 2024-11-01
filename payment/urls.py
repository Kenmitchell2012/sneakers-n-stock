from django.urls import path
from django.contrib.auth import views as auth_views

from . import views

app_name = 'core'

urlpatterns = [
    path('payment_success', views.payment_success, name='payment_success'),
    
    

]