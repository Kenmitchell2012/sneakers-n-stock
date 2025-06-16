from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from items.models import Items
from cart.models import Cart
from .models import Conversation
from .forms import ConversationMessagesForm
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q
from django.db import models
from notifications.models import Notification

# Create your views here.

from django.contrib import messages



@login_required
def new_conversation(request, item_pk):
    item = get_object_or_404(Items, pk=item_pk)

    # --- Prevent user from contacting themselves ---
    if item.created_by == request.user:
        messages.info(request, 'You cannot start a conversation with yourself about your own item.')
        return redirect('item:detail', pk=item_pk) # Redirect back to the item detail page

    # --- Check for existing conversation between THIS BUYER and THIS SELLER for THIS ITEM ---
    # Filter by item and ensure BOTH current user AND item creator are members
    existing_conversations = Conversation.objects.filter(
        item=item
    ).filter(
        members__in=[request.user, item.created_by] # Members must include both
    ).annotate(
        num_members=models.Count('members') # Count members in the conversation
    ).filter(
        num_members=2 # Ensure only conversations with exactly two members (buyer and seller)
    )

    # notification_count = 0 # Initialize notification count, if you have a notifications app
    # Get unread notification count for navbar (even for this page)
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()


    if existing_conversations.exists():
        conversation = existing_conversations.first()
        messages.info(request, 'You already have a conversation about this item.')
        return redirect('conversations:detail', pk=conversation.pk)

    if request.method == 'POST':
        form = ConversationMessagesForm(request.POST)
        if form.is_valid():
            # Create the new conversation instance
            conversation = Conversation.objects.create(item=item)
            conversation.members.add(request.user)
            conversation.members.add(item.created_by)

            # Create the first message for this new conversation
            conversation_message = form.save(commit=False)
            conversation_message.conversation = conversation
            conversation_message.created_by = request.user
            conversation_message.save()

            messages.success(request, 'Your message has been posted and a new conversation has been started.')
            return redirect('conversations:detail', pk=conversation.pk)
    else: # GET request
        form = ConversationMessagesForm()
    
    # Calculate cart item count (for displaying in base template/navbar)
    cart, created_cart = Cart.objects.get_or_create(user=request.user)
    cart_item_count = sum(item_in_cart.quantity for item_in_cart in cart.items.all())

    return render(request, 'conversation/new.html', {
        'form': form, 
        'item': item, # <--- Pass the item object to the template
        'cart_item_count': cart_item_count, # Pass cart item count
        'unread_notifications_count': unread_notifications_count, # For navbar
    })


@login_required
def inbox(request):
    conversations = Conversation.objects.filter(members__in=[request.user.id]).order_by('-updated_at')
    conversation_count = conversations.count()
    # Get the cart item count for the authenticated user
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)
     # notification_count = 0 # Initialize notification count, if you have a notifications app
    # Get unread notification count for navbar (even for this page)
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    return render(request, 'conversation/inbox.html', {
        'conversations': conversations, 
        'conversation_count': conversation_count,
        'cart_item_count': cart_item_count,
        'unread_notifications_count': unread_notifications_count, # For navbar
        })


@login_required
def detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, members__in=[request.user.id])
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()

    # Get the cart item count for the authenticated user
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)

     # notification_count = 0 # Initialize notification count, if you have a notifications app
    # Get unread notification count for navbar (even for this page)
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()


    if request.method == 'POST':
        form = ConversationMessagesForm(request.POST)
        if form.is_valid():
            conversation_message = form.save(commit=False)
            conversation_message.conversation = conversation
            conversation_message.created_by = request.user
            conversation_message.save()
            return redirect('conversations:detail', pk=conversation.pk)
    else:
        form = ConversationMessagesForm()

    return render(request, 'conversation/detail.html', {'conversation': conversation, 'form': form, 'conversation_count': conversation_count, 'cart_item_count': cart_item_count, 'unread_notifications_count': unread_notifications_count,}) # Pass the conversation object to the template



@login_required
def delete(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, members__in=[request.user.id])
    conversation.delete()
    return redirect('conversations:inbox')
