import os
from flask import Blueprint, request, jsonify, redirect, g
import stripe
from app.db import SessionLocal
from app.routes.observation import Product, Subscription

payments_bp = Blueprint('payments', __name__)

# Configure Stripe
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")

@payments_bp.route('/api/create-checkout-session', methods=['POST'])
def create_checkout_session():
    data = request.get_json()
    price_id = data.get('price_id') # We expect the internal product ID or stripe price ID? Let's use internal Product ID logic
    product_id = data.get('product_id') 
    user_email = data.get('user_email')
    
    if not product_id or not user_email:
        return jsonify({"error": "Missing product_id or user_email"}), 400

    db = SessionLocal()
    product = db.get(Product, product_id)
    db.close()
    
    if not product:
        return jsonify({"error": "Product not found"}), 404
        
    if not product.stripe_price_id:
        return jsonify({"error": "This product is not configured for payments"}), 400

    try:
        checkout_session = stripe.checkout.Session.create(
            line_items=[
                {
                    # Provide the exact Price ID (for example, pr_1234) of the product you want to sell
                    'price': product.stripe_price_id,
                    'quantity': 1,
                },
            ],
            mode='subscription',
            success_url='http://127.0.0.1:8000/payment-success?session_id={CHECKOUT_SESSION_ID}',
            cancel_url='http://127.0.0.1:8000/payment-failed',
            customer_email=user_email,
            metadata={
                "product_id": product.id,
                "user_email": user_email
            }
        )
    except Exception as e:
        return jsonify({"error": str(e)}), 500

    return jsonify({"checkout_url": checkout_session.url})

@payments_bp.route('/api/payment/verify-session', methods=['GET'])
def verify_session():
    session_id = request.args.get('session_id')
    if not session_id:
        return jsonify({"error": "Missing session_id"}), 400
        
    try:
        session = stripe.checkout.Session.retrieve(session_id)
        if session.payment_status == 'paid':
             # Reuse the fulfillment logic
             handle_checkout_session(session)
             return jsonify({"status": "verified", "payment_status": "paid"}), 200
        else:
             return jsonify({"status": "pending", "payment_status": session.payment_status}), 200
             
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@payments_bp.route('/stripe_webhook', methods=['POST'])
def webhook():
    event = None
    payload = request.data
    sig_header = request.headers['STRIPE_SIGNATURE']
    webhook_secret = os.getenv('STRIPE_WEBHOOK_SECRET')

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, webhook_secret
        )
    except ValueError as e:
        # Invalid payload
        return jsonify({"error": "Invalid payload"}), 400
    except stripe.error.SignatureVerificationError as e:
        # Invalid signature
        return jsonify({"error": "Invalid signature"}), 400

    # Handle the event
    if event['type'] == 'checkout.session.completed':
        session = event['data']['object']
        handle_checkout_session(session)

    return jsonify({"status": "success"}), 200

def handle_checkout_session(session):
    """
    Fulfill the purchase...
    """
    product_id = session['metadata'].get('product_id')
    user_email = session['metadata'].get('user_email')
    
    if product_id and user_email:
        db = SessionLocal()
        
        # Check if subscription already exists to avoid duplicates
        existing = db.query(Subscription).filter(
            Subscription.user_id == user_email,
            Subscription.product_id == int(product_id)
        ).first()
        
        if not existing:
            new_sub = Subscription(
                user_id=user_email,
                product_id=int(product_id)
            )
            db.add(new_sub)
            db.commit()
            print(f" Created subscription for {user_email} (Product {product_id}) via Stripe")
        
        db.close()
