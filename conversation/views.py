from django.shortcuts import render
from django.contrib.auth.decorators import login_required
from items.models import Items
from .models import Conversation
from .forms import ConversationMessagesForm
from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.

from django.contrib import messages



@login_required
def new_conversation(request, item_pk):
    item = get_object_or_404(Items, pk=item_pk)

    if item.created_by == request.user:
        messages.info(request, 'You cannot start a conversation with yourself.')
        return redirect('conversations:detail', pk=conversations.first().id)
    
    conversations = Conversation.objects.filter(item=item).filter(members__in=[request.user.id])
    if conversations.exists():
        conversation = conversations.first()
        messages.info(request, 'You already have a conversation about this item.')
        return redirect('conversations:detail', pk=conversation.pk)

    if request.method == 'POST':
        form = ConversationMessagesForm(request.POST)
        if form.is_valid():
            conversation = Conversation.objects.create(item=item)
            conversation.members.add(request.user)
            conversation.members.add(item.created_by)
            conversation.save()

            conversation_message = form.save(commit=False)
            conversation_message.conversation = conversation
            conversation_message.created_by = request.user
            conversation_message.save()

            messages.success(request, 'Your message has been posted and a new conversation has been started.')
            return redirect('conversations:detail', pk=conversation.pk)
    else:
        form = ConversationMessagesForm()
    
    return render(request, 'conversation/new.html', {'form': form})



@login_required
def inbox(request):
    conversations = Conversation.objects.filter(members__in=[request.user.id]).order_by('-updated_at')
    conversation_count = conversations.count()
    return render(request, 'conversation/inbox.html', {'conversations': conversations, 'conversation_count': conversation_count})


@login_required
def detail(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, members__in=[request.user.id])
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()

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

    return render(request, 'conversation/detail.html', {'conversation': conversation, 'form': form, 'conversation_count': conversation_count})



@login_required
def delete(request, pk):
    conversation = get_object_or_404(Conversation, pk=pk, members__in=[request.user.id])
    conversation.delete()
    return redirect('conversations:inbox')
