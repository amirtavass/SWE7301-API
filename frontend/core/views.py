# # US-14: Django Website - Basic Views
import requests
import os
from django.http import JsonResponse
from django.shortcuts import render, redirect
from .forms import LoginForm

BACKEND_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:5000")

def index(request):
    """Landing page view"""
    return render(request, 'index.html')


def home(request):
    """Serve the static HTML page"""
    return render(request, 'index.html')


def login_view(request):
    form = LoginForm(request.POST or None)
    error = None

    if request.method == "POST" and form.is_valid():
        email = form.cleaned_data["email"]
        password = form.cleaned_data["password"]
        
        try:
            response = requests.post(f"{BACKEND_URL}/login", json={
                "email": email,
                "password": password
            })
            
            data = response.json()
            if response.status_code == 200:
                if data.get("two_step_required"):
                    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                        return JsonResponse({"two_step_required": True, "email": email})
                    return render(request, "login.html", {"form": form, "two_step_required": True})
                
                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                user_info = data.get("user", {})
                
                # Store tokens and user info in session
                request.session["access_token"] = access_token
                request.session["refresh_token"] = refresh_token
                request.session["username"] = user_info.get("email") # Using email as username in session
                request.session["first_name"] = user_info.get("first_name", "User")
                request.session["user_info"] = user_info
                
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({"success": True, "redirect_url": "/dashboard/"})
                return redirect("dashboard")
            else:
                error = data.get("msg", "Invalid email or password")
                if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                    return JsonResponse({"success": False, "error": error})
        except requests.exceptions.RequestException as e:
            error = f"Backend connection error: {str(e)}"
            if request.headers.get('x-requested-with') == 'XMLHttpRequest':
                return JsonResponse({"success": False, "error": error})

    return render(request, "login.html", {"form": form, "error": error})


def verify_2fa_view(request):
    """AJAX view to verify 2FA code"""
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        email = data.get("email") or data.get("username")
        otp_code = data.get("otp_code")
        
        try:
            response = requests.post(f"{BACKEND_URL}/2fa/verify", json={
                "email": email,
                "otp_code": otp_code
            })
            
            if response.status_code == 200:
                res_data = response.json()
                request.session["access_token"] = res_data.get("access_token")
                request.session["refresh_token"] = res_data.get("refresh_token")
                request.session["username"] = email
                request.session["user_info"] = res_data.get("user")
                return JsonResponse({"success": True, "redirect_url": "/dashboard/"})
            else:
                return JsonResponse({"success": False, "error": "Invalid OTP code"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"status": "error"}, status=405)


def google_login_view(request):
    """
    Redirects to Backend Google Login to start OAuth flow.
    """
    return redirect(f"{BACKEND_URL}/google-login")


def google_callback_view(request):
    """
    Handles callback from Backend after successful Google OAuth.
    Captures tokens from URL parameters and sets session.
    """
    access_token = request.GET.get("access_token")
    refresh_token = request.GET.get("refresh_token")
    email = request.GET.get("email")

    if access_token and refresh_token:
        request.session["access_token"] = access_token
        request.session["refresh_token"] = refresh_token
        request.session["username"] = email 
        request.session["first_name"] = request.GET.get("first_name", "User")
        
        is_2fa = request.GET.get("is_2fa_enabled")
        if is_2fa == "0" or is_2fa == "False" or is_2fa == "false":
             return redirect("setup_2fa")
        
        return redirect("dashboard")
    else:
        return render(request, "login.html", {"error": "Google Login Failed: Missing tokens."})

def setup_2fa_view(request):
    """Render 2FA setup page"""
    access_token = request.session.get("access_token")
    if not access_token:
        return redirect("login")
    
    return render(request, "setup_2fa.html", {
        "backend_url": BACKEND_URL,
        "access_token": access_token
    })

def verify_2fa_setup_view(request):
    """AJAX handler for creating 2FA setup"""
    if request.method == "POST":
        import json
        data = json.loads(request.body)
        otp_code = data.get("otp_code")
        email = request.session.get("username")
        
        try:
            response = requests.post(f"{BACKEND_URL}/2fa/verify", json={
                "email": email,
                "otp_code": otp_code,
                "setup_mode": True
            })
            
            if response.status_code == 200:
                res_data = response.json()
                # Update tokens if refreshed
                request.session["access_token"] = res_data.get("access_token", request.session.get("access_token"))
                return JsonResponse({"success": True, "redirect_url": "/dashboard/"})
            else:
                return JsonResponse({"success": False, "error": "Invalid OTP Code"})
        except Exception as e:
            return JsonResponse({"success": False, "error": str(e)})
    return JsonResponse({"status": "error"}, 405)


