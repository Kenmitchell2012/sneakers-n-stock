from django.shortcuts import render, redirect
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, get_object_or_404

from django.contrib.auth.models import User


from conversation.models import Conversation

from .forms import SignupForm, EditProfileForm
from payment.forms import ShippingAddressForm

from payment.models import ShippingAddress

from cart.models import Cart

from items.models import Category, Items
# Create your views here.

def index(request):
    if request.user.is_authenticated:
        username = request.user.username
        user = get_object_or_404(User, username=username)
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()

        # Get the cart item count for the authenticated user
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item_count = cart.items.count()
    else:
        user = None
        conversation_count = 0
        cart_item_count = 0

    items = Items.objects.filter(is_sold=False).order_by('-created_at')[0:6]
    categories = Category.objects.all()
    items = Items.objects.filter(is_sold=False).order_by('-created_at')

    return render(request, 'core/index.html', {
        'items': items,
        'categories': categories,
        'conversation_count': conversation_count,
        'user': user,
        'cart_item_count': cart_item_count,
    })

def contact(request):
    return render(request, 'core/contact.html')

def signup(request):
    if request.method == 'POST':
        form = SignupForm(request.POST)

        if form.is_valid():
            form.save()

            return redirect('/login/')
    else:
        form = SignupForm()

    return render(request, 'core/signup.html', {'form':form})

def user_profile(request):
    pass

def update_user(request):
    if request.user.is_authenticated:
        # Get the current user
        current_user = User.objects.get(id=request.user.id)

        # handle conversations
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()

        # Try to retrieve the user's shipping address or initialize a new instance if not found
        try:
            shipping_user = ShippingAddress.objects.get(user=current_user)
        except ShippingAddress.DoesNotExist:
            shipping_user = ShippingAddress(user=current_user)  # Create a new instance for the user

        # Get the user's edit form and shipping address edit form
        user_form = EditProfileForm(request.POST or None, instance=current_user)
        shipping_form = ShippingAddressForm(request.POST or None, instance=shipping_user)

        if user_form.is_valid() and shipping_form.is_valid():
            user_form.save()
            shipping_form.save()  # Save the shipping address

            login(request, current_user)
            messages.success(request, 'Your profile has been updated successfully.')
            return redirect('core:index')

        # Get the cart item count for the authenticated user
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_item_count = cart.items.count()
        
        return render(request, "core/update_user.html", {
            'user_form': user_form, 
            'shipping_form': shipping_form, 
            'conversation_count': conversation_count,
            'cart_item_count': cart_item_count,
            })
    
    else:
        messages.error(request, "You must be logged in to access that page!")
        return redirect('home')


def shipping_address(request):
    pass

def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('/login/')