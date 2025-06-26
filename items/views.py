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

# --- View to list all categories ---
def categories_list(request):
    """
    Displays a list of all item categories.
    """
    categories = Category.objects.all().order_by('name')

    # Get common navbar context variables
    conversation_count = 0
    cart_item_count = 0
    unread_notifications_count = 0
    inbox_unread_count = 0

    if request.user.is_authenticated:
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item_count = sum(item_in_cart.quantity for item_in_cart in cart.items.all())
        unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
        inbox_unread_count = Notification.objects.filter(
            user=request.user, notification_type='new_message', is_read=False
        ).count()

    context = {
        'categories': categories,
        'conversation_count': conversation_count,
        'cart_item_count': cart_item_count,
        'unread_notifications_count': unread_notifications_count,
        'inbox_unread_count': inbox_unread_count,
    }
    return render(request, 'item/categories_list.html', context)


# --- View to list items for a specific category ---
def category_items(request, pk):
    """
    Displays items belonging to a specific category.
    """
    category = get_object_or_404(Category, pk=pk)
    items = Items.objects.filter(category=category, is_sold=False).order_by('-created_at')

    # Get common navbar context variables
    conversation_count = 0
    cart_item_count = 0
    unread_notifications_count = 0
    inbox_unread_count = 0

    if request.user.is_authenticated:
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item_count = sum(item_in_cart.quantity for item_in_cart in cart.items.all())
        unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()
        inbox_unread_count = Notification.objects.filter(
            user=request.user, notification_type='new_message', is_read=False
        ).count()


    context = {
        'category': category,
        'items': items,
        'conversation_count': conversation_count,
        'cart_item_count': cart_item_count,
        'unread_notifications_count': unread_notifications_count,
        'inbox_unread_count': inbox_unread_count,
    }
    return render(request, 'item/category_items.html', context)

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


    conversation_count = 0
    cart_item_count = 0
    unread_notifications_count = 0 

    # Only fetch user-specific data if the user is authenticated
    if request.user.is_authenticated:
        # Handle conversations
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()
        # Get unread notification count for navbar
        unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

        # The inbox_unread_count for the navbar should count ALL unread 'new_message' notifications for the user
        inbox_unread_count = Notification.objects.filter(
            user=request.user,
            notification_type='new_message',
            is_read=False
        ).count()

        # Cart quantity info
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        cart_item_count = sum(item_in_cart.quantity for item_in_cart in cart_items) # Use item_in_cart for clarity


    return render(request, 'item/items.html', {
        "inbox_unread_count": inbox_unread_count, # Pass this for the navbar
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

def new_arrivals_list(request):
    """
    Displays a list of new arrival items, adapted from the old homepage content.
    """
    # Initialize variables for authenticated-only data, so they always exist in context
    conversation_count = 0
    cart_item_count = 0
    unread_notifications_count = 0
    inbox_unread_count = 0

    if request.user.is_authenticated:
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()

        inbox_unread_count = Notification.objects.filter(
            user=request.user,
            notification_type='new_message',
            is_read=False
        ).count()

        unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item_count = sum(item_in_cart.quantity for item_in_cart in cart.items.all())

    # This view's primary content is the new arrivals
    items = Items.objects.filter(is_sold=False).order_by('-created_at') # Fetch all new arrivals

    context = {
        'items': items, # The new arrivals items
        'conversation_count': conversation_count,
        'cart_item_count': cart_item_count,
        'unread_notifications_count': unread_notifications_count,
        'inbox_unread_count': inbox_unread_count,
    }
    return render(request, 'item/new_arrivals.html', context)



def detail(request, pk):
    item = get_object_or_404(Items, pk=pk)

    # Initialize variables for authenticated-only data, so they always exist in context
    conversation_count = 0
    cart_item_count = 0
    unread_notifications_count = 0  # Initialize for all cases
    inbox_unread_count = 0          # Initialize for all cases

    form = AddToCartForm() # Initialize form for GET request (and unauthenticated users)

    # Only fetch user-specific data if the user is authenticated
    if request.user.is_authenticated:
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()

        # The inbox_unread_count for the navbar should count ALL unread 'new_message' notifications for the user
        inbox_unread_count = Notification.objects.filter(
            user=request.user,
            notification_type='new_message',
            is_read=False
        ).count()

        # Get unread notification count for navbar
        unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

        # Get the cart and its item count for the authenticated user
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        cart_item_count = sum(item_in_cart.quantity for item_in_cart in cart_items) # Use a different loop var name here (item_in_cart)

    # get the related items for the item being viewed
    related_items = Items.objects.filter(category=item.category, is_sold=False).exclude(pk=pk)[:5] # Limit to 5 related items

    context = {
        'inbox_unread_count': inbox_unread_count, # Pass this for the navbar
        'cart_item_count': cart_item_count, # For navbar
        'item': item,
        'related_items': related_items,
        'conversation_count': conversation_count,
        'form': form, # This form will be for AddToCart, regardless of login status
        # 'cart_item_count' is already in context once, no need to repeat
        'unread_notifications_count': unread_notifications_count, # For navbar
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

