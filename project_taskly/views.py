import re
import json
from decimal import Decimal, InvalidOperation
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.utils.timesince import timesince
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, Q, Sum, Case, When, IntegerField
from .models import Users, Project, Task, ActivityLog, ProjectMember
from django.http import JsonResponse
from .utils import create_and_send_otp, verify_otp, mask_email
from django.contrib.auth.hashers import make_password
from django.views.decorators.http import require_POST
import logging

logger = logging.getLogger(__name__)


def build_project_summary(project):
    tasks = list(project.tasks.all())
    total_tasks = len(tasks)
    todo_tasks = sum(1 for task in tasks if task.status == Task.STATUS_TODO)
    in_progress_tasks = sum(1 for task in tasks if task.status == Task.STATUS_IN_PROGRESS)
    completed_tasks = sum(1 for task in tasks if task.status == Task.STATUS_COMPLETED)
    progress = round(sum(get_task_progress(task) for task in tasks) / total_tasks) if total_tasks else 0
    members = list(project.project_members.all())

    return {
        'object': project,
        'progress': progress,
        'total_tasks': total_tasks,
        'todo_tasks': todo_tasks,
        'in_progress_tasks': in_progress_tasks,
        'completed_tasks': completed_tasks,
        'members': members[:3],
        'extra_members': max(len(members) - 3, 0),
    }


def get_task_progress(task):
    if task.status == Task.STATUS_COMPLETED:
        return 100
    if task.status == Task.STATUS_TODO:
        return 0
    if task.due_date and task.created_at:
        created_date = timezone.localtime(task.created_at).date()
        total_days = max((task.due_date - created_date).days, 1)
        elapsed_days = (timezone.localdate() - created_date).days
        return max(15, min(90, round((elapsed_days / total_days) * 100)))
    return 55


def build_task_payload(task):
    comments = [
        {
            'id': comment.id,
            'user_name': comment.user.display_name,
            'user_initials': comment.user.initials,
            'comment': comment.comment,
            'created_at': f"{timesince(comment.created_at)} ago",
        }
        for comment in task.comments.select_related('user').all().order_by('-created_at')
    ]

    member_options = [
        {
            'id': membership.user.id,
            'name': membership.user.display_name,
            'initials': membership.user.initials,
        }
        for membership in task.project.project_members.select_related('user').all()
    ]

    return {
        'id': task.id,
        'title': task.title,
        'description': task.description or '',
        'status': task.status,
        'status_label': task.get_status_display(),
        'priority': task.priority,
        'priority_label': task.get_priority_display(),
        'progress_value': get_task_progress(task),
        'due_date': task.due_date.isoformat() if task.due_date else '',
        'due_date_display': task.due_date.strftime('%b %d') if task.due_date else 'No date',
        'project_name': task.project.name,
        'project_id': task.project_id,
        'assigned_to_id': task.assigned_to_id,
        'assigned_to_name': task.assigned_to.display_name if task.assigned_to else '',
        'assigned_to_initials': task.assigned_to.initials if task.assigned_to else '',
        'comment_count': len(comments),
        'comments': comments,
        'members': member_options,
    }


