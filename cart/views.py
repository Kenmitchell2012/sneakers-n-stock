from django.shortcuts import render
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from items.models import Items, SizeVariant 
from .models import Cart, CartItem
from .forms import AddToCartForm
from django.contrib import messages
from conversation.models import Conversation
from django.http import JsonResponse
from django.db import transaction

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



from django.db import transaction, IntegrityError, OperationalError # Import OperationalError
import logging 

logger = logging.getLogger(__name__)


@login_required
def add_to_cart(request, item_id):
    """
    Handles adding an item (with a specific size variant) to the user's cart via AJAX.
    If the item and size variant are already in the cart, it increments the quantity.
    Otherwise, it creates a new cart item.
    Also handles real-time stock reduction and database errors.
    """
    item = get_object_or_404(Items, pk=item_id)
    cart, _ = Cart.objects.get_or_create(user=request.user)

    if request.method == 'POST':
        form = AddToCartForm(request.POST)
        if form.is_valid():
            quantity_to_add = form.cleaned_data['quantity']
            size_id = request.POST.get('size') 
            
            try:
                size_variant = get_object_or_404(SizeVariant, id=size_id, item=item)
            except Exception as e:
                logger.error(f"SizeVariant lookup failed for item_id={item_id}, size_id={size_id}. Error: {e}")
                return JsonResponse({'success': False, 'error': 'Invalid size selection or item/size mismatch.'}, status=400)


            if size_variant.quantity < quantity_to_add:
                logger.warning(f"Not enough stock for item {item_id}, size {size_id}. Available: {size_variant.quantity}, Requested: {quantity_to_add}")
                return JsonResponse({
                    'success': False, 
                    'error': f'Not enough stock for Size {size_variant.size}. Available: {size_variant.quantity}'
                }, status=400)

            success_response_data = None 

            try:
                with transaction.atomic():
                    cart_item, created_cart_item = CartItem.objects.get_or_create(
                        cart=cart, 
                        item=item, 
                        size_variant=size_variant, 
                        defaults={'quantity': quantity_to_add} 
                    )

                    if not created_cart_item:
                        cart_item.quantity += quantity_to_add
                        cart_item.save(update_fields=['quantity'])
                    
                    # Decrement the available stock (uncommented as this is desired behavior now)
                    size_variant.quantity -= quantity_to_add 
                    size_variant.save(update_fields=['quantity']) 
                    
                
                # Check for item images before accessing .first().image.url
                first_image_url = ''
                if item.images.exists() and item.images.first().image:
                    first_image_url = item.images.first().image.url

                cart_total = sum(ci.quantity * ci.item.price for ci in cart.items.all())

                success_response_data = {
                    'success': True,
                    'itemImage': first_image_url,
                    'itemPrice': format(item.price, '.2f'),
                    'cartTotal': format(cart_total, '.2f'),
                    'itemSize': size_variant.size,
                    'itemQuantity': quantity_to_add,
                }


            except IntegrityError as e:
                logger.warning(f"IntegrityError (Duplicate CartItem) caught for user {request.user.id}, item {item.id}, size {size_variant.id}. Attempting recovery: {e}")
                try:
                    cart_item = CartItem.objects.get(cart=cart, item=item, size_variant=size_variant)
                    cart_item.quantity += quantity_to_add
                    cart_item.save(update_fields=['quantity'])
                    
                    # Decrement stock during recovery as well
                    size_variant.quantity -= quantity_to_add 
                    size_variant.save(update_fields=['quantity'])

                    # Recalculate success data after successful recovery
                    first_image_url = ''
                    if item.images.exists() and item.images.first().image:
                        first_image_url = item.images.first().image.url

                    cart_total = sum(ci.quantity * ci.item.price for ci in cart.items.all())

                    success_response_data = {
                        'success': True,
                        'itemImage': first_image_url,
                        'itemPrice': format(item.price, '.2f'),
                        'cartTotal': format(cart_total, '.2f'),
                        'itemSize': size_variant.size,
                        'itemQuantity': quantity_to_add,
                    }

                except CartItem.DoesNotExist:
                    logger.error(f"Race condition recovery failed: CartItem not found for user {request.user.id}, item {item.id}, size {size_variant.id}.")
                    return JsonResponse({'success': False, 'error': 'Failed to update existing cart item during race condition.'}, status=500)
                except Exception as ex:
                    logger.error(f"Unexpected error during IntegrityError recovery for user {request.user.id}, item {item.id}, size {size_variant.id}: {ex}")
                    return JsonResponse({'success': False, 'error': 'A database error occurred during recovery. Please try again.'}, status=500)

            except OperationalError as e: 
                logger.warning(f"OperationalError (Database Locked) caught for user {request.user.id}, item {item.id}, size {size_variant.id}: {e}")
                return JsonResponse({'success': False, 'error': 'The database is temporarily busy. Please try again in a moment.'}, status=429)

            except Exception as e: 
                logger.error(f"Critical unexpected error caught for user {request.user.id}, item {item.id}, size {size_variant.id}: {e}")
                return JsonResponse({'success': False, 'error': 'An unexpected server error occurred. Please try again.'}, status=500)

            # --- Final Return ---
            if success_response_data:
                return JsonResponse(success_response_data)
            else:
                logger.error(f"add_to_cart: success_response_data was not set for user {request.user.id}, item {item.id}, size {size_variant.id}.")
                return JsonResponse({'success': False, 'error': 'An internal server error occurred after successful operation.'}, status=500)

    else:
        # For GET requests (e.g., if someone navigates directly to /cart/add/<item_id>)
        form = AddToCartForm() 
        return render(request, 'cart/add_to_cart.html', {'form': form, 'item': item})


