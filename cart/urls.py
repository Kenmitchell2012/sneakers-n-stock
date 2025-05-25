from django.urls import path
from . import views

app_name = 'cart'

urlpatterns = [
    path('add/<int:item_id>/', views.add_to_cart, name='add_to_cart'),
    path('remove_from_cart/<int:cart_item_id>/', views.remove_from_cart, name='remove_from_cart'),
    path('', views.view_cart, name='view_cart'),
    path('clear/', views.clear_cart, name='clear_cart'),
    path('update_quantity/<int:cart_item_id>/', views.update_quantity, name='update_quantity'),
]