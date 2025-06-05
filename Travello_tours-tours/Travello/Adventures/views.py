from django.contrib.auth import authenticate, login as auth_login, logout as auth_logout
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .models import Vendor, Create_Tour_Package, Manage_Bills
from .forms import (UserRegForm, VendorRegistrationForm, VendorLoginForm, CreatedPackageForm)
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt
from datetime import date
from django.db.models import Q

# from django.views.decorators import login_required

# Home Page
def home(request):
    return render(request, 'homepage.html')

# About
def about(request):
    return render(request, 'aboutpage.html')

# User registration
def user_reg(request):
    if request.method == 'POST':
        form = UserRegForm(request.POST)
        if form.is_valid():
            form.save()
            messages.success(request, "Registration Successful! Please login.")
            return redirect('login')
        else:
            messages.error(request, "Registration failed. Check the form.")
    else:
        form = UserRegForm()
    return render(request, 'user_reg.html', {'uform': form})
# User login
def login_view(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)

        if user is not None:
            if user.is_superuser:
                messages.error(request, "Admin cannot log in from user login page.", extra_tags='login')
                return redirect('login')
            else:
                auth_login(request, user)
                messages.success(request, "Login Successful!", extra_tags='login')
                return redirect('travel_plan')
        else:
            messages.error(request, "Invalid Username or Password!", extra_tags='login')
            return redirect('login')

    return render(request, 'login.html')
# User dashboard
@csrf_exempt
def travel_plan(request):
    if request.user.is_authenticated:
        return redirect('non_expired_package')
    else:
        messages.error(request, "Please login to access Travel Plan.")
        return redirect('login')

# User logout
def logout_view(request):
    auth_logout(request)
    messages.success(request, "Logged out successfully.")
    return redirect('home')

# Vendor Registration
def vendor_register(request):
    if request.method == 'POST':
        form = VendorRegistrationForm(request.POST)
        if form.is_valid():
            vendor = form.save(commit=False)
            vendor.set_password(form.cleaned_data['password'])
            vendor.save()
            messages.success(request, "Vendor registered successfully! Please log in.")
            return redirect('vendor_login')
    else:
        form = VendorRegistrationForm()
    return render(request, 'vendor_reg.html', {'form': form})

# Vendor Login
def vendor_login(request):
    if request.method == 'POST':
        form = VendorLoginForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password = form.cleaned_data['password']
            try:
                vendor = Vendor.objects.get(username=username)
                if vendor.check_password(password):
                    request.session['vendor_id'] = vendor.id
                    return redirect('ven_addpackage')
                else:
                    messages.error(request, "Invalid password")
            except Vendor.DoesNotExist:
                messages.error(request, "Vendor not found")
    else:
        form = VendorLoginForm()
    return render(request, 'vendor_login.html', {'form': form})

# Vendor Logout
def vendor_logout(request):
    request.session.flush()
    messages.success(request, "Logged out successfully!")
    return redirect('home')

# Add Package (Vendor Only)
def add_package(request):
    if not request.session.get('vendor_id'):
        messages.error(request, "Please login first.")
        return redirect('vendor_login')
    return render(request, 'addpackage.html')

# Vendor login page
def ven_login(request):
    return render(request, 'vendor_login.html')

# Vendor Add Package Page
def ven_addpackage(request):
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        messages.error(request, "Please login first.")
        return redirect('vendor_login')
    vendor = Vendor.objects.get(id=vendor_id)
    return render(request, 'addpackage.html', {'vendor': vendor})

# Combined User/Vendor login POST handler
def ven_user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')

        user = authenticate(request, username=username, password=password)
        if user is not None:
            auth_login(request, user)
            messages.success(request, "User Login Successful!", extra_tags='login')
            return redirect('travel_plan')

        try:
            vendor = Vendor.objects.get(username=username)
            if vendor.check_password(password):
                request.session['vendor_id'] = vendor.id
                messages.success(request, "Vendor Login Successful!", extra_tags='login')
                return redirect('ven_addpackage')
            else:
                messages.error(request, "Invalid Password for Vendor!", extra_tags='login')
        except Vendor.DoesNotExist:
            messages.error(request, "Invalid Credentials!", extra_tags='login')
            
    return render(request, 'user_vendor_login.html')


def uv_login(request):
    return render(request, 'user_vendor_login.html')

def create_package(request):
    if request.method == 'POST':
        form = CreatedPackageForm(request.POST)
        if form.is_valid():
            package = form.save(commit=False)
            vendor = Vendor.objects.get(id=request.session['vendor_id'])
            package.vendor = vendor
            package.save()
            return redirect('success')
    else:
        form = CreatedPackageForm()
    return render(request, 'vendor/create_package.html', {'form': form})

def success(request):
    return render(request, 'success.html')

@csrf_exempt
def non_expired_package(request):
    today = timezone.now().date()
    packages = Create_Tour_Package.objects.filter(
        approved=True,
        auto_expire=True,
        start_date__gt=today
    )
    return render(request, 'travel_plan.html', {
        'first_name': request.user.first_name,
        'last_name': request.user.last_name,
        'packages': packages
    })

def return_to_vendor_dashboard(request):
    return render(request, 'addpackage.html')

