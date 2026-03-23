import re
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import csrf_protect
from django.db.models import Sum
from .models import Users, Project, Task, Expense, ActivityLog
from django.http import JsonResponse
from .utils import create_and_send_otp, verify_otp, mask_email
from django.contrib.auth.hashers import make_password

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

        user = Users.objects.filter(email__iexact=identifier).first() \
            or Users.objects.filter(username__iexact=identifier).first()

        if not user:
            messages.error(request, 'User not found.')
            return render(request, 'pages/login.html')

        user_password = user.password or ''

        if check_password(password, user_password):
            request.session.flush()

            request.session['user_id'] = user.id
            request.session['user_email'] = user.email
            request.session['user_role'] = user.role
            request.session['user_name'] = f"{user.first_name} {user.last_name}".strip()

            request.session.set_expiry(0 if not remember else 60 * 60 * 24 * 30)

            return redirect('dashboard')
        else:
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

    total_projects = Project.objects.count()
    team_list = Users.objects.all()

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
        "recent_activities": recent_activities,
        "team_list": team_list
    }

    return render(request, 'pages/dashboard.html', context)

def log_activity(user_id, action, project=None, task=None):
    user = Users.objects.filter(id=user_id).first()

    if user:
        ActivityLog.objects.create(
            user=user,
            action=action,
            project=project,
            task=task,
            timestamp=timezone.now()
        )

def projects(request):

    projects = Project.objects.select_related("manager").all()
    managers = Users.objects.all()

    context = {
        "projects": projects,
        "managers": managers,
        "total_projects": projects.count(),
        "in_progress": projects.filter(status="in_progress").count(),
        "completed": projects.filter(status="completed").count(),
        "on_hold": projects.filter(status="on_hold").count(),
        "active_page": "projects"
    }

    return render(request, "pages/projects.html", context)

def create_project(request):

    if request.method == "POST":

        name = request.POST.get("name")
        description = request.POST.get("description")
        start_date = request.POST.get("start_date")
        end_date = request.POST.get("end_date")
        budget = request.POST.get("budget")
        manager_id = request.POST.get("manager")
        status = request.POST.get("status")

        manager = Users.objects.filter(id=manager_id).first()

        project = Project.objects.create(
            name=name,
            description=description,
            start_date=start_date,
            end_date=end_date if end_date else None,
            budget=budget,
            manager=manager,
            status=status,
            created_at=timezone.now(),
            updated_at=timezone.now()
        )

        # Activity Log
        log_activity(
            request.session.get("user_id"),
            f"Created project '{project.name}'",
            project
        )

    return redirect("projects")

def view_project(request, id):

    project = get_object_or_404(Project, id=id)

    context = {
        "project": project,
        "active_page": "projects"
    }

    return render(request, "pages/view_project.html", context)

def edit_project(request, id):

    project = get_object_or_404(Project, id=id)
    managers = Users.objects.all()

    if request.method == "POST":

        project.name = request.POST.get("name")
        project.description = request.POST.get("description")
        project.start_date = request.POST.get("start_date")
        project.end_date = request.POST.get("end_date")
        project.budget = request.POST.get("budget")
        project.status = request.POST.get("status")

        manager_id = request.POST.get("manager")
        project.manager = Users.objects.filter(id=manager_id).first()

        project.updated_at = timezone.now()

        project.save()

        log_activity(
            request.session.get("user_id"),
            f"Updated project '{project.name}'",
            project
        )

        messages.success(request, "Project updated successfully.")
        return redirect("projects")

    context = {
        "project": project,
        "managers": managers,
        "active_page": "projects"
    }

    return render(request, "pages/edit_project.html", context)

def delete_project(request, id):

    project = get_object_or_404(Project, id=id)
    project_name = project.name

    log_activity(
        request.session.get("user_id"),
        f"Deleted project '{project_name}'",
        project
    )
    project.delete()

    messages.success(request, "Project deleted successfully.")

    return redirect("projects")

def settings(request):

    user_id = request.session.get("user_id")
    user = Users.objects.filter(id=user_id).first()

    context = {
        "user": user,
        "active_page": "settings"
    }

    return render(request, "pages/settings.html", context)