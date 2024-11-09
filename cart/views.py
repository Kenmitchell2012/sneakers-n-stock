from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from items.models import Items 
from .models import Cart, CartItem
from .forms import AddToCartForm
from django.contrib import messages
from conversation.models import Conversation
from django.http import JsonResponse

# Create your views here.
@login_required
def item_detail(request, item_id):
    item = get_object_or_404(Items, id=item_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = AddToCartForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
            cart_item.quantity += quantity
            cart_item.save()
            return redirect('cart:view_cart')
    else:
        form = AddToCartForm()

    related_items = Items.objects.filter(category=item.category).exclude(id=item.id)[:4]  # Adjust as needed

    return render(request, 'item/detail.html', {
        'item': item,
        'form': form,
        'related_items': related_items
    })



@login_required
def add_to_cart(request, item_id):
    item = get_object_or_404(Items, pk=item_id)
    cart, created = Cart.objects.get_or_create(user=request.user)
    
    if request.method == 'POST':
        form = AddToCartForm(request.POST)
        if form.is_valid():
            quantity = form.cleaned_data['quantity']
            cart_item, created = CartItem.objects.get_or_create(cart=cart, item=item)
            if not created:
                cart_item.quantity += quantity
            else:
                cart_item.quantity = quantity
            cart_item.save()
            
            cart_total = sum(ci.quantity * ci.item.price for ci in cart.items.all())
            first_image_url = item.images.first().image.url if item.images.exists() else ''

            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'itemImage': first_image_url,
                    'itemPrice': format(item.price, '.2f'),
                    'cartTotal': format(cart_total, '.2f'),
                })
            else:
                return redirect('cart:view_cart')

    else:
        form = AddToCartForm()
    
    return render(request, 'cart/add_to_cart.html', {'form': form, 'item': item})



# remove from cart

@login_required
def remove_from_cart(request, item_id):
    # Attempt to get the item from the database
    item = get_object_or_404(Items, pk=item_id)
    
    # Get the cart for the current user
    cart = get_object_or_404(Cart, user=request.user)

    # Attempt to get the cart item from the database
    cart_item = get_object_or_404(CartItem, cart=cart, item=item)

    # Delete the cart item
    cart_item.delete()
    messages.success(request, 'Item removed from cart successfully.')

    return redirect('cart:view_cart')  # Redirect to cart view after deletion


@login_required
def clear_cart(request):
    # Get the current user's cart
    cart = get_object_or_404(Cart, user=request.user)

    # Get all cart items associated with the cart
    cart_items = CartItem.objects.filter(cart=cart)

    # Delete all cart items
    cart_items.delete()
    messages.success(request, 'Cart cleared successfully.')

    # Redirect back to the cart view
    return redirect('cart:view_cart')

@login_required
def update_quantity(request, item_id):
    cart_item = get_object_or_404(CartItem, id=item_id, cart__user=request.user)
    if request.method == 'POST':
        quantity = request.POST.get('quantity')
        if quantity and int(quantity) > 0:
            cart_item.quantity = int(quantity)
            cart_item.save()
            messages.success(request, 'Quantity updated successfully.')
    return redirect('cart:view_cart')



@login_required
def view_cart(request):
    # cart = get_object_or_404(Cart, user=request.user)

    # Get the cart item count for the authenticated user
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_item_count = cart.items.count()
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()
    total_price = cart.calculate_total_price()
    return render(request, 'cart/view_cart.html', {
        'cart': cart, 
        'conversation_count': conversation_count, 
        'total_price': total_price, 
        'cart_item_count': cart_item_count,  
        'cart_items': cart})

