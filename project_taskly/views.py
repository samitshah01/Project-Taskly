import re
import json
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import csrf_protect
from .models import Users
from django.http import JsonResponse
from .utils import create_and_send_otp, verify_otp, mask_email
from django.contrib.auth.hashers import make_password
from django.views.decorators.http import require_POST
import logging

logger = logging.getLogger(__name__)

@require_POST
def set_timezone(request):
    try:
        data = json.loads(request.body)
        tz_name = data.get("timezone", "").strip()

        if tz_name:
            request.session["user_timezone"] = tz_name
            return JsonResponse({"status": "ok", "timezone": tz_name})

        return JsonResponse({"status": "error", "message": "Timezone missing"}, status=400)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)

def index(request):
    return render(request, 'index.html')


def terms(request):
    return render(request, 'pages/terms.html')


def privacy(request):
    return render(request, 'pages/privacy.html')


@csrf_protect
def login(request):
    if request.session.get('user_id'):
        return redirect('dashboard')

    if request.method == 'POST':
        identifier = request.POST.get('identifier', '').strip()
        password = request.POST.get('password', '').strip()
        remember = request.POST.get('remember', False)

        user = Users.objects.filter(email__iexact=identifier).first() or Users.objects.filter(username__iexact=identifier).first()

        logger.info(f"Login attempt for identifier={identifier}")

        if not user:
            logger.warning(f"Login failed - user not found: {identifier}")
            messages.error(request, 'User not found.')
            return render(request, 'pages/login.html')

        user_password = user.password or ''

        if check_password(password, user_password):
            request.session.flush()

            logger.info(f"User logged in successfully: user_id={user.id}")

            request.session['user_id'] = user.id
            request.session['user_email'] = user.email
            request.session['user_role'] = user.role
            request.session['user_full_name'] = f"{user.first_name or ''} {user.last_name or ''}".strip()
            request.session['user_username'] = user.username

            request.session.set_expiry(0 if not remember else 60 * 60 * 24 * 30)

            messages.success(request, 'Successfully Logged In.')
            return redirect('dashboard')
        else:
            logger.warning(f"Invalid password attempt for user: {identifier}")
            messages.error(request, 'Invalid password.')

    return render(request, 'pages/login.html')


def logout(request):
    request.session.flush()
    messages.success(request, 'You have been logged out.')
    return redirect('login')

def check_username(request):
    username = request.GET.get('username', '').strip()
    if not username:
        return JsonResponse({'available': False, 'message': 'Username cannot be empty'})

    exists = Users.objects.filter(username__iexact=username).exists()
    return JsonResponse({
        'available': not exists,
        'message': 'Username available' if not exists else 'Username already taken'
    })

@csrf_protect
def register(request):
    if request.session.get('user_id'):
        return redirect('dashboard')

    if request.method == 'POST':
        first_name = request.POST.get('first_name', '').strip()
        last_name = request.POST.get('last_name', '').strip()
        username = request.POST.get('username', '').strip()
        email = request.POST.get('email', '').strip().lower()
        password1 = request.POST.get('password1', '')
        password2 = request.POST.get('password2', '')

        if not all([first_name, last_name, username, email, password1, password2]):
            messages.error(request, 'All fields are required.')
            return redirect('register')
        
        gmail_regex = r'^[a-zA-Z0-9._%+-]+@gmail\.com$'
        if not re.match(gmail_regex, email):
            messages.error(request, 'Please enter a valid Gmail address.')
            return redirect('register')

        valid_username_regex = r'^[A-Za-z0-9][A-Za-z0-9_]{2,49}$'
        if not re.match(valid_username_regex, username):
            messages.error(request, 'Invalid username. Minimum 3 characters.')
            return redirect('register')
        
        if password1 != password2:
            messages.error(request, 'Passwords do not match.')
            return redirect('register')

        if Users.objects.filter(email=email).exists():
            messages.warning(request, 'Email already registered. Please login.')
            return redirect('login')

        if Users.objects.filter(username=username).exists():
            messages.warning(request, 'Username already taken. Please choose another.')
            return redirect('register')

        try:
            user = Users(
                first_name=first_name,
                last_name=last_name,
                username=username,
                email=email,
                role='user',
                created_at=timezone.now()
            )
            user.set_password(password1)
            user.save()

            messages.success(request, 'Account created successfully! Please login.')
            return redirect('login')

        except Exception as e:
            logger.error(f"Error creating user {email}: {str(e)}")
            messages.error(request, f'Error creating account: {str(e)}')
            return redirect('register')

    return render(request, 'pages/register.html')


