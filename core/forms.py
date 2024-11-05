from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm, UserChangeForm, SetPasswordForm
from django.contrib.auth.models import User
from .models import UserProfile

class LoginForm(AuthenticationForm):
    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Your username',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    password = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Enter your password',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))

class SignupForm(UserCreationForm):
    class Meta:
        model = User
        fields = ('username', 'email', 'password1', 'password2',)

    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Your username',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    email = forms.CharField(widget=forms.EmailInput(attrs={
        'placeholder': 'Your email address',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Enter your password',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Enter your password',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))

class UserProfileForm(forms.ModelForm):
    class Meta:
        model = UserProfile
        fields = ['image', 'summary']

class EditProfileForm(UserChangeForm):
    class Meta:
        model = User
        fields = ('username', 'first_name', 'last_name', 'email')

    username = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Your new username',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    
    first_name = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Your new first name',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    
    last_name = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Your new last name',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    
    email = forms.CharField(widget=forms.EmailInput(attrs={
        'placeholder': 'Your new email address',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))

# set password form
class ChangePasswordForm(SetPasswordForm):
    class Meta:
        model = User
        fields = ('new_password1', 'new_password2')
        help_text=( "Your password can’t be too similar to your other personal information. " "Your password must contain at least 8 characters. " "Your password can’t be a commonly used password. " "Your password can’t be entirely numeric." ),
    
    new_password1 = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Enter your new password',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    new_password2 = forms.CharField(widget=forms.PasswordInput(attrs={
        'placeholder': 'Enter your new password again',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))