from django.shortcuts import render

from items.models import Category, Items
# Create your views here.

def index(request):
    items = Items.objects.filter(is_sold=False)[0:6]
    categories = Category.objects.all()
    return render(request, 'core/index.html', {'items':items, 'categories':categories,})

def contact(request):
    return render(request, 'core/contact.html')