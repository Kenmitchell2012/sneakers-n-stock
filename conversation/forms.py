from django import forms

from .models import ConversationMessages

class ConversationMessagesForm(forms.ModelForm):
    class Meta:
        model = ConversationMessages
        fields = ('content',)
        widgets = {
            'content': forms.Textarea(attrs={
                'class': 'w-full py-4 px-6 rounded-xl border',
                'placeholder': 'Type your message here',
                'rows': 5,
            })
        }

        
