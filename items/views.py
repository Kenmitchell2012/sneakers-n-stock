from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .forms import EditItemForm, NewItemForm
from .models import Items, Category, ItemImage
from cart.models import Cart, CartItem
from cart.forms import AddToCartForm
from .forms import NewItemForm

from conversation.models import Conversation
# Create your views here.

@login_required
def items(request):
    query = request.GET.get('query', '')
    category_id = request.GET.get('category', 0)
    categories = Category.objects.all()
    items = Items.objects.filter(is_sold=False).order_by('-created_at')

    if category_id:
        items = items.filter(category__id=category_id)

    if query:
        items = items.filter(Q(name__icontains=query) | Q(description__icontains=query) | Q(price__icontains=query))

    # Handle conversations
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()

    # cart qty info
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)

    return render(request, 'item/items.html', {
        'items': items,
        'query': query,
        'categories': categories,
        'category_id': int(category_id),
        'conversation_count': conversation_count,
        'cart_item_count': cart_item_count,
        })

@login_required
def detail(request, pk):
    item = get_object_or_404(Items, pk=pk)
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()
    # Get the cart item count for the authenticated user

    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)

    # get the related items for the item being viewed
    related_items = Items.objects.filter(category=item.category, is_sold=False).exclude(pk=pk)[0:5]
    
    if request.method == 'POST':
        form = AddToCartForm(request.POST)
        if form.is_valid():
            cart, created = Cart.objects.get_or_create(user=request.user)
            quantity = form.cleaned_data['quantity']
            cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
            cart_item.quantity += quantity
            cart_item.save()
            return redirect('cart:view_cart')  # Adjust the redirect to your cart view
    else:
        form = AddToCartForm()
    
    context = {
        'item': item,
        'related_items': related_items,
        'conversation_count': conversation_count,
        'form': form,
        'cart_item_count': cart_item_count,
    }
    return render(request, 'item/detail.html', context)


@login_required
def new(request):
    if request.method == 'POST':
        item_form = NewItemForm(request.POST)
        
        if item_form.is_valid():
            item = item_form.save(commit=False)
            item.created_by = request.user
            item.save()

            for image in request.FILES.getlist('images'):
                ItemImage.objects.create(item=item, image=image)

            return redirect('item:detail', pk=item.id)
    else:
        item_form = NewItemForm()
    
    # get conversation count
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()

    # Get the cart item count for the authenticated user
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)

    return render(request, 'item/form.html', {
        'item_form': item_form, 
        'title': 'New Item', 
        'conversation_count': conversation_count,
        'cart_item_count': cart_item_count
        })

@login_required
def edit(request, pk):
    item = get_object_or_404(Items, pk=pk, created_by=request.user)
    # Get the cart item count for the authenticated user
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)
    # get conversation count
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()

    if request.method == 'POST':
        item_form = EditItemForm(request.POST, request.FILES, instance=item)
        
        if item_form.is_valid():
            item_form.save()
            return redirect('item:detail', pk=item.id)
    else:
        item_form = EditItemForm(instance=item)
    return render(request, 'item/form.html', {
        'item_form': item_form,
        'title': 'Edit Item',
        'conversation_count': conversation_count,
        'cart_item_count': cart_item_count,
        },)

@login_required
def delete(request, pk):
    item = get_object_or_404(Items, pk=pk, created_by=request.user)
    item.delete()
    return redirect('core:index')

