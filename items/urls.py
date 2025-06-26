from django.urls import path
from . import views
from django.conf import settings 
from django.conf.urls.static import static

app_name = 'item'

urlpatterns = [
    path('new/', views.new, name='new'),
    path('<int:pk>/delete/', views.delete, name='delete'),
    path('<int:pk>/', views.detail, name='detail'),
    path('<int:pk>/edit/', views.edit, name='edit'),
    path('', views.items, name='items'),
    path('live-search/', views.live_search_items, name='live_search'),
    path('new-arrivals/', views.new_arrivals_list, name='new_arrivals'), # NEW URL for new arrivals page
    path('category/<int:pk>/', views.category_items, name='category_items'),
    path('categories/', views.categories_list, name='categories'), # Lists all categories
    path('categories/<int:pk>/', views.category_items, name='category_items'), # Lists items for a specific category
    

]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    urlpatterns += static(settings.STATIC_URL, document_root=settings.STATIC_ROOT) 