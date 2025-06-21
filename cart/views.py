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
from notifications.models import Notification

# Create your views here.
@login_required
def item_detail(request, item_id):
    item = get_object_or_404(Items, id=item_id)
    cart, created = Cart.objects.get_or_create(user=request.user)

    # The inbox_unread_count for the navbar should count ALL unread 'new_message' notifications for the user
    inbox_unread_count = Notification.objects.filter(
        user=request.user,
        notification_type='new_message',
        is_read=False
    ).count()

    # notification_count = 0 # Initialize notification count, if you have a notifications app
    # Get unread notification count for navbar (even for this page)
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    
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
        'inbox_unread_count': inbox_unread_count, # For navbar
        'item': item,
        'form': form,
        'related_items': related_items,
        # 'notification_count': notification_count, # For navbar
        'unread_notifications_count': unread_notifications_count, # For navbar
    })



from django.db import transaction, IntegrityError, OperationalError # Import OperationalError
import logging 

logger = logging.getLogger(__name__)


@login_required
def add_to_cart(request, item_id):
    """
    Handles adding an item (with a specific size variant) to the user's cart via AJAX.
    Stock is *not* decremented here; it's validated against total physical stock.
    Stock is decremented/reserved at checkout/order completion.
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

            # --- STOCK VALIDATION AT ADD TO CART (User cannot add more than physically exists in total) ---
            existing_cart_item = CartItem.objects.filter(cart=cart, item=item, size_variant=size_variant).first()
            current_cart_quantity_of_this_item = existing_cart_item.quantity if existing_cart_item else 0
            
            proposed_total_cart_quantity = current_cart_quantity_of_this_item + quantity_to_add

            # Check if adding this quantity would exceed the total available stock on the shelf
            if proposed_total_cart_quantity > size_variant.quantity: # size_variant.quantity is the total physical stock
                logger.warning(f"Proposed quantity {proposed_total_cart_quantity} exceeds physical stock {size_variant.quantity} for item {item_id}, size {size_id}.")
                return JsonResponse({
                    'success': False, 
                    'error': f'Not enough stock for Size {size_variant.size}. Only {size_variant.quantity} physically available.'
                }, status=400)
            # --- END STOCK VALIDATION AT ADD TO CART ---

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
                    
                    # --- REMOVED STOCK DECREMENT HERE ---
                    # size_variant.quantity -= quantity_to_add 
                    # size_variant.save(update_fields=['quantity']) 
                    # Stock is not decremented until actual order completion.
                    # ------------------------------------
                    
                
                # Prepare success_response_data (this part is outside transaction.atomic but inside outer try)
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
                    
                    # --- REMOVED STOCK DECREMENT DURING RECOVERY ---
                    # size_variant.quantity -= quantity_to_add 
                    # size_variant.save(update_fields=['quantity'])
                    # Stock is not decremented until actual order completion.
                    # ---------------------------------------------

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
    Stock is *not* returned here, as it was never decremented on add to cart.
    """
    with transaction.atomic():
        cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)
        
        # --- REMOVED STOCK RETURN HERE ---
        # removed_quantity = cart_item.quantity
        # size_variant_to_update = cart_item.size_variant 
        # if size_variant_to_update:
        #     size_variant_to_update.quantity += removed_quantity
        #     size_variant_to_update.save(update_fields=['quantity']) 
        # --- END REMOVED STOCK RETURN ---

        cart_item.delete()

    messages.success(request, 'Item removed from cart successfully.')
    return redirect('cart:view_cart')


#--- clear cart ---