def get_current_user(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    return Users.objects.filter(id=user_id).first()


def get_status_badge_color(status):
    return {
        'completed': 'var(--low)',
        'in_progress': 'var(--accent)',
        'planned': 'var(--med)',
        'on_hold': 'var(--high)',
        'todo': 'var(--med)',
    }.get(status, 'var(--muted)')


def build_dashboard_base_context(user):
    project_count = Project.objects.count()
    task_count = Task.objects.count()
    task_projects = Project.objects.prefetch_related('project_members__user').order_by('name')
    notification_count = ActivityLog.objects.filter(
        Q(user=user) | Q(project__project_members__user=user)
    ).distinct().count()

    task_project_member_map = {}
    for project in task_projects:
        task_project_member_map[str(project.id)] = [
            {
                'id': member.user.id,
                'name': member.user.display_name,
            }
            for member in project.project_members.all()
        ]

    return {
        'user': user,
        'sidebar_project_count': project_count,
        'sidebar_task_count': task_count,
        'notification_count': notification_count,
        'user_initials': user.initials,
        'task_project_options': task_projects,
        'task_project_member_map': task_project_member_map,
    }

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

    user = get_current_user(request)

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

    today_date = timezone.localdate()
    user_tasks = Task.objects.select_related('project').filter(assigned_to=user)
    total_tasks = user_tasks.count()
    pending_tasks = user_tasks.filter(status=Task.STATUS_TODO).count()
    in_progress_tasks = user_tasks.filter(status=Task.STATUS_IN_PROGRESS).count()
    completed_tasks = user_tasks.filter(status=Task.STATUS_COMPLETED).count()
    overdue_tasks = user_tasks.exclude(status=Task.STATUS_COMPLETED).filter(due_date__lt=today_date).count()

    my_tasks = list(user_tasks.order_by(
        Case(
            When(status=Task.STATUS_COMPLETED, then=1),
            default=0,
            output_field=IntegerField(),
        ),
        'due_date',
        '-created_at',
    )[:6])

    project_rows = []
    projects = Project.objects.prefetch_related('tasks', 'project_members__user').all()[:4]
    for project in projects:
        project_tasks = list(project.tasks.all())
        task_total = len(project_tasks)
        completed_total = sum(1 for task in project_tasks if task.status == Task.STATUS_COMPLETED)
        progress = round((completed_total / task_total) * 100) if task_total else 0
        member_initials = [member.user.initials for member in project.project_members.all()[:3]]
        project_rows.append({
            'object': project,
            'task_total': task_total,
            'progress': progress,
            'member_initials': member_initials,
            'member_extra_count': max(project.project_members.count() - len(member_initials), 0),
            'status_color': get_status_badge_color(project.status),
        })

    upcoming_deadlines = list(
        user_tasks.exclude(status=Task.STATUS_COMPLETED)
        .filter(due_date__isnull=False)
        .order_by('due_date')[:4]
    )
    recent_activity = list(
        ActivityLog.objects.select_related('user', 'project', 'task').order_by('-timestamp')[:4]
    )
    team_members = list(
        Users.objects.filter(
            Q(id=user.id) | Q(project_memberships__project__project_members__user=user)
        ).distinct()[:5]
    )

    context = build_dashboard_base_context(user)
    context.update({
        "greeting": greeting,
        "greeting_icon": greeting_icon,
        "today": now.strftime("%A, %B %d, %Y"),
        "today_date": today_date,
        "total_tasks": total_tasks,
        "pending_tasks": pending_tasks,
        "in_progress_tasks": in_progress_tasks,
        "completed_tasks": completed_tasks,
        "overdue_tasks": overdue_tasks,
        "my_tasks": my_tasks,
        "project_rows": project_rows,
        "upcoming_deadlines": upcoming_deadlines,
        "recent_activity": recent_activity,
        "team_members": team_members,
    })

    return render(request, 'dashboard/dashboard.html', context)

@require_POST
@csrf_protect
def create_task(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    project_id = request.POST.get('project', '').strip()
    priority = request.POST.get('priority', Task.PRIORITY_MEDIUM).strip()
    status = request.POST.get('status', Task.STATUS_TODO).strip()
    due_date = request.POST.get('due_date', '').strip() or None
    assigned_to_id = request.POST.get('assigned_to', '').strip() or None
    next_url = request.POST.get('next', '').strip() or 'dashboard'

    if not title:
        messages.error(request, 'Task title is required.')
        return redirect(next_url)

    project = Project.objects.filter(id=project_id).first()
    if not project:
        messages.error(request, 'Please select a valid project.')
        return redirect(next_url)

    valid_priorities = {choice[0] for choice in Task.PRIORITY_CHOICES}
    valid_statuses = {choice[0] for choice in Task.STATUS_CHOICES}

    if priority not in valid_priorities:
        priority = Task.PRIORITY_MEDIUM
    if status not in valid_statuses:
        status = Task.STATUS_TODO

    assigned_user = user
    if assigned_to_id:
        assigned_user = Users.objects.filter(
            id=assigned_to_id,
            project_memberships__project=project,
        ).distinct().first()
        if not assigned_user:
            messages.error(request, 'Please select a valid assignee.')
            return redirect(next_url)

    try:
        task = Task.objects.create(
            title=title,
            description=description or None,
            project=project,
            assigned_to=assigned_user,
            priority=priority,
            status=status,
            due_date=due_date,
        )

        ActivityLog.objects.create(
            user=user,
            action=f'created task "{task.title}"',
            project=project,
            task=task,
        )

        messages.success(request, 'Task created successfully.')
    except Exception as exc:
        logger.error(f"Task creation failed for user_id={user.id}: {exc}")
        messages.error(request, 'Unable to create task right now.')

    return redirect(next_url)

def projects(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    projects_qs = Project.objects.select_related('manager').prefetch_related('tasks', 'project_members__user').all()
    project_cards = [build_project_summary(project) for project in projects_qs]

    total_budget = projects_qs.aggregate(total=Sum('budget'))['total'] or 0
    status_counts = projects_qs.aggregate(
        total=Count('id'),
        in_progress=Count('id', filter=Q(status=Project.STATUS_IN_PROGRESS)),
        planned=Count('id', filter=Q(status=Project.STATUS_PLANNED)),
        completed=Count('id', filter=Q(status=Project.STATUS_COMPLETED)),
        on_hold=Count('id', filter=Q(status=Project.STATUS_ON_HOLD)),
    )

    context = build_dashboard_base_context(user)
    context.update({
        'projects': project_cards,
        'project_status_counts': status_counts,
        'project_total_budget': total_budget,
        'team_options': Users.objects.order_by('first_name', 'last_name', 'username'),
        'project_color_options': ['#4f7cff', '#7c5cfc', '#30d87d', '#ffb547', '#ff5470', '#00d4aa', '#e06030', '#8b5cf6'],
        'project_icon_options': ['globe', 'server', 'diagram-3', 'people', 'phone', 'bar-chart-line', 'shield-lock', 'lightning-charge', 'brush', 'gear'],
    })
    return render(request, 'dashboard/projects.html', context)


@require_POST
@csrf_protect
def update_project(request, project_id):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    project = Project.objects.filter(id=project_id).first()
    if not project:
        messages.error(request, 'Project not found.')
        return redirect('projects')

    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    status = request.POST.get('status', Project.STATUS_PLANNED).strip()
    start_date = request.POST.get('start_date', '').strip()
    end_date = request.POST.get('end_date', '').strip() or None
    color = request.POST.get('color', '#4f7cff').strip() or '#4f7cff'
    icon = request.POST.get('icon', 'folder2').strip() or 'folder2'
    budget_raw = request.POST.get('budget', '0').strip() or '0'

    if not name:
        messages.error(request, 'Project name is required.')
        return redirect('projects')

    if not start_date:
        messages.error(request, 'Start date is required.')
        return redirect('projects')

    valid_statuses = {choice[0] for choice in Project.STATUS_CHOICES}
    if status not in valid_statuses:
        status = Project.STATUS_PLANNED

    try:
        budget = Decimal(budget_raw)
        if budget < 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError):
        messages.error(request, 'Budget must be a valid positive amount.')
        return redirect('projects')

    if end_date and end_date < start_date:
        messages.error(request, 'Deadline cannot be earlier than the start date.')
        return redirect('projects')

    project.name = name
    project.description = description or None
    project.status = status
    project.start_date = start_date
    project.end_date = end_date
    project.budget = budget
    project.color = color
    project.icon = icon
    project.save()

    ActivityLog.objects.create(
        user=user,
        action=f'updated project "{project.name}"',
        project=project,
    )
    messages.success(request, 'Project updated successfully.')
    return redirect('projects')


@require_POST
@csrf_protect
def manage_project_team(request, project_id):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    project = Project.objects.prefetch_related('project_members').filter(id=project_id).first()
    if not project:
        messages.error(request, 'Project not found.')
        return redirect('projects')

    selected_member_ids = {int(member_id) for member_id in request.POST.getlist('members') if member_id.isdigit()}
    selected_member_ids.add(project.manager_id or user.id)

    current_members = {membership.user_id: membership for membership in project.project_members.all()}

    for member_id, membership in current_members.items():
        if member_id not in selected_member_ids and member_id != project.manager_id:
            membership.delete()

    valid_users = Users.objects.filter(id__in=selected_member_ids)
    for member in valid_users:
        if member.id not in current_members:
            ProjectMember.objects.create(
                project=project,
                user=member,
                role='Manager' if member.id == project.manager_id else 'Member',
            )
        elif member.id == project.manager_id and current_members[member.id].role != 'Manager':
            current_members[member.id].role = 'Manager'
            current_members[member.id].save(update_fields=['role'])

    ActivityLog.objects.create(
        user=user,
        action=f'updated team for "{project.name}"',
        project=project,
    )
    messages.success(request, 'Project team updated successfully.')
    return redirect('projects')


@require_POST
@csrf_protect
def delete_project(request, project_id):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    project = Project.objects.filter(id=project_id).first()
    if not project:
        messages.error(request, 'Project not found.')
        return redirect('projects')

    project_name = project.name
    project.delete()
    ActivityLog.objects.create(user=user, action=f'deleted project "{project_name}"')
    messages.success(request, 'Project deleted successfully.')
    return redirect('projects')


def project_board(request, project_id):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    project = Project.objects.select_related('manager').prefetch_related(
        'tasks__assigned_to',
        'tasks__comments__user',
        'project_members__user',
        'activity_logs__user',
    ).filter(id=project_id).first()

    if not project:
        messages.error(request, 'Project not found.')
        return redirect('projects')

    summary = build_project_summary(project)
    task_columns = {
        Task.STATUS_TODO: [],
        Task.STATUS_IN_PROGRESS: [],
        Task.STATUS_COMPLETED: [],
    }

    project_tasks = project.tasks.select_related('assigned_to').annotate(comment_count=Count('comments')).order_by('due_date', '-created_at')

    for task in project_tasks:
        task.progress_value = get_task_progress(task)
        task_columns.setdefault(task.status, []).append(task)

    recent_activity = list(project.activity_logs.all().order_by('-timestamp')[:5])

    context = build_dashboard_base_context(user)
    context.update({
        'project': project,
        'project_summary': summary,
        'board_columns': [
            {'key': Task.STATUS_TODO, 'label': 'To Do', 'tasks': task_columns[Task.STATUS_TODO], 'icon': 'list-task'},
            {'key': Task.STATUS_IN_PROGRESS, 'label': 'In Progress', 'tasks': task_columns[Task.STATUS_IN_PROGRESS], 'icon': 'activity'},
            {'key': Task.STATUS_COMPLETED, 'label': 'Completed', 'tasks': task_columns[Task.STATUS_COMPLETED], 'icon': 'patch-check'},
        ],
        'project_recent_activity': recent_activity,
        'selected_task_project_id': project.id,
    })
    return render(request, 'dashboard/project_board.html', context)


@require_POST
@csrf_protect
def update_task_status(request, task_id):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    task = Task.objects.select_related('project').filter(id=task_id).first()
    if not task:
        messages.error(request, 'Task not found.')
        return redirect('projects')

    next_url = request.POST.get('next', '').strip() or 'projects'
    new_status = request.POST.get('status', '').strip()
    valid_statuses = {choice[0] for choice in Task.STATUS_CHOICES}

    if new_status not in valid_statuses:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid task status.'}, status=400)
        messages.error(request, 'Invalid task status.')
        return redirect(next_url)

    if task.status != new_status:
        task.status = new_status
        task.save(update_fields=['status', 'updated_at'])
        ActivityLog.objects.create(
            user=user,
            action=f'moved task "{task.title}" to {task.get_status_display()}',
            project=task.project,
            task=task,
        )

    if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        task = Task.objects.select_related('project', 'assigned_to').prefetch_related(
            'comments__user',
            'project__project_members__user',
        ).get(id=task.id)
        return JsonResponse({
            'success': True,
            'task_id': task.id,
            'status': task.status,
            'status_label': task.get_status_display(),
            'message': 'Task status updated.',
            'redirect_url': reverse('project_board', args=[task.project_id]),
            'task': build_task_payload(task),
        })

    messages.success(request, 'Task status updated.')
    return redirect(next_url)


def task_detail(request, task_id):
    if not request.session.get('user_id'):
        return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)

    task = Task.objects.select_related('project', 'assigned_to').prefetch_related(
        'comments__user',
        'project__project_members__user',
    ).filter(id=task_id).first()

    if not task:
        return JsonResponse({'success': False, 'message': 'Task not found.'}, status=404)

    return JsonResponse({'success': True, 'task': build_task_payload(task)})


@require_POST
@csrf_protect
def update_task(request, task_id):
    if not request.session.get('user_id'):
        return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)

    user = get_current_user(request)
    if not user:
        request.session.flush()
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=401)

    task = Task.objects.select_related('project', 'assigned_to').prefetch_related(
        'comments__user',
        'project__project_members__user',
    ).filter(id=task_id).first()
    if not task:
        return JsonResponse({'success': False, 'message': 'Task not found.'}, status=404)

    title = request.POST.get('title', '').strip()
    description = request.POST.get('description', '').strip()
    status = request.POST.get('status', '').strip()
    priority = request.POST.get('priority', '').strip()
    due_date = request.POST.get('due_date', '').strip() or None
    assigned_to_id = request.POST.get('assigned_to', '').strip() or None

    if not title:
        return JsonResponse({'success': False, 'message': 'Task title is required.'}, status=400)

    valid_statuses = {choice[0] for choice in Task.STATUS_CHOICES}
    valid_priorities = {choice[0] for choice in Task.PRIORITY_CHOICES}

    if status not in valid_statuses:
        return JsonResponse({'success': False, 'message': 'Invalid status.'}, status=400)

    if priority not in valid_priorities:
        return JsonResponse({'success': False, 'message': 'Invalid priority.'}, status=400)

    assigned_user = None
    if assigned_to_id:
        assigned_user = Users.objects.filter(
            id=assigned_to_id,
            project_memberships__project=task.project,
        ).distinct().first()
        if not assigned_user:
            return JsonResponse({'success': False, 'message': 'Invalid assignee.'}, status=400)

    task.title = title
    task.description = description or None
    task.status = status
    task.priority = priority
    task.due_date = due_date
    task.assigned_to = assigned_user
    task.save()

    ActivityLog.objects.create(
        user=user,
        action=f'updated task "{task.title}"',
        project=task.project,
        task=task,
    )

    task.refresh_from_db()
    task = Task.objects.select_related('project', 'assigned_to').prefetch_related(
        'comments__user',
        'project__project_members__user',
    ).get(id=task.id)
    return JsonResponse({'success': True, 'message': 'Task updated successfully.', 'task': build_task_payload(task)})


