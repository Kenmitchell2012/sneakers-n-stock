from django.shortcuts import render, get_object_or_404
from .models import Items
# Create your views here.

def detail(request, pk):
    item = get_object_or_404(Items, pk=pk)
    related_items = Items.objects.filter(category=item.category, is_sold=False).exclude(pk=pk)[0:5]
    return render(request, 'item/detail.html', {'items': item, 'related_items': related_items})
