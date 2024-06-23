from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required

from .forms import EditItemForm, NewItemForm
from .models import Items
# Create your views here.




def items(request):
    items = Items.objects.filter(is_sold=False)
    return render(request, 'item/items.html', {'items': items})


def detail(request, pk):
    item = get_object_or_404(Items, pk=pk)
    related_items = Items.objects.filter(category=item.category, is_sold=False).exclude(pk=pk)[0:5]
    return render(request, 'item/detail.html', {'items': item, 'related_items': related_items})


@login_required
def new(request):
    if request.method == 'POST':
        form = NewItemForm(request.POST, request.FILES)
        
        if form.is_valid():
            item = form.save(commit=False)
            item.created_by = request.user
            item.save()
            return redirect('item:detail', pk=item.id)
    else:
        form = NewItemForm
    return render(request, 'item/form.html', {'form': form,'title': 'New Item'},)

@login_required
def edit(request, pk):
    item = get_object_or_404(Items, pk=pk, created_by=request.user)
    if request.method == 'POST':
        form = EditItemForm(request.POST, request.FILES, instance=item)
        
        if form.is_valid():
            form.save()
            return redirect('item:detail', pk=item.id)
    else:
        form = EditItemForm(instance=item)
    return render(request, 'item/form.html', {'form': form,'title': 'Edit Item'},)

@login_required
def delete(request, pk):
    item = get_object_or_404(Items, pk=pk, created_by=request.user)
    item.delete()
    return redirect('core:index')

