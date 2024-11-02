from django.urls import path
from django.contrib.auth import views as auth_views

from . import views
from .forms import LoginForm

app_name = 'core'

urlpatterns = [
    path('', views.index, name='index'),
    path('contact/', views.contact, name='contact'),
    path('signup/', views.signup, name='signup'),
    path('login/', auth_views.LoginView.as_view(template_name='core/login.html', authentication_form=LoginForm), name='login'),
    path('logout/', views.logout_user, name= 'logout_user' ),
    path('profile/<str:username>/', views.user_profile, name='user_profile'),
    path('update_user/', views.update_user, name='update_user'),
    path('update_password/', views.update_user, name='update_password'),
    path('shipping_address/', views.shipping_address, name='shipping_address'),
    

]