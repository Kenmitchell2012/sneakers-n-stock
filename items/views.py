from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.db.models import Q
from .forms import EditItemForm, NewItemForm
from .models import Items, Category, ItemImage
from cart.models import Cart, CartItem
from cart.forms import AddToCartForm
from .forms import NewItemForm
from django.http import JsonResponse
from django.urls import reverse
from django.templatetags.static import static
from notifications.models import Notification

from conversation.models import Conversation
# Create your views here.

import logging
logger = logging.getLogger(__name__)

def items(request):
    query = request.GET.get('query', '')
    category_id = request.GET.get('category', 0)
    categories = Category.objects.all()
    items = Items.objects.filter(is_sold=False).order_by('-created_at')

    if category_id:
        items = items.filter(category__id=category_id)

    if query:
        # Use Q objects to build complex OR queries
        items = items.filter(
            Q(name__icontains=query) | 
            Q(description__icontains=query) | 
            Q(price__icontains=query) # Note: price__icontains might behave unexpectedly for non-numeric queries
        )

    # --- NEW LOGIC: Initialize user-specific data to default values for guests ---
    conversation_count = 0
    cart_item_count = 0

    # notification_count = 0 # Initialize notification count, if you have a notifications app
    # Get unread notification count for navbar (even for this page)
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()


    # Only fetch user-specific data if the user is authenticated
    if request.user.is_authenticated:
        # Handle conversations
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()

        # Cart quantity info
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        cart_item_count = sum(item_in_cart.quantity for item_in_cart in cart_items) # Use item_in_cart for clarity
    # --- END NEW LOGIC ---

    return render(request, 'item/items.html', {
        'items': items,
        'query': query,
        'categories': categories,
        'category_id': int(category_id),
        'conversation_count': conversation_count, # Will be 0 for guests, actual count for logged-in
        'cart_item_count': cart_item_count,       # Will be 0 for guests, actual count for logged-in
        'unread_notifications_count': unread_notifications_count, # For navbar
        })

# --- Live Search API Endpoint ---
def live_search_items(request):
    query = request.GET.get('query', '').strip() # Get search query, strip whitespace
    results = []

    if query:
        # Perform the same search logic as your main items view
        # Filter by name or description
        search_results = Items.objects.filter(is_sold=False).filter(
            Q(name__icontains=query) | Q(description__icontains=query)
        ).order_by('name')[:5] # Limit results for autocomplete performance (e.g., top 5)

        for item in search_results:
            # Prepare data for JSON response
            item_data = {
                'id': item.id,
                'name': item.name,
                'price': float(item.price), # Convert Decimal to float for JSON
                'url': reverse('item:detail', args=[item.id]), # Generate detail URL
                'image_url': '',
            }
            # Add first image URL if available
            if item.images.exists() and item.images.first().image:
                item_data['image_url'] = request.build_absolute_uri(item.images.first().image.url)
            else:
                item_data['image_url'] = request.build_absolute_uri(static('media/item_images/images.png')) # Default image

            results.append(item_data)
    
    return JsonResponse(results, safe=False) # safe=False allows non-dict objects (like lists) to be returned
# --- END LIVE SEARCH VIEW ---



def detail(request, pk):
    item = get_object_or_404(Items, pk=pk)
    
    # Initialize variables for authenticated-only data
    conversation_count = 0
    cart_item_count = 0
    form = AddToCartForm() # Initialize form for GET request (and unauthenticated users)
    # notification_count = 0 # Initialize notification count, if you have a notifications app
        # Get unread notification count for navbar (even for this page)
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()


    # Only fetch user-specific data if the user is authenticated
    if request.user.is_authenticated:
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()

        # Get the cart and its item count for the authenticated user
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        cart_item_count = sum(item_in_cart.quantity for item_in_cart in cart_items) # Use a different loop var name here (item_in_cart)

        # If a POST request comes in for Add to Cart, it will be handled by the @login_required add_to_cart view
        # The form is rendered here, but its action goes to cart:add_to_cart
        # So, we can just initialize the form here.
        
    # get the related items for the item being viewed
    related_items = Items.objects.filter(category=item.category, is_sold=False).exclude(pk=pk)[:5] # Limit to 5 related items
    
    # If the user is not authenticated, the form will still be rendered, but it won't be used for adding to cart
    context = {
        'item': item,
        'related_items': related_items,
        'conversation_count': conversation_count,
        'form': form, # This form will be for AddToCart, regardless of login status
        'cart_item_count': cart_item_count,
        'unread_notifications_count': unread_notifications_count, # For navbar
        # 'is_authenticated': request.user.is_authenticated, # Can pass this to template for explicit checks
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

