from django.db import models
from items.models import Items
from django.contrib.auth.models import User
# Create your models here.

class Conversation(models.Model):
    item = models.ForeignKey(Items, related_name='conversations', on_delete=models.CASCADE)
    members = models.ManyToManyField(User, related_name='conversations')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ('updated_at',)

    def __str__(self):
        # conversation about item: {self.item.name} with members: {', '.join([member.username for member in self.members.all()])}"
        return f"Conversation about {self.item.name} with members: {', '.join([member.username for member in self.members.all()])}"
    

class ConversationMessages(models.Model):
    conversation = models.ForeignKey(Conversation, related_name='messages', on_delete=models.CASCADE)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, related_name='messages', on_delete=models.CASCADE)


