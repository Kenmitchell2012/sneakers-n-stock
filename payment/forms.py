from django import forms
from .models import ShippingAddress


INPUT_CLASSES = 'w-full py-4 px-6 rounded-xl border'


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
    

class PaymentForm(forms.Form):
    card_name = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Name on Card',
            'class': INPUT_CLASSES,
        }),
        error_messages={'required': ''},
    )

    card_number = forms.CharField(
        widget=forms.NumberInput(attrs={
            'placeholder': 'Card Number',
            'class': INPUT_CLASSES,
        }),
        error_messages={'required': ''},
    )

    card_exp_date = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Exp Date',
            'class': INPUT_CLASSES,
        }),
        error_messages={'required': ''},
    )

    card_cvv = forms.CharField(
        widget=forms.NumberInput(attrs={
            'placeholder': 'CVV',
            'class': INPUT_CLASSES,
        }),
        error_messages={'required': ''},
    )

    card_address1 = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Address',
            'class': INPUT_CLASSES,
        }),
        error_messages={'required': ''},
    )

    card_address2 = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Address (optional)',
            'class': INPUT_CLASSES,
        }),
    )

    card_city = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'City',
            'class': INPUT_CLASSES,
        }),
        error_messages={'required': ''},
    )

    card_state = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'State',
            'class': INPUT_CLASSES,
        }),
        error_messages={'required': ''},
    )

    card_zip_code = forms.CharField(
        widget=forms.NumberInput(attrs={
            'placeholder': 'Zip Code',
            'class': INPUT_CLASSES,
        }),
        error_messages={'required': ''},
    )

    card_country = forms.CharField(
        widget=forms.TextInput(attrs={
            'placeholder': 'Country',
            'class': INPUT_CLASSES,
        }),
        error_messages={'required': ''},
    )

    card_phone_number = forms.CharField(
        widget=forms.NumberInput(attrs={
            'placeholder': 'Phone Number',
            'class': INPUT_CLASSES,
        }),
        error_messages={'required': ''},
    )