@require_POST
@csrf_protect
def add_task_comment(request, task_id):
    if not request.session.get('user_id'):
        return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)

    user = get_current_user(request)
    if not user:
        request.session.flush()
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=401)

    task = Task.objects.select_related('project').filter(id=task_id).first()
    if not task:
        return JsonResponse({'success': False, 'message': 'Task not found.'}, status=404)

    comment_text = request.POST.get('comment', '').strip()
    if not comment_text:
        return JsonResponse({'success': False, 'message': 'Comment cannot be empty.'}, status=400)

    comment = task.comments.create(user=user, comment=comment_text)
    ActivityLog.objects.create(
        user=user,
        action=f'commented on "{task.title}"',
        project=task.project,
        task=task,
    )

    return JsonResponse({
        'success': True,
        'message': 'Comment added.',
        'comment': {
            'id': comment.id,
            'user_name': user.display_name,
            'user_initials': user.initials,
            'comment': comment.comment,
            'created_at': 'just now',
        }
    })


@require_POST
@csrf_protect
def delete_task(request, task_id):
    if not request.session.get('user_id'):
        return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)

    user = get_current_user(request)
    if not user:
        request.session.flush()
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=401)

    task = Task.objects.select_related('project').filter(id=task_id).first()
    if not task:
        return JsonResponse({'success': False, 'message': 'Task not found.'}, status=404)

    project_id = task.project_id
    task_title = task.title
    task.delete()

    ActivityLog.objects.create(
        user=user,
        action=f'deleted task "{task_title}"',
        project_id=project_id,
    )

    return JsonResponse({'success': True, 'message': 'Task deleted successfully.', 'project_id': project_id})

