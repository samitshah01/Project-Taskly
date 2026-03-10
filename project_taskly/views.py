from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_protect
from .models import Users

def index(request):
    return render(request, 'index.html')

def terms(request):
    return render(request, 'pages/terms.html')

def privacy(request):
    return render(request, 'pages/privacy.html')

@csrf_protect
def login(request):
    if request.session.get('user_id'):
        return redirect('index')

    if request.method == 'POST':
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '').strip()
        remember = request.POST.get('remember', False)

        user = Users.objects.filter(email=email).first()
        if not user:
            messages.error(request, 'Email not found.')
            return render(request, 'pages/login.html')

        user_password = user.password or ''

        if check_password(password, user_password):
            request.session.flush()
            request.session['user_id'] = user.id
            request.session['user_email'] = user.email
            request.session['user_role'] = user.role
            request.session['user_name'] = f'{user.first_name} {user.last_name}'.strip()

            request.session.set_expiry(0 if not remember else 60 * 60 * 24 * 7)
            return redirect('dashboard')

        else:
            messages.error(request, 'Invalid password.')

    return render(request, 'pages/login.html')


def logout(request):
    request.session.flush()
    messages.success(request, 'You have been logged out.')
    return redirect('login')

@csrf_protect
def register(request):
    if request.session.get('user_id'):
        return redirect('index')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password = request.POST.get('password', '')
        confirm_password = request.POST.get('confirm_password', '')

        if password != confirm_password:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')

        if Users.objects.filter(email=email).exists():
            messages.warning(request, 'Email already registered. Please login.')
            return redirect('login')

        hashed_password = make_password(password)

        try:
            user = Users.objects.create(
                first_name=first_name,
                last_name=last_name,
                email=email,
                password=hashed_password,
                role='user',
                created_at=timezone.now()
            )
            messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')

        except Exception as e:
            messages.error(request, f'Error creating account: {str(e)}')
            return redirect('register')

    return render(request, 'pages/register.html')

def forgot_password(request):
    return render(request, 'pages/forgot_password.html')

def dashboard(request):
    if not request.session.get('user_id'):
        return redirect('login')

    return render(request, 'pages/dashboard.html')