@login_required
def clear_cart(request):
    """
    Clears all items from the user's cart. Stock is *not* returned here, as it was never decremented on add to cart.
    """
    cart = get_object_or_404(Cart, user=request.user)
    
    with transaction.atomic():
        cart_items_to_clear = list(cart.items.all()) 

        if not cart_items_to_clear:
            logger.info(f"Cart is already empty for user {request.user.username}.")

        for cart_item in cart_items_to_clear:
            # --- REMOVED STOCK RETURN HERE ---
            # size_variant = cart_item.size_variant
            # if size_variant:
            #     size_variant.quantity += cart_item.quantity
            #     size_variant.save(update_fields=['quantity'])
            # --- END REMOVED STOCK RETURN ---
            cart_item.delete() 

    messages.success(request, 'Your cart has been cleared.')
    return redirect('cart:view_cart')


#--- update quantity ---

@login_required
def update_quantity(request, cart_item_id):
    """
    Updates the quantity of a specific item in the cart.
    Includes stock validation to prevent ordering more than physically exists.
    Stock is *not* changed here; it's decremented/reserved at checkout/order completion.
    """
    cart_item = get_object_or_404(CartItem, id=cart_item_id, cart__user=request.user)

    if request.method == 'POST':
        try:
            new_quantity = int(request.POST.get('quantity', 1))
            if new_quantity < 1:
                new_quantity = 1 # Ensure quantity is at least 1

            size_variant = cart_item.size_variant

            # --- STOCK VALIDATION AT UPDATE QUANTITY ---
            # Check if the new_quantity requested exceeds the total physical stock available
            # size_variant.quantity is the total physical stock for this size variant
            if new_quantity > size_variant.quantity: 
                messages.error(request, f"Not enough stock for Size {size_variant.size}. Only {size_variant.quantity} physically available.")
                return redirect('cart:view_cart')
            # --- END STOCK VALIDATION ---

            # Calculate the actual change to apply to inventory (this will no longer affect DB here)
            # Positive value means returning to shelf, negative means taking from shelf
            inventory_change_delta = cart_item.quantity - new_quantity 

            with transaction.atomic():
                cart_item.quantity = new_quantity
                cart_item.save(update_fields=['quantity'])

                # --- REMOVED STOCK CHANGE HERE ---
                # size_variant.quantity += inventory_change_delta 
                # size_variant.save(update_fields=['quantity']) 
                # Stock is not changed until actual order completion.
                # ---------------------------------

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
    """
    Displays the contents of the user's shopping cart,
    and determines if the cart is ready for checkout based on stock.
    """
    cart, created = Cart.objects.get_or_create(user=request.user)
    cart_items = cart.items.all()
    cart_item_count = sum(item.quantity for item in cart_items)
    conversations = Conversation.objects.filter(members__in=[request.user.id])
    conversation_count = conversations.count()
    total_price = sum(ci.quantity * ci.item.price for ci in cart_items) 
    # notification_count = 0 # Initialize notification count, if you have a notifications app
        # Get unread notification count for navbar (even for this page)
    unread_notifications_count = Notification.objects.filter(user=request.user, is_read=False).count()

    # The inbox_unread_count for the navbar should count ALL unread 'new_message' notifications for the user
    inbox_unread_count = Notification.objects.filter(
        user=request.user,
        notification_type='new_message',
        is_read=False
    ).count()

    
    # --- Determine if checkout is possible ---
    can_checkout = True # Assume true until an out-of-stock item is found
    for item_in_cart in cart_items:
        if item_in_cart.quantity > item_in_cart.size_variant.quantity:
            can_checkout = False
            break # No need to check further if one item is OOS
    
    if not cart_items.exists(): # If cart is empty, cannot checkout
        can_checkout = False
    # --- END LOGIC ---

    return render(request, 'cart/view_cart.html', {
        'inbox_unread_count': inbox_unread_count, # For navbar
        'cart': cart, 
        'cart_items': cart_items, 
        'conversation_count': conversation_count, 
        'total_price': total_price, 
        'cart_item_count': cart_item_count,
        'can_checkout': can_checkout, # <--- Pass this new flag to the template
        'unread_notifications_count': unread_notifications_count, # For navbar
        })