def signup_view(request):
    """Handle user signup"""
    error = None

    if request.method == "POST":
        first_name = request.POST.get("first_name")
        last_name = request.POST.get("last_name")
        email = request.POST.get("email")
        password = request.POST.get("password")
        
        try:
            response = requests.post(f"{BACKEND_URL}/signup", json={
                "first_name": first_name,
                "last_name": last_name,
                "email": email,
                "password": password
            })
            
            if response.status_code == 200 or response.status_code == 201:
                # Auto-login to proceed to 2FA setup
                login_res = requests.post(f"{BACKEND_URL}/login", json={
                    "email": email,
                    "password": password
                })
                
                if login_res.status_code == 200:
                    data = login_res.json()
                    request.session["access_token"] = data.get("access_token")
                    request.session["refresh_token"] = data.get("refresh_token")
                    request.session["username"] = email
                    request.session["first_name"] = data.get("user", {}).get("first_name", "User")
                    return redirect("setup_2fa")
                
                return redirect("login")
            else:
                error = response.json().get("message", "Signup failed")
        except requests.exceptions.RequestException as e:
            error = f"Backend connection error: {str(e)}"

    return render(request, "signup.html", {"error": error})


def dashboard(request):
    """Dashboard view protected by session token"""
    access_token = request.session.get("access_token")
    if not access_token:
        return redirect("login")
    
    username = request.session.get("first_name") or request.session.get("username", "User")
    
    products = []
    subscriptions = []
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        # Fetch products
        prod_res = requests.get(f"{BACKEND_URL}/api/products", headers=headers)
        if prod_res.status_code == 200:
            products = prod_res.json()
        
        # Fetch user's subscriptions
        sub_res = requests.get(f"{BACKEND_URL}/api/subscriptions", params={"username": username}, headers=headers)
        if sub_res.status_code == 200:
            subscriptions = sub_res.json()
    except Exception as e:
        print(f"Error fetching dashboard data: {e}")

    return render(request, "dashboard.html", {
        "username": username,
        "products": products,
        "subscriptions": subscriptions,
        "backend_connected": True if (products or subscriptions) else False
    })


def subscriptions(request):
    """Subscriptions view protected by session token"""
    access_token = request.session.get("access_token")
    if not access_token:
        return redirect("login")
    
    username = request.session.get("username", "User")
    
    products = []
    subscriptions = []
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        # Fetch products
        prod_res = requests.get(f"{BACKEND_URL}/api/products", headers=headers)
        if prod_res.status_code == 200:
            products = prod_res.json()
        
        # Fetch user's subscriptions
        sub_res = requests.get(f"{BACKEND_URL}/api/subscriptions", params={"username": username}, headers=headers)
        if sub_res.status_code == 200:
            subscriptions = sub_res.json()
    except Exception as e:
        print(f"Error fetching subscription data: {e}")

    return render(request, "subscriptions.html", {
        "username": username,
        "products": products,
        "subscriptions": subscriptions
    })


def subscribe(request, product_id):
    """Handle product subscription"""
    access_token = request.session.get("access_token")
    if not access_token:
        return redirect("login")
    
    username = request.session.get("username")
    headers = {"Authorization": f"Bearer {access_token}"}
    try:
        requests.post(f"{BACKEND_URL}/api/subscriptions", json={
            "username": username,
            "product_id": product_id
        }, headers=headers)
    except Exception as e:
        print(f"Error subscribing: {e}")
    
    return redirect("dashboard")


def update_token_view(request):
    """Update access token in session - US-16 requirement"""
    if request.method == "POST":
        try:
            import json
            data = json.loads(request.body)
            access_token = data.get("access_token")
            
            if access_token:
                request.session["access_token"] = access_token
                return JsonResponse({"status": "success", "message": "Token updated"})
            else:
                return JsonResponse({"status": "error", "message": "No token provided"}, status=400)
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=500)
    
    return JsonResponse({"status": "error", "message": "Method not allowed"}, status=405)

