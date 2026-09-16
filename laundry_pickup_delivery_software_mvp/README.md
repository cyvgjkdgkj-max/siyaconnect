# Laundry Pickup & Delivery MVP

A simple web app for a laundry collection/delivery business.

## Included
- Customer order form
- Automatic order number
- Pickup date and time
- Customer contact/address
- Service selection
- Estimated weight and price
- Payment method field
- Order tracking page
- Printable collection/order slip
- Admin order dashboard
- Order status updates
- SQLite database
- JSON API endpoint for future mobile app integrations

## Run locally

1. Install Python 3.
2. Open a terminal in this folder.
3. Install packages:

    pip install -r requirements.txt

4. Start the app:

    python app.py

5. Open:

    http://127.0.0.1:5000

## Admin

Open:

    http://127.0.0.1:5000/admin

Default admin key:

    admin123

Change this before going live by setting an environment variable:

    ADMIN_KEY=your-secure-key

Also set:

    SECRET_KEY=your-random-secret

## Important for real business use

This MVP is intentionally simple. Before accepting real customer payments or sensitive customer information, add:
- HTTPS
- secure authentication
- backups
- a production database
- payment gateway integration
- driver accounts
- customer notifications
- proper privacy policy and terms
- business-specific pricing rules

The app can be expanded without rebuilding it from scratch.
pip install -r requirements.txt