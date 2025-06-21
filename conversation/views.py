from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from items.models import Items
from cart.models import Cart
from .models import Conversation
from .forms import ConversationMessagesForm
from django.shortcuts import render, get_object_or_404, redirect
from django.db.models import Q, Count, Case, When, BooleanField
from django.db import models
from notifications.models import Notification

# Create your views here.

from django.contrib import messages



@login_required
def new_conversation(request, item_pk):
    # ... (no changes here from previous turn) ...
    item = get_object_or_404(Items, pk=item_pk)

    if item.created_by == request.user:
        messages.info(request, 'You cannot start a conversation with yourself about your own item.')
        return redirect('item:detail', pk=item_pk)

    existing_conversations = Conversation.objects.filter(
        item=item
    ).filter(
        members__in=[request.user, item.created_by]
    ).annotate(
        num_members=Count('members')
    ).filter(
        num_members=2
    )

    cart, created_cart = Cart.objects.get_or_create(user=request.user)
    cart_item_count = sum(item_in_cart.quantity for item_in_cart in cart.items.all())
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()


    if existing_conversations.exists():
        conversation = existing_conversations.first()
        messages.info(request, 'You already have a conversation about this item.')
        return redirect('conversations:detail', pk=conversation.pk)

    if request.method == 'POST':
        form = ConversationMessagesForm(request.POST)
        if form.is_valid():
            conversation = Conversation.objects.create(item=item)
            conversation.members.add(request.user)
            conversation.members.add(item.created_by)

            conversation_message = form.save(commit=False)
            conversation_message.conversation = conversation
            conversation_message.created_by = request.user
            conversation_message.save()

            other_member = item.created_by
            Notification.objects.create(
                user=other_member,
                content=f"You have a new message from {request.user.username} about '{item.name}'.",
                notification_type='new_message',
                conversation=conversation # Ensure this is passed
            )

            messages.success(request, 'Your message has been posted and a new conversation has been started.')
            return redirect('conversations:detail', pk=conversation.pk)
    else:
        form = ConversationMessagesForm()

    return render(request, 'conversation/new.html', {
        'form': form,
        'item': item,
        'cart_item_count': cart_item_count,
        'unread_notifications_count': unread_notifications_count,
    })


@login_required
def inbox(request):
    # Retrieve conversations and annotate with unread message count for the current user
    conversations = Conversation.objects.filter(members__in=[request.user.id]).order_by('-updated_at')

    # This annotation counts how many 'new_message' notifications exist for this conversation
    # that are targeted to the current user and are not read.
    conversations = conversations.annotate(
        # unread_messages_count = Count(
        #     'notifications', # This assumes related_name='notifications' from Notification.conversation
        #     filter=Q(notifications__user=request.user, notifications__notification_type='new_message', notifications__is_read=False)
        # ),
        # A simpler way using a boolean annotation (is_unread_for_user)
        # This checks if there is *at least one* unread 'new_message' notification
        # for this conversation targeted at the current user.
        is_unread_for_user=Case(
            When(
                notifications__user=request.user,
                notifications__notification_type='new_message',
                notifications__is_read=False,
                then=True
            ),
            default=False,
            output_field=BooleanField()
        )
    ).distinct() # Use distinct() to avoid duplicate conversations if there are multiple notifications

    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)

    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    # The inbox_unread_count for the navbar should count ALL unread 'new_message' notifications for the user
    inbox_unread_count = Notification.objects.filter(
        user=request.user,
        notification_type='new_message',
        is_read=False
    ).count()


    return render(request, 'conversation/inbox.html', {
        'conversations': conversations,
        'conversation_count': conversations.count(), # Total count of conversations for display
        'cart_item_count': cart_item_count,
        'unread_notifications_count': unread_notifications_count,
        'inbox_unread_count': inbox_unread_count, # Pass this for the navbar
    })


@login_required
def detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, members__in=[request.user.id])

    # --- NEW: Mark all 'new_message' notifications for THIS conversation as read for the current user ---
    # This also applies if a notification was about this conversation
    Notification.objects.filter(
        user=request.user,
        notification_type='new_message',
        conversation=conversation, # Filter by the current conversation
        is_read=False
    ).update(is_read=True)
    # --- END NEW ---

    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()

    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)

    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()


    if request.method == 'POST':
        form = ConversationMessagesForm(request.POST)
        if form.is_valid():
            conversation_message = form.save(commit=False)
            conversation_message.conversation = conversation
            conversation_message.created_by = request.user
            conversation_message.save()

            # Send notification to the other member
            other_member = conversation.members.exclude(id=request.user.id).first()
            if other_member:
                Notification.objects.create(
                    user=other_member,
                    content=f"You have a new message from {request.user.username} in conversation about '{conversation.item.name}'.",
                    notification_type='new_message',
                    conversation=conversation # Ensure this is passed
                )
            messages.success(request, 'Your message has been sent.')
            # Redirect to the same detail page to display the new message
            return redirect('conversations:detail', pk=conversation.pk)
    else:
        form = ConversationMessagesForm()

    return render(request, 'conversation/detail.html', {
        'conversation': conversation,
        'form': form,
        'conversation_count': conversation_count,
        'cart_item_count': cart_item_count,
        'unread_notifications_count': unread_notifications_count,
    })



@login_required
def delete(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, members__in=[request.user.id])
    conversation.delete()
    messages.success(request, 'Conversation deleted.') # Optional success message
    return redirect('conversations:inbox')