@csrf_protect
def forgot_password(request):
    if request.method == "POST":
        email = request.POST.get("email", "").strip().lower()
        if not email:
            messages.error(request, "Please enter a valid email.")
            return redirect('forgot_password')

        if not Users.objects.filter(email=email).exists():
            messages.warning(request, f"No account found with email {email}.")
            return redirect('forgot_password')

        try:
            success, msg = create_and_send_otp(email)

            if not success:
                messages.error(request, msg)
                return redirect('forgot_password')

            request.session['pending_email'] = email
            messages.success(request, msg)
            return redirect('verify_otp')

        except Exception as e:
            logger.error(f"OTP sending failed for {email}: {str(e)}")
            messages.error(request, f"Failed to send OTP: {str(e)}")
            return redirect('forgot_password')

    return render(request, 'pages/forgot_password.html')

def verify_otp_view(request):
    email = request.session.get("pending_email")

    if not email:
        messages.error(request, "You must request a password reset first.")
        return redirect('forgot_password')

    if request.method == "POST":
        otp = request.POST.get("otp")

        if not email:
            messages.error(request, "Session expired. Try again.")
            return redirect('forgot_password')

        is_valid, msg = verify_otp(email, otp)

        if is_valid:
            messages.success(request, "OTP verified successfully!")
            request.session['reset_email'] = email
            request.session.pop("pending_email", None)

            return redirect('reset_password')
        else:
            messages.error(request, msg)

    email = request.session.get("pending_email")
    masked_email = mask_email(email) if email else ""

    return render(request, 'pages/verify_otp.html', {
        'masked_email': masked_email
    })

def resend_otp(request):
    if request.method == "POST":
        email = request.session.get("pending_email")

        if not email:
            return JsonResponse({"success": False, "message": "Session expired"})

        success, msg = create_and_send_otp(email)

        return JsonResponse({
            "success": success,
            "message": msg
        })

    return JsonResponse({"success": False, "message": "Invalid request"})

@csrf_protect
def reset_password(request):
    email = request.session.get("reset_email")
    if not email:
        messages.error(request, "Unauthorized access. Please verify OTP first.")
        return redirect('forgot_password')

    user = Users.objects.filter(email=email).first()
    if not user:
        messages.error(request, "User not found.")
        request.session.pop("reset_email", None)
        return redirect('forgot_password')

    if request.method == "POST":
        new_password1 = request.POST.get("new_password1")
        new_password2 = request.POST.get("new_password2")

        if not new_password1 or not new_password2:
            messages.error(request, "All fields are required.")
        elif new_password1 != new_password2:
            messages.error(request, "Passwords do not match.")
        else:
            user.password = make_password(new_password1)
            user.save()

            request.session.pop("reset_email", None)

            messages.success(request, "Password reset successfully! Please login.")
            return redirect('login')

    return render(request, 'pages/reset_password.html')

def dashboard(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user_id = request.session.get('user_id')
    user = Users.objects.filter(id=user_id).first()

    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    now = timezone.localtime()
    hour = now.hour

    if hour < 5:
        greeting = "Still up"
        greeting_icon = "moon-stars"
    elif hour < 12:
        greeting = "Good morning"
        greeting_icon = "sunrise"
    elif hour < 17:
        greeting = "Good afternoon"
        greeting_icon = "sun"
    elif hour < 21:
        greeting = "Good evening"
        greeting_icon = "sunset"
    else:
        greeting = "Working late"
        greeting_icon = "moon"

    context = {
        "user": user,
        "greeting": greeting,
        "greeting_icon": greeting_icon,
        "today": now.strftime("%A, %B %d, %Y"),
    }

    return render(request, 'dashboard/dashboard.html', context)

def profile(request):
    return render(request, 'dashboard/profile.html')
