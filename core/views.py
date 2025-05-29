from django.db import IntegrityError
from django.shortcuts import render, redirect, resolve_url
from django.urls import reverse
from django.contrib import messages
from django.contrib.auth import authenticate, login, logout
from django.shortcuts import render, get_object_or_404
from django.contrib.auth.decorators import login_required

from django.contrib.auth.models import User
from conversation.models import Conversation
from .forms import SignupForm, EditProfileForm, UserProfileForm, ChangePasswordForm, LoginForm  # Imported UserProfileForm
from payment.forms import ShippingAddressForm
from payment.models import ShippingAddress
from cart.models import Cart
from . models import UserProfile
from items.models import Category, Items

import logging
from django.db import IntegrityError
from django.shortcuts import render, redirect
from .forms import SignupForm

# Set up logging
logger = logging.getLogger(__name__)

# Create your views here.

def index(request):
    if request.user.is_authenticated:
        username = request.user.username
        user = get_object_or_404(User, username=username)
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()

        # Get the cart item count for the authenticated user
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        cart_item_count = sum(item.quantity for item in cart_items)
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
     # Redirect authenticated users away from the signup page
    if request.user.is_authenticated:
        return redirect('core:index')  # Change this to the appropriate page for logged-in users
    
    # If form is submitted, process the form data
    if request.method == 'POST':
        form = SignupForm(request.POST)

        if form.is_valid():
            try:
                user = form.save()  # Only save the User; profile is handled by signals
                return redirect('/login/')
            except IntegrityError as e:
                # Log the specific error details
                logger.error(f"User creation failed for {form.cleaned_data.get('email')}: {e}")
                form.add_error(None, 'An error occurred during account creation. Please try again later.')

    else:
        form = SignupForm()

    return render(request, 'core/signup.html', {'form': form})




def login_user(request):
    # If user is already logged in, immediately redirect to the home page
    if request.user.is_authenticated:
        messages.info(request, "You are already logged in.")
        return redirect('core:index') 

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST) 
        
        if form.is_valid():
            user = form.get_user() 
            login(request, user)
            
            UserProfile.objects.get_or_create(user=user)
            
            messages.success(request, f"Welcome back, {user.username}!")
            
            # --- REVISED REDIRECT LOGIC ---
            # Prioritize 'next' from GET (most common for redirects from decorators)
            # Fallback to 'next' from POST (if hidden in form)
            # Default to LOGIN_REDIRECT_URL from settings.py
            next_url = request.GET.get('next') # Check GET parameters first
            
            if not next_url: # If not found in GET, check POST (less common for redirects)
                next_url = request.POST.get('next')
            
            if not next_url: # If still not found, use the default login redirect URL
                next_url = resolve_url('core:index') # Use resolve_url for robustness

            # --- DEBUGGING PRINTS FOR THIS FINAL ATTEMPT ---
            print(f"\n--- Login Redirect Debug ---")
            print(f"Request.GET.get('next'): {request.GET.get('next')}")
            print(f"Request.POST.get('next'): {request.POST.get('next')}")
            print(f"Final next_url being used: {next_url}")
            print(f"User authenticated: {request.user.is_authenticated}")
            print(f"--- End Login Redirect Debug ---")
            # --- END DEBUGGING PRINTS ---
            
            return redirect(next_url)

        else:
            messages.error(request, 'Invalid username or password. Please try again.')
            return render(request, 'core/login.html', {'form': form})
    else:
        # For GET requests, ensure 'next' parameter is passed to the context for debugging if needed
        form = LoginForm()
        context = {
            'form': form,
        }
        # --- DEBUGGING PRINTS FOR GET REQUEST ---
        print(f"\n--- Login Page GET Debug ---")
        print(f"GET Request next parameter: {request.GET.get('next')}")
        print(f"--- End Login Page GET Debug ---")
        # --- END DEBUGGING PRINTS ---
        return render(request, 'core/login.html', context)

@login_required
def user_profile(request, username):
    user = get_object_or_404(User, username=username)
    UserProfile.objects.get_or_create(user=user)
    
    # Check if the user has any items created by them
    items = Items.objects.filter(created_by=user)

    # Handle conversations
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()

    # Determine if the logged-in user is viewing their own dashboard
    is_owner = request.user == user

    # Cart item count for user
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)

    return render(request, 'core/profile.html', {
        'items': items,
        'user': user,
        'conversation_count': conversation_count,
        'is_owner': is_owner,
        'cart_item_count': cart_item_count,
    })

@login_required
def update_user(request): 
    if request.user.is_authenticated:
        current_user = User.objects.get(id=request.user.id)
        UserProfile.objects.get_or_create(user=current_user)

        # Conversations
        conversations = Conversation.objects.filter(members__in=[request.user.id])
        conversation_count = conversations.count()

        # Retrieve or create the user's shipping address
        shipping_user, created = ShippingAddress.objects.get_or_create(user=current_user)

        # Forms
        user_form = EditProfileForm(request.POST or None, instance=current_user)
        profile_form = UserProfileForm(request.POST, request.FILES, instance=current_user.userprofile)
        shipping_form = ShippingAddressForm(request.POST or None, instance=shipping_user)

        if request.method == 'POST':
            print(user_form.errors)  # Debug: Print user form errors
            print(shipping_form.errors)  # Debug: Print shipping form errors

            if user_form.is_valid() and profile_form.is_valid() and shipping_form.is_valid():
                user_form.save()
                profile_form.save()
                shipping_form.save()
                
                login(request, current_user)
                messages.success(request, 'Your profile has been updated successfully.')
                return redirect('core:index')  # Keep for redirect after successful save

        # Cart item count for user
        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        cart_item_count = sum(item.quantity for item in cart_items)

        return render(request, "core/update_user.html", {
            'user_form': user_form, 
            'profile_form': profile_form,
            'shipping_form': shipping_form, 
            'conversation_count': conversation_count,
            'cart_item_count': cart_item_count,
        })
    
    else:
        messages.error(request, "You must be logged in to access that page!")
        return redirect('home')

def update_password(request):
    if request.user.is_authenticated:
        current_user = request.user

        # Get the cart item count for the authenticated user

        cart, created = Cart.objects.get_or_create(user=request.user)
        cart_items = cart.items.all()
        cart_item_count = sum(item.quantity for item in cart_items)
        # was form filled out
        if request.method == 'POST':
            # do stuff
            form = ChangePasswordForm(current_user, request.POST)
            # check if form is valid and password matches current user's password
            if form.is_valid():
                form.save()
                messages.success(request, 'Your password has been updated successfully. PLease log in again.')
                return redirect('core:login')  # Keep for redirect after successful save
            else:
                messages.error(request, 'Invalid password or new password. Please try again.')
                return render(request, "core/update_password.html", {'form': form},)
        else:
            form = ChangePasswordForm(current_user)
            return render(request, "core/update_password.html", {'form': form, 'cart_item_count': cart_item_count},)
    else:
        messages.success(request, 'You must be logged in to change your password!')
        return redirect('/login/')




def shipping_address(request):
    pass

def logout_user(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('/login/')
