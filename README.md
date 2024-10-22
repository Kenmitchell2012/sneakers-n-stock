# Sneaker Marketplace

## Project Overview

The Sneaker Marketplace is a web application built with **HTML**, **Bootstrap**, **Django**, and **Python** that allows users to buy, sell, and interact with other sneaker enthusiasts. Users can create profiles, post sneakers for sale, chat with sellers or buyers, and make purchases through the admin-operated store.

## Features

- **User Profiles**: Sign up, create a profile, and manage your sneaker listings.
- **Post Sneakers**: Upload sneakers for sale, including images, prices, and descriptions.
- **Buy Sneakers**: Browse listings from other users and purchase your favorite sneakers.
- **Admin Store**: Purchase sneakers directly from the admin-operated store.
- **Chat**: Message sellers or buyers to negotiate and discuss sneaker deals in real-time.
- **Responsive Design**: Optimized for both desktop and mobile users using Bootstrap.

## Technologies Used

- **HTML5**: Markup for structuring the web pages.
- **Bootstrap**: Responsive design and styling framework.
- **Django**: Backend web framework for handling server-side logic.
- **Python**: Programming language for backend development and database interactions.
- **SQLite**: Default database used by Django for storing user and product data.

## Installation and Setup

1. Clone the repository:
   ```bash
   git clone https://github.com/yourusername/sneaker-marketplace.git
   cd sneaker-marketplace
   ```

2. Create a virtual environment and install the dependencies:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   pip install -r requirements.txt
   ```

3. Apply migrations to set up the database:
   ```bash
   python manage.py migrate
   ```

4. Run the Django development server:
   ```bash
   python manage.py runserver
   ```

5. Open your browser and go to:
   ```
   http://127.0.0.1:8000
   ```

## Features Breakdown

- **User Registration**: Create and manage a user account.
- **Admin Store**: View sneakers sold directly by the admin.
- **Sneaker Listings**: Post your sneakers for sale with descriptions, images, and prices.
- **Chat System**: Real-time messaging between buyers and sellers.
- **Shopping Cart**: Add sneakers to your cart and proceed to checkout.

## Future Enhancements

- **Wishlist**: Save sneakers for later.
- **Payment Integration**: Implement Stripe or PayPal for secure payments.
- **Search and Filtering**: Advanced search options by size, brand, and price.
- **Order Tracking**: Track sneaker orders after purchase.
