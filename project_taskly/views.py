from django.shortcuts import render, redirect, get_object_or_404
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