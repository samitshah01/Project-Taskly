from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.hashers import check_password, make_password
from django.views.decorators.csrf import csrf_protect
from django.db.models import Sum

from .models import Users, Project, Task, Expense, ActivityLog


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
            request.session['user_name'] = f"{user.first_name} {user.last_name}".strip()

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
        return redirect('dashboard')

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

            Users.objects.create(
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
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user_id = request.session.get('user_id')

    user = Users.objects.filter(id=user_id).first()

    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    total_projects = Project.objects.count()

    active_tasks = Task.objects.filter(
        status__in=["todo", "in_progress", "review"]
    ).count()

    total_team_members = Users.objects.count()

    budget_used = Expense.objects.aggregate(
        total=Sum('amount')
    )['total'] or 0

    recent_tasks = Task.objects.order_by('-id')[:5]

    recent_projects = Project.objects.order_by('-id')[:5]

    recent_activities = ActivityLog.objects.order_by('-timestamp')[:5]

    context = {
        "user": user,
        "total_projects": total_projects,
        "active_tasks": active_tasks,
        "team_members": total_team_members,
        "budget_used": budget_used,
        "recent_tasks": recent_tasks,
        "recent_projects": recent_projects,
        "recent_activities": recent_activities
    }

    return render(request, 'pages/dashboard.html', context)