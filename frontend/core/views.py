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
        username = form.cleaned_data["username"]
        password = form.cleaned_data["password"]
        
        try:
            response = requests.post(f"{BACKEND_URL}/login", json={
                "username": username,
                "password": password
            })
            
            if response.status_code == 200:
                data = response.json()
                access_token = data.get("access_token")
                refresh_token = data.get("refresh_token")
                user_info = data.get("user", {})
                
                # Store tokens and user info in session
                request.session["access_token"] = access_token
                request.session["refresh_token"] = refresh_token
                request.session["username"] = username
                request.session["user_info"] = user_info
                return redirect("dashboard")
            else:
                error = "Invalid username or password"
        except requests.exceptions.RequestException as e:
            error = f"Backend connection error: {str(e)}"

    return render(request, "login.html", {"form": form, "error": error})


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
                # Redirect to login after successful signup
                return redirect("login")
            else:
                error = response.json().get("message", "Signup failed")
        except requests.exceptions.RequestException as e:
            error = f"Backend connection error: {str(e)}"

    return render(request, "signup.html", {"error": error})

<<<<<<< Updated upstream
=======
def verify_email_view(request):
    """Handle email verification"""
    if request.method == "POST":
        try:
            import json
            data = json.loads(request.body)
            
            response = requests.post(f"{BACKEND_URL}/verify-email", json=data)
            
            if response.status_code == 200:
                res_data = response.json()
                # Set session
                request.session["access_token"] = res_data.get("access_token")
                request.session["refresh_token"] = res_data.get("refresh_token")
                user = res_data.get("user", {})
                request.session["username"] = user.get("email")
                request.session["first_name"] = user.get("first_name", "User")
                
                return JsonResponse({"success": True, "redirect_url": "/dashboard/"})
            else:
                return JsonResponse(response.json(), status=response.status_code)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=500)
    return JsonResponse({"error": "Method not allowed"}, status=405)

def observations(request):
    """Observations view protected by session token"""
    access_token = request.session.get("access_token")
    if not access_token:
        return redirect("login")
    
    username = request.session.get("username", "User")
    observations_data = []
    headers = {"Authorization": f"Bearer {access_token}"}
    
    try:
        # Fetching observations from your backend API
        response = requests.get(f"{BACKEND_URL}/api/observations", params={"username": username}, headers=headers)
        if response.status_code == 200:
            observations_data = response.json()
    except Exception as e:
        print(f"Error fetching observations: {e}")

    return render(request, "observations.html", {
        "username": username,
        "observations": observations_data
    })

def satellites(request):
    """View to display satellite constellation status"""
    access_token = request.session.get("access_token")
    if not access_token:
        return redirect("login")
    
    username = request.session.get("username", "User")
    
    # Example data structure - replace with API call later
    satellite_list = [
        {"name": "Sentinel-2A", "status": "Active", "sensor": "MSI", "orbit": "Sun-synchronous", "last_seen": "12 mins ago"},
        {"name": "Sentinel-2B", "status": "Active", "sensor": "MSI", "orbit": "Sun-synchronous", "last_seen": "45 mins ago"},
        {"name": "Landsat-8", "status": "Maintenance", "sensor": "OLI/TIRS", "orbit": "Near-polar", "last_seen": "2 hours ago"},
        {"name": "GeoScope-P1", "status": "Active", "sensor": "SAR", "orbit": "Low Earth", "last_seen": "Just now"},
    ]

    return render(request, "satellites.html", {
        "username": username,
        "satellites": satellite_list
    })
>>>>>>> Stashed changes

def dashboard(request):
    """Dashboard view protected by session token"""
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
        print(f"Error fetching dashboard data: {e}")

    return render(request, "dashboard.html", {
        "username": username,
        "products": products,
        "subscriptions": subscriptions,
        "backend_connected": True if (products or subscriptions) else False
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

