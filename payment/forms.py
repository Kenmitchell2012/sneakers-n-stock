from django import forms
from .models import ShippingAddress

class ShippingAddressForm(forms.ModelForm):
    class Meta:
        model = ShippingAddress
        fields = ('shipping_full_name', 'shipping_email', 'shipping_address', 'shipping_city', 'shipping_state', 'shipping_zip_code', 'shipping_country', 'shipping_phone_number')

    shipping_full_name = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Full Name',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    
    shipping_email = forms.CharField(widget=forms.EmailInput(attrs={
        'placeholder': 'Email address',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    
    shipping_address = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Address',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    
    shipping_city = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'City',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    
    shipping_state = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'State',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    
    shipping_zip_code = forms.CharField(widget=forms.NumberInput(attrs={
        'placeholder': 'Zip Code',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    
    shipping_phone_number = forms.CharField(widget=forms.NumberInput(attrs={
        'placeholder': 'Phone Number',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))
    
    shipping_country = forms.CharField(widget=forms.TextInput(attrs={
        'placeholder': 'Country',
        'class': 'w-full py-4 px-6 rounded-xl',
        }))