@require_POST
@csrf_protect
def create_project(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    name = request.POST.get('name', '').strip()
    description = request.POST.get('description', '').strip()
    status = request.POST.get('status', Project.STATUS_PLANNED).strip()
    start_date = request.POST.get('start_date', '').strip()
    end_date = request.POST.get('end_date', '').strip() or None
    color = request.POST.get('color', '#4f7cff').strip() or '#4f7cff'
    icon = request.POST.get('icon', 'folder2').strip() or 'folder2'
    member_ids = request.POST.getlist('members')

    budget_raw = request.POST.get('budget', '0').strip() or '0'
    next_url = request.POST.get('next', '').strip() or 'projects'

    if not name:
        messages.error(request, 'Project name is required.')
        return redirect(next_url)

    if not start_date:
        messages.error(request, 'Start date is required.')
        return redirect(next_url)

    valid_statuses = {choice[0] for choice in Project.STATUS_CHOICES}
    if status not in valid_statuses:
        status = Project.STATUS_PLANNED

    try:
        budget = Decimal(budget_raw)
        if budget < 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError):
        messages.error(request, 'Budget must be a valid positive amount.')
        return redirect(next_url)

    if end_date and end_date < start_date:
        messages.error(request, 'Deadline cannot be earlier than the start date.')
        return redirect(next_url)

    try:
        project = Project.objects.create(
            name=name,
            description=description or None,
            start_date=start_date,
            end_date=end_date,
            budget=budget,
            manager=user,
            status=status,
            color=color,
            icon=icon,
        )

        member_queryset = Users.objects.filter(id__in=member_ids).distinct()
        ProjectMember.objects.create(project=project, user=user, role='Manager')

        existing_member_ids = {user.id}
        for member in member_queryset:
            if member.id in existing_member_ids:
                continue
            ProjectMember.objects.create(project=project, user=member, role='Member')
            existing_member_ids.add(member.id)

        ActivityLog.objects.create(
            user=user,
            action=f'created project "{project.name}"',
            project=project,
        )

        messages.success(request, 'Project created successfully.')
    except Exception as exc:
        logger.error(f"Project creation failed for user_id={user.id}: {exc}")
        messages.error(request, 'Unable to create project right now.')

    return redirect(next_url)

def profile(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    return render(request, 'dashboard/profile.html', build_dashboard_base_context(user))