#--- remove from cart ---

@login_required
def remove_from_cart(request, cart_item_id):
    """
    Removes a specific item (identified by cart_item_id) from the user's cart.
    Returns the quantity to stock.
    """
    with transaction.atomic():
        # Get the specific CartItem that belongs to the current user's cart
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
        
        # Store the quantity and associated size variant before deleting the cart item.
        removed_quantity = cart_item.quantity
        size_variant_to_update = cart_item.size_variant 

        # Delete the CartItem from the database
        cart_item.delete()

        # Return quantity to stock for the specific size variant
        if size_variant_to_update:
            size_variant_to_update.quantity += removed_quantity
            size_variant_to_update.save(update_fields=['quantity']) 

    messages.success(request, 'Item removed from cart successfully.')
    return redirect('cart:view_cart')


#--- clear cart ---

@login_required
def clear_cart(request):
    """
    Clears all items from the user's cart and returns quantities to stock.
    """
    cart = get_object_or_404(Cart, user=request.user)
    
    with transaction.atomic():
        cart_items_to_clear = list(cart.items.all()) 

        if not cart_items_to_clear:
            logger.info(f"Cart is already empty for user {request.user.username}. No items to return to stock.")

        for cart_item in cart_items_to_clear:
            size_variant = cart_item.size_variant
            
            if size_variant:
                size_variant.quantity += cart_item.quantity 
                size_variant.save(update_fields=['quantity']) 
            else:
                logger.warning(f"CartItem ID {cart_item.id} for user {request.user.username} has no associated SizeVariant. Stock not returned.")
            
            cart_item.delete() 

    messages.success(request, 'Your cart has been cleared.')
    return redirect('cart:view_cart')


#--- update quantity ---

@login_required
def update_quantity(request, cart_item_id):
    """
    Updates the quantity of a specific item in the cart.
    Includes robust stock validation.
    """
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)

    if request.method == 'POST':
        try:
            new_quantity = int(request.POST.get('quantity', 1))
            if new_quantity < 1:
                new_quantity = 1 # Ensure quantity is at least 1

            size_variant = cart_item.size_variant

            # Calculate how many more items the user wants to add to their cart from available stock
            quantity_increase_from_shelf = new_quantity - cart_item.quantity

            # Only perform stock check if the user is trying to increase the cart quantity
            if quantity_increase_from_shelf > 0:
                # If the quantity needed from the shelf (quantity_increase_from_shelf)
                # is greater than the actual stock available on the shelf (size_variant.quantity)
                if quantity_increase_from_shelf > size_variant.quantity:
                    messages.error(request, f"Not enough stock for Size {size_variant.size}. Only {size_variant.quantity} available on shelf to add.")
                    return redirect('cart:view_cart')

            # --- All stock checks passed if we reached here ---

            # Calculate the actual change to apply to inventory (can be positive or negative)
            # Positive value means returning to shelf, negative means taking from shelf
            inventory_change_delta = cart_item.quantity - new_quantity 

            with transaction.atomic():
                cart_item.quantity = new_quantity
                cart_item.save(update_fields=['quantity'])

                size_variant.quantity += inventory_change_delta 
                size_variant.save(update_fields=['quantity']) 

            messages.success(request, 'Cart quantity updated successfully.')
            return redirect('cart:view_cart')

        except ValueError:
            messages.error(request, "Invalid quantity provided.")
        except OperationalError: # Catch database lock errors
            messages.error(request, "Database is temporarily busy. Please try again.")
        except Exception as e: # Catch any other unexpected errors
            logger.error(f"Error updating cart quantity for cart_item_id={cart_item_id}: {e}")
            messages.error(request, "An unexpected error occurred while updating cart.")
            
    return redirect('cart:view_cart')


#--- view cart ---

@login_required
def view_cart(request):
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()
    total_price = sum(ci.quantity * ci.item.price for ci in cart_items) 
    
    return render(request, 'cart/view_cart.html', {
        'cart': cart, 
        'cart_items': cart_items, 
        'conversation_count': conversation_count, 
        'total_price': total_price, 
        'cart_item_count': cart_item_count,  
        })