@csrf_exempt
def return_to_user_dashboard(request):
    return redirect('travel_plan')

def published_package(request):
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        messages.error(request, "Please login first.")
        return redirect('vendor_login')

    today = timezone.now().date()
    vendor = Vendor.objects.get(id=vendor_id)
    packages = Create_Tour_Package.objects.filter(
        vendor=vendor,
        approved=True,
        auto_expire=True,
        start_date__gt=today
    )
    return render(request, 'vendor/published_package.html', {'packages': packages})

def delete_package(request, package_id):
    today = timezone.now().date()
    package = get_object_or_404(Create_Tour_Package, id=package_id)
    if package.start_date <= today:
        messages.error(request, "You can't delete expired packages.")
        return redirect('published_package')
    package.delete()
    return redirect('published_package')

def edit_package(request, package_id): 
    today = timezone.now().date()
    package = get_object_or_404(Create_Tour_Package, id=package_id)

    if package.start_date <= today:
        messages.error(request, "You can't edit expired packages.")
        return redirect('published_package')

    if request.method == "POST":
        package.package_title = request.POST.get('package_title')
        package.destination = request.POST.get('destination')
        package.place_image = request.POST.get('place_image')
        package.price = request.POST.get('price')
        package.description = request.POST.get('description')
        package.duration = request.POST.get('duration')
        package.start_date = request.POST.get('start_date')
        package.end_date = request.POST.get('end_date')
        package.top_package = request.POST.get('top_package') == 'on'
        package.budget_friendly = request.POST.get('budget_friendly') == 'on'
        package.save()
        return redirect('published_package')

    return render(request, 'vendor/edit_package.html', {'package': package})

def package_details(request, package_id):
    package = get_object_or_404(Create_Tour_Package, id=package_id)
    return render(request, 'user/package_details.html', {'package': package})

def confirm_payment(request, package_id):
    package = get_object_or_404(Create_Tour_Package, id=package_id)

    # Check if the user has already booked this package
    already_booked = Manage_Bills.objects.filter(user=request.user, package=package).exists()
    if already_booked:
         messages.warning(request, "You have already booked this package.")
         return redirect('package_details', package_id=package.id)  # ✅ This sends user back to the package detail page

    # Proceed with booking
    package.booking_count += 1
    package.save()
    Manage_Bills.objects.create(user=request.user, package=package)
    
    messages.success(request, "Booking successful!")
    return render(request, 'user/payment_page.html', {'package': package})

# show bookings of avtive packages userbooking page
def user_bookings(request):
    today = timezone.now().date()
    bookings = Manage_Bills.objects.filter(
        user=request.user,
        package__start_date__gt=today  # only non-expired packages
    ).order_by('-date_booked') 

    return render(request, "user/booked_packages.html", {"bookings": bookings})

def top_packages(request):
    today = timezone.now().date()
    packages = Create_Tour_Package.objects.filter(
        top_package=True,
        auto_expire=True,
        start_date__gt=today
    )
    return render(request, 'user/top_packages.html', {'packages': packages})

def budget_friendly_packages(request):
    today = timezone.now().date()
    packages = Create_Tour_Package.objects.filter(
        budget_friendly=True,
        auto_expire=True,
        start_date__gt=today
    )
    return render(request, 'user/budget_friendly_packages.html', {'packages': packages})

@csrf_exempt
def vendor_package_bookings(request):
    vendor_id = request.session.get('vendor_id')
    if not vendor_id:
        messages.error(request, "Please log in.")
        return redirect('vendor_login')

    today = timezone.now().date()
    vendor = Vendor.objects.get(id=vendor_id)
    packages = Create_Tour_Package.objects.filter(
        vendor=vendor,
        approved=True,
        auto_expire=True,
        start_date__gt=today
    )
    return render(request, 'bookings.html', {
        'packages': packages,
        'vendor': vendor,
    })

def search_packages(request):
    query = request.GET.get('q', '').strip().lower()
    results = []

    if query:
        # Parse numeric value if query includes 'under' and a number
        price_filter = None
        if "under" in query:
            try:
                price_str = query.split("under")[1].strip().split()[0]
                price_filter = float(price_str)
            except (IndexError, ValueError):
                pass  # Ignore if unable to extract number

        # Check flags
        is_top = 'top' in query or 'top package' in query
        is_budget = 'budget' in query or 'budget-friendly' in query

        filters = Q(approved=True, start_date__gt=date.today()) & (
            Q(destination__icontains=query) |
            Q(package_title__icontains=query) |
            Q(description__icontains=query)
        )

        if is_top:
            filters &= Q(top_package=True)
        if is_budget:
            filters &= Q(budget_friendly=True)
        if price_filter is not None:
            filters &= Q(price__lte=price_filter)

        results = Create_Tour_Package.objects.filter(filters)

    return render(request, 'user/search_packages.html', {'results': results, 'query': query})

    query = request.GET.get('q')
    results = []

    if query:
        results = Create_Tour_Package.objects.filter(
            destination__icontains=query,
            approved=True,
            start_date__gt=date.today()
        )

    return render(request, 'user/search_packages.html', {'results': results, 'query': query})