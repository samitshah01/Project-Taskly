import re
import json
import os
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError, available_timezones
from decimal import Decimal, InvalidOperation
from datetime import date, timedelta
from django.conf import settings
from django.shortcuts import render, redirect
from django.contrib import messages
from django.utils import timezone
from django.urls import reverse
from django.utils.timesince import timesince
from django.utils.dateparse import parse_date, parse_datetime
from django.contrib.auth.hashers import check_password
from django.views.decorators.csrf import csrf_protect
from django.db.models import Count, Q, Sum, Case, When, IntegerField
from django.db.models.functions import TruncMonth
from django.core.paginator import Paginator
from .models import Users, Project, Task, ActivityLog, ProjectMember, ProjectFile, Expense, ExpenseCategory, EmployeeProfile, EmployeePayroll, EmailNotificationLog
from django.http import JsonResponse, FileResponse, Http404, HttpResponse
from .notifications import send_generic_notification
from .utils import create_and_send_otp, verify_otp, mask_email
from django.contrib.auth.hashers import make_password
from django.views.decorators.http import require_POST
import logging

logger = logging.getLogger(__name__)
NOTIFICATIONS_LAST_SEEN_SESSION_KEY = 'notifications_last_seen_at'
PROJECT_STATUS_WORKFLOW = {
    Project.STATUS_PLANNED: {Project.STATUS_IN_PROGRESS, Project.STATUS_ON_HOLD},
    Project.STATUS_IN_PROGRESS: {Project.STATUS_ON_HOLD, Project.STATUS_COMPLETED},
    Project.STATUS_ON_HOLD: {Project.STATUS_IN_PROGRESS, Project.STATUS_COMPLETED},
    Project.STATUS_COMPLETED: set(),
}
TASK_STATUS_WORKFLOW = {
    Task.STATUS_TODO: {Task.STATUS_IN_PROGRESS},
    Task.STATUS_IN_PROGRESS: {Task.STATUS_TODO, Task.STATUS_COMPLETED},
    Task.STATUS_COMPLETED: {Task.STATUS_IN_PROGRESS},
}


def format_utc_offset(offset):
    total_minutes = int((offset.total_seconds() if offset else 0) // 60)
    sign = "+" if total_minutes >= 0 else "-"
    total_minutes = abs(total_minutes)
    hours, minutes = divmod(total_minutes, 60)
    return f"UTC{sign}{hours:02d}:{minutes:02d}"


def get_safe_timezone(tz_name):
    try:
        return ZoneInfo(tz_name)
    except ZoneInfoNotFoundError:
        return ZoneInfo("UTC")


def build_timezone_options(selected_timezone):
    reference_now = timezone.now()
    options = []

    for tz_name in sorted(available_timezones()):
        if tz_name.startswith("Etc/"):
            continue

        zone = get_safe_timezone(tz_name)
        localized_now = reference_now.astimezone(zone)
        options.append({
            "value": tz_name,
            "label": f"{tz_name.replace('_', ' ')} ({format_utc_offset(localized_now.utcoffset())})",
            "selected": tz_name == selected_timezone,
        })

    return options


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


def get_project_membership(project, user):
    if not user or not project:
        return None
    membership = project.project_members.filter(user=user).first()
    if membership:
        return membership
    if (project.manager_id and project.manager_id == user.id) or (getattr(project, 'owner_id', None) and project.owner_id == user.id):
        return sync_project_manager_membership(project, user)
    return None


def get_project_owner_id(project):
    return getattr(project, 'owner_id', None) or project.manager_id


def is_project_owner(project, user):
    return bool(project and user and get_project_owner_id(project) == user.id)


def is_project_manager(project, user):
    membership = get_project_membership(project, user)
    if membership and membership.is_manager:
        return True
    return bool(project.manager_id and user and project.manager_id == user.id)


def has_project_full_access(project, user):
    return is_project_owner(project, user) or is_project_manager(project, user)


def can_view_project_budget(project, user):
    return is_project_owner(project, user)


def can_manage_project_finances(project, user):
    return is_project_owner(project, user)


def is_project_member(project, user):
    return get_project_membership(project, user) is not None


def get_accessible_projects(user):
    if not user:
        return Project.objects.none()
    return Project.objects.select_related('manager', 'owner').prefetch_related('tasks', 'project_members__user').filter(
        Q(project_members__user=user) | Q(manager=user) | Q(owner=user)
    ).distinct()


def get_budget_visible_projects(user):
    accessible_projects = list(get_accessible_projects(user))
    allowed_ids = [project.id for project in accessible_projects if can_view_project_budget(project, user)]
    return Project.objects.select_related('manager', 'owner').prefetch_related('tasks', 'project_members__user').filter(id__in=allowed_ids)


def get_default_finance_project(user):
    if not user:
        return None
    owned_project = get_accessible_projects(user).filter(owner=user).order_by('name').first()
    if owned_project:
        return owned_project
    return get_accessible_projects(user).order_by('name').first()


def get_project_budget_url(project):
    return reverse('project_budget', args=[project.id])


def sync_project_manager_membership(project, manager_user, role_label='Project Manager'):
    membership, _ = ProjectMember.objects.get_or_create(
        project=project,
        user=manager_user,
        defaults={'role': role_label, 'is_manager': True},
    )
    updates = []
    if membership.role != role_label:
        membership.role = role_label
        updates.append('role')
    if not membership.is_manager:
        membership.is_manager = True
        updates.append('is_manager')
    if updates:
        membership.save(update_fields=updates)
    return membership


DEFAULT_FIXED_CATEGORY_NAMES = ['Salary', 'Tools', 'Services', 'Miscellaneous']
FINANCE_ENTRY_KIND_CHOICES = [
    ('income', 'Income'),
    ('expense', 'Expense'),
    ('salary', 'Salary Payment'),
]
PROJECT_ROLE_CHOICES = [
    ('product_owner', 'Product Owner'),
    ('project_manager', 'Project Manager'),
    ('client', 'Client'),
    ('developer', 'Developer'),
    ('designer', 'Designer'),
    ('qa_engineer', 'QA Engineer'),
    ('business_analyst', 'Business Analyst'),
    ('devops_engineer', 'DevOps Engineer'),
]


def normalize_category_name(value):
    return " ".join((value or '').strip().split())


def ensure_default_expense_categories(project, user=None):
    if not project:
        return
    existing_names = set(project.expense_categories.filter(is_fixed=True).values_list('name', flat=True))
    missing_names = [name for name in DEFAULT_FIXED_CATEGORY_NAMES if name not in existing_names]
    for name in missing_names:
        ExpenseCategory.objects.create(
            project=project,
            name=name,
            is_fixed=True,
        )


def get_salary_category(project, user=None):
    ensure_default_expense_categories(project, user)
    category = project.expense_categories.filter(name__iexact='Salary').first()
    if category:
        return category
    return ExpenseCategory.objects.create(
        project=project,
        name='Salary',
        is_fixed=True,
    )
def build_role_badge_class(role_name, is_manager=False):
    if is_manager:
        return 'bg-primary'

    normalized_role = (role_name or '').strip().lower()
    if 'developer' in normalized_role:
        return 'bg-success'
    if 'designer' in normalized_role:
        return 'bg-info text-dark'
    if 'qa' in normalized_role or 'tester' in normalized_role:
        return 'bg-warning text-dark'
    return 'bg-secondary'


def normalize_membership_role(role_name, is_manager=False):
    cleaned_role = (role_name or '').strip()
    if is_manager:
        return cleaned_role or 'Project Manager'
    return cleaned_role or 'Team Member'


def get_project_role_options():
    return [{'value': value, 'label': label} for value, label in PROJECT_ROLE_CHOICES]


def normalize_project_role_value(role_value, is_manager=False):
    normalized = (role_value or '').strip().lower()
    role_map = dict(PROJECT_ROLE_CHOICES)
    if is_manager:
        return 'Project Manager'
    if normalized in role_map:
        return role_map[normalized]
    return 'Developer'


def build_member_entry(membership, current_user_id=None):
    display_role = membership.display_role
    return {
        'membership_id': membership.id,
        'user': membership.user,
        'role': display_role,
        'badge_class': build_role_badge_class(display_role, membership.is_manager),
        'is_manager': membership.is_manager,
        'is_current_user': membership.user_id == current_user_id,
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
            'user_id': comment.user.id,
            'user_name': comment.user.display_name,
            'user_initials': comment.user.initials,
            'user_avatar_url': comment.user.avatar_url,
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
            'role': membership.display_role,
            'is_manager': membership.is_manager,
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
        'assigned_to_avatar_url': task.assigned_to.avatar_url if task.assigned_to else '',
        'comment_count': len(comments),
        'comments': comments,
        'members': member_options,
    }


def get_current_user(request):
    user_id = request.session.get('user_id')
    if not user_id:
        return None
    return Users.objects.filter(id=user_id).first()


def complete_login_session(request, user, remember=False):
    request.session.flush()
    request.session['user_id'] = user.id
    request.session['user_email'] = user.email
    request.session['user_role'] = user.role
    request.session['user_full_name'] = f"{user.first_name or ''} {user.last_name or ''}".strip()
    request.session['user_username'] = user.username
    request.session.set_expiry(0 if not remember else 60 * 60 * 24 * 30)


def get_status_badge_color(status):
    return {
        'completed': 'var(--low)',
        'in_progress': 'var(--accent)',
        'planned': 'var(--med)',
        'on_hold': 'var(--high)',
        'todo': 'var(--med)',
    }.get(status, 'var(--muted)')


def get_notifications_last_seen(request):
    raw_value = request.session.get(NOTIFICATIONS_LAST_SEEN_SESSION_KEY)
    if not raw_value:
        return None

    parsed_value = parse_datetime(raw_value)
    if not parsed_value:
        return None

    if timezone.is_naive(parsed_value):
        return timezone.make_aware(parsed_value, timezone.get_current_timezone())
    return parsed_value


def can_transition_project_status(current_status, next_status):
    if current_status == next_status:
        return True
    return next_status in PROJECT_STATUS_WORKFLOW.get(current_status, set())


def can_transition_task_status(current_status, next_status):
    if current_status == next_status:
        return True
    return next_status in TASK_STATUS_WORKFLOW.get(current_status, set())


def send_user_email_notification(user, subject, message):
    if not user or not user.email:
        return

    try:
        send_generic_notification(user, subject, message)
    except Exception as exc:
        logger.warning("Email notification failed for user_id=%s: %s", user.id, exc)


def get_user_mentions(comment_text):
    usernames = {match.lower() for match in re.findall(r'@([A-Za-z0-9_]{3,50})', comment_text or "")}
    if not usernames:
        return []
    return list(Users.objects.filter(username__iregex=r'^(?:' + '|'.join(re.escape(name) for name in usernames) + r')$'))


def get_project_file_absolute_path(project_file):
    relative_path = (project_file.file or "").replace("/", os.sep)
    return os.path.join(settings.MEDIA_ROOT, relative_path)


def build_budget_rows(projects, current_user):
    budget_rows = []
    total_budget = Decimal('0')
    total_actual = Decimal('0')

    for project in projects:
        actual = project.expenses.filter(transaction_type=Expense.TYPE_EXPENSE).aggregate(total=Sum('amount'))['total'] or Decimal('0')
        remaining = project.budget - actual
        usage_percent = min(100, round((actual / project.budget) * 100)) if project.budget else 0
        categories = list(project.expense_categories.all())
        expenses = list(
            project.expenses.filter(transaction_type=Expense.TYPE_EXPENSE).select_related('category').order_by('-created_at')[:6]
        )
        budget_rows.append({
            'project': project,
            'actual': actual,
            'remaining': remaining,
            'usage_percent': usage_percent,
            'categories': categories,
            'expenses': expenses,
            'can_manage': can_manage_project_finances(project, current_user),
        })
        total_budget += project.budget or Decimal('0')
        total_actual += actual

    return budget_rows, total_budget, total_actual


def build_finance_badge_class(status):
    return {
        Expense.STATUS_PAID: 'bg-success-subtle text-success border border-success-subtle',
        Expense.STATUS_PENDING: 'bg-warning-subtle text-warning border border-warning-subtle',
        Expense.STATUS_CANCELLED: 'bg-danger-subtle text-danger border border-danger-subtle',
        Expense.STATUS_OVERDUE: 'bg-danger-subtle text-danger border border-danger-subtle',
    }.get(status, 'bg-secondary-subtle text-light border border-secondary-subtle')


def build_transaction_reference_id(transaction_id):
    return f"TXN-{int(transaction_id):06d}"


def ensure_transaction_reference_id(transaction):
    if not transaction or not transaction.id:
        return ""

    expected_reference_id = build_transaction_reference_id(transaction.id)
    duplicate_exists = bool(
        transaction.reference_id
        and Expense.objects.exclude(id=transaction.id).filter(reference_id=transaction.reference_id).exists()
    )

    if transaction.reference_id != expected_reference_id or duplicate_exists:
        transaction.reference_id = expected_reference_id
        transaction.save(update_fields=['reference_id'])

    return transaction.reference_id


def build_finance_rows(transactions):
    rows = []
    income_total = Decimal('0')
    expense_total = Decimal('0')
    salary_total = Decimal('0')

    for transaction in transactions:
        reference_id = ensure_transaction_reference_id(transaction)
        amount = transaction.amount or Decimal('0')
        if transaction.transaction_type == Expense.TYPE_INCOME:
            income_total += amount
        else:
            expense_total += amount
            if transaction.is_salary_payment:
                salary_total += amount

        rows.append({
            'object': transaction,
            'title': transaction.display_title,
            'project_name': transaction.project.name,
            'project_id': transaction.project_id,
            'category_name': transaction.category_name,
            'reference_id': reference_id,
            'issue_date': transaction.issue_date,
            'paid_date': transaction.paid_date,
            'status': transaction.status,
            'status_label': transaction.get_status_display(),
            'status_badge_class': build_finance_badge_class(transaction.status),
            'amount': amount,
            'is_income': transaction.transaction_type == Expense.TYPE_INCOME,
            'is_salary_payment': transaction.is_salary_payment,
            'entry_kind_label': 'Salary Payment' if transaction.is_salary_payment else ('Income' if transaction.transaction_type == Expense.TYPE_INCOME else 'Expense'),
            'assigned_user_name': transaction.assigned_user.display_name if transaction.assigned_user else '',
        })

    return rows, income_total, expense_total, salary_total, income_total - expense_total


def get_profile_badge_class(status):
    return {
        EmployeeProfile.STATUS_ACTIVE: 'bg-success-subtle text-success border border-success-subtle',
        EmployeeProfile.STATUS_ON_LEAVE: 'bg-warning-subtle text-warning border border-warning-subtle',
        EmployeeProfile.STATUS_INACTIVE: 'bg-secondary-subtle text-light border border-secondary-subtle',
    }.get(status, 'bg-secondary-subtle text-light border border-secondary-subtle')


def get_assignment_badge_class(status):
    return {
        'active': 'bg-primary-subtle text-primary border border-primary-subtle',
        'planned': 'bg-info-subtle text-info border border-info-subtle',
        'completed': 'bg-success-subtle text-success border border-success-subtle',
        'on_hold': 'bg-warning-subtle text-warning border border-warning-subtle',
    }.get(status, 'bg-secondary-subtle text-light border border-secondary-subtle')


def ensure_employee_profile(user):
    if not user:
        return None
    profile, _ = EmployeeProfile.objects.get_or_create(
        user=user,
        defaults={
            'employee_type': EmployeeProfile.TYPE_FULL_TIME,
            'salary': Decimal('0'),
            'join_date': user.created_at.date() if user.created_at else timezone.localdate(),
            'status': EmployeeProfile.STATUS_ACTIVE,
        },
    )
    return profile


def build_user_directory_rows(queryset, include_profiles=False):
    user_list = list(queryset.order_by('first_name', 'last_name', 'username', 'email'))
    profiles = {}
    membership_map = {}
    if include_profiles and user_list:
        profiles = {profile.user_id: profile for profile in EmployeeProfile.objects.filter(user__in=user_list)}
    if user_list:
        membership_map = {directory_user.id: [] for directory_user in user_list}
        memberships = (
            ProjectMember.objects.select_related('project')
            .filter(user__in=user_list)
            .order_by('-assignment_start_date', '-joined_at')
        )
        for membership in memberships:
            membership_map.setdefault(membership.user_id, []).append(membership)

    rows = []
    for directory_user in user_list:
        profile = profiles.get(directory_user.id) if include_profiles else None
        memberships = membership_map.get(directory_user.id, [])
        rows.append({
            'user': directory_user,
            'profile': profile,
            'membership_count': len(memberships),
            'assigned_projects': memberships,
            'primary_assignment': memberships[0] if memberships else None,
            'status_badge_class': get_profile_badge_class(profile.status) if profile else '',
        })
    return rows


def build_dashboard_base_context(request, user):
    accessible_projects = list(get_accessible_projects(user))
    project_count = len(accessible_projects)
    task_count = Task.objects.filter(assigned_to=user).count()
    task_projects = [project for project in accessible_projects if has_project_full_access(project, user)]
    finance_project = get_default_finance_project(user)
    notifications_last_seen = get_notifications_last_seen(request)
    notification_qs = ActivityLog.objects.select_related('user', 'project', 'task').filter(
        Q(user=user) | Q(project__project_members__user=user)
    ).distinct()
    notification_count = notification_qs.count()
    notification_unread_count = notification_qs.filter(
        timestamp__gt=notifications_last_seen
    ).count() if notifications_last_seen else notification_count

    task_project_member_map = {}
    for project in task_projects:
        task_project_member_map[str(project.id)] = [
            {
                'id': member.user.id,
                'name': member.user.display_name,
                'role': member.display_role,
            }
            for member in project.project_members.all()
        ]

    recent_notifications = [
        {
            'user_id': log.user.id,
            'user_initials': log.user.initials,
            'user_avatar_url': log.user.avatar_url,
            'user_name': log.user.display_name,
            'action': log.action,
            'timestamp': f"{timesince(log.timestamp)} ago",
            'is_unread': log.timestamp > notifications_last_seen if notifications_last_seen else True,
        }
        for log in notification_qs[:6]
    ]

    return {
        'user': user,
        'sidebar_project_count': project_count,
        'sidebar_task_count': task_count,
        'notification_count': notification_count,
        'notification_unread_count': notification_unread_count,
        'recent_notifications': recent_notifications,
        'user_initials': user.initials,
        'user_avatar_url': user.avatar_url,
        'task_project_options': task_projects,
        'task_project_member_map': task_project_member_map,
        'managed_project_ids': [project.id for project in task_projects],
        'finance_nav_url': get_project_budget_url(finance_project) if finance_project else reverse('projects'),
    }

@require_POST
def set_timezone(request):
    try:
        data = json.loads(request.body)
        tz_name = data.get("timezone", "").strip()

        if tz_name:
            get_safe_timezone(tz_name)
            request.session["user_timezone"] = tz_name
            return JsonResponse({"status": "ok", "timezone": tz_name})

        return JsonResponse({"status": "error", "message": "Timezone missing"}, status=400)
    except Exception:
        return JsonResponse({"status": "error", "message": "Invalid request"}, status=400)


@require_POST
def mark_notifications_read(request):
    if not request.session.get('user_id'):
        return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)

    user = get_current_user(request)
    if not user:
        request.session.flush()
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=401)

    request.session[NOTIFICATIONS_LAST_SEEN_SESSION_KEY] = timezone.now().isoformat()
    return JsonResponse({'success': True, 'message': 'Notifications marked as read.', 'unread_count': 0})

def index(request):
    return render(request, 'index.html')

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
            remember_login = bool(remember)

            if user.is_email_verified:
                logger.info(f"User logged in successfully without OTP: user_id={user.id}")
                complete_login_session(request, user, remember_login)
                messages.success(request, 'Successfully Logged In.')
                return redirect('dashboard')

            request.session['pending_email'] = user.email
            request.session['otp_purpose'] = 'login'
            request.session['pending_login_user_id'] = user.id
            request.session['pending_login_remember'] = remember_login

            success, msg = create_and_send_otp(user.email, purpose='login')
            if not success:
                request.session.pop('pending_email', None)
                request.session.pop('otp_purpose', None)
                request.session.pop('pending_login_user_id', None)
                request.session.pop('pending_login_remember', None)
                messages.error(request, msg)
                return render(request, 'pages/login.html')

            logger.info(f"Login password verified, OTP sent for user_id={user.id}")
            messages.success(request, 'We sent a verification code to your email. Enter it to continue.')
            return redirect('verify_otp')
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
        first_name = request.POST.get('first_name', '').strip().capitalize()
        last_name = request.POST.get('last_name', '').strip().capitalize()
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
            success, msg = create_and_send_otp(email, purpose='password_reset')

            if not success:
                messages.error(request, msg)
                return redirect('forgot_password')

            request.session['pending_email'] = email
            request.session['otp_purpose'] = 'password_reset'
            request.session.pop('pending_login_user_id', None)
            request.session.pop('pending_login_remember', None)
            messages.success(request, msg)
            return redirect('verify_otp')

        except Exception as e:
            logger.error(f"OTP sending failed for {email}: {str(e)}")
            messages.error(request, f"Failed to send OTP: {str(e)}")
            return redirect('forgot_password')

    return render(request, 'pages/forgot_password.html')

def verify_otp_view(request):
    email = request.session.get("pending_email")
    otp_purpose = request.session.get("otp_purpose", "password_reset")

    if not email:
        if otp_purpose == 'login':
            messages.error(request, "Your login verification session expired. Please sign in again.")
            return redirect('login')
        messages.error(request, "You must request a password reset first.")
        return redirect('forgot_password')

    if request.method == "POST":
        otp = request.POST.get("otp")

        if not email:
            messages.error(request, "Session expired. Try again.")
            return redirect('forgot_password')

        is_valid, msg = verify_otp(email, otp)

        if is_valid:
            if otp_purpose == 'login':
                pending_user_id = request.session.get('pending_login_user_id')
                remember_login = bool(request.session.get('pending_login_remember', False))
                user = Users.objects.filter(id=pending_user_id, email__iexact=email).first()

                if not user:
                    request.session.pop("pending_email", None)
                    request.session.pop("otp_purpose", None)
                    request.session.pop("pending_login_user_id", None)
                    request.session.pop("pending_login_remember", None)
                    messages.error(request, "Login session expired. Please sign in again.")
                    return redirect('login')

                if not user.is_email_verified:
                    user.is_email_verified = True
                    user.save(update_fields=['is_email_verified'])

                logger.info(f"User logged in successfully after OTP verification: user_id={user.id}")
                complete_login_session(request, user, remember_login)
                messages.success(request, "Email verified successfully. Welcome back!")
                return redirect('dashboard')

            messages.success(request, "OTP verified successfully!")
            request.session['reset_email'] = email
            request.session.pop("pending_email", None)
            request.session.pop("otp_purpose", None)
            request.session.pop("pending_login_user_id", None)
            request.session.pop("pending_login_remember", None)
            return redirect('reset_password')
        else:
            messages.error(request, msg)

    email = request.session.get("pending_email")
    masked_email = mask_email(email) if email else ""

    return render(request, 'pages/verify_otp.html', {
        'masked_email': masked_email,
        'otp_purpose': otp_purpose,
        'otp_resend_url': reverse('resend_otp'),
    })

def resend_otp(request):
    if request.method == "POST":
        email = request.session.get("pending_email")

        if not email:
            return JsonResponse({"success": False, "message": "Session expired"})

        otp_purpose = request.session.get("otp_purpose", "password_reset")
        success, msg = create_and_send_otp(email, purpose=otp_purpose)

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
    accessible_projects = list(get_accessible_projects(user).prefetch_related('expenses', 'expense_categories') )
    projects = accessible_projects[:4]
    for project in projects:
        membership = get_project_membership(project, user)
        project_tasks = list(project.tasks.all())
        task_total = len(project_tasks)
        completed_total = sum(1 for task in project_tasks if task.status == Task.STATUS_COMPLETED)
        progress = round((completed_total / task_total) * 100) if task_total else 0
        member_entries = [
            build_member_entry(member, current_user_id=user.id)
            for member in project.project_members.select_related('user').all()
        ]
        project_rows.append({
            'object': project,
            'task_total': task_total,
            'progress': progress,
            'members': member_entries,
            'status_color': get_status_badge_color(project.status),
            'current_membership': membership,
            'is_manager': bool(membership and membership.is_manager),
        })

    upcoming_deadlines = list(
        user_tasks.exclude(status=Task.STATUS_COMPLETED)
        .filter(due_date__isnull=False)
        .order_by('due_date')[:4]
    )
    recent_activity = list(
        ActivityLog.objects.select_related('user', 'project', 'task').filter(
            Q(user=user) | Q(project__project_members__user=user)
        ).distinct().order_by('-timestamp')[:4]
    )
    admin_snapshot = None
    if (user.role or "").lower() == 'admin':
        admin_snapshot = {
            'projects': Project.objects.count(),
            'users': Users.objects.count(),
            'tasks': Task.objects.count(),
            'memberships': ProjectMember.objects.count(),
        }

    timeline_projects = []
    managed_timeline_qs = Project.objects.all() if (user.role or "").lower() == 'admin' else Project.objects.filter(manager=user)
    for timeline_project in managed_timeline_qs.order_by('start_date', 'end_date')[:6]:
        start_date = timeline_project.start_date
        end_date = timeline_project.end_date or start_date
        total_days = max((end_date - start_date).days, 1)
        elapsed_days = (today_date - start_date).days
        elapsed_percent = max(0, min(100, round((elapsed_days / total_days) * 100)))
        timeline_projects.append({
            'project': timeline_project,
            'start_label': start_date.strftime('%b %d'),
            'end_label': end_date.strftime('%b %d'),
            'elapsed_percent': elapsed_percent,
            'duration_days': total_days,
        })

    team_members = []
    seen_memberships = set()
    for project in projects:
        for member in project.project_members.select_related('user').all():
            key = (member.project_id, member.user_id)
            if key in seen_memberships:
                continue
            seen_memberships.add(key)
            team_members.append({
                'project': project,
                **build_member_entry(member, current_user_id=user.id),
            })
            if len(team_members) >= 6:
                break
        if len(team_members) >= 6:
            break

    budget_visible_projects = [project for project in accessible_projects if can_view_project_budget(project, user)]
    budget_rows, budget_total, budget_actual = build_budget_rows(budget_visible_projects[:6], user)
    budget_remaining_total = budget_total - budget_actual
    budget_usage_percent = min(100, round((budget_actual / budget_total) * 100)) if budget_total else 0

    context = build_dashboard_base_context(request, user)
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
        "admin_snapshot": admin_snapshot,
        "dashboard_chart_data": [completed_tasks, in_progress_tasks, pending_tasks],
        "timeline_projects": timeline_projects,
        "dashboard_budget_rows": budget_rows[:4],
        "dashboard_budget_total": budget_total,
        "dashboard_budget_actual": budget_actual,
        "dashboard_budget_remaining": budget_remaining_total,
        "dashboard_budget_usage_percent": budget_usage_percent,
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
    if not has_project_full_access(project, user):
        messages.error(request, 'Only the project owner or manager can create tasks for this project.')
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

    projects_qs = get_accessible_projects(user)
    status_filter = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    if status_filter in {choice[0] for choice in Project.STATUS_CHOICES}:
        projects_qs = projects_qs.filter(status=status_filter)

    if date_from:
        projects_qs = projects_qs.filter(start_date__gte=date_from)

    if date_to:
        projects_qs = projects_qs.filter(
            Q(end_date__lte=date_to) | Q(end_date__isnull=True, start_date__lte=date_to)
        )
    project_cards = []
    for project in projects_qs:
        summary = build_project_summary(project)
        membership = get_project_membership(project, user)
        summary.update({
            'current_membership': membership,
            'can_manage': has_project_full_access(project, user),
            'can_view_budget': can_view_project_budget(project, user),
            'member_entries': [
                build_member_entry(member, current_user_id=user.id)
                for member in project.project_members.select_related('user').all()
            ],
        })
        project_cards.append(summary)

    budget_visible_projects = [project for project in project_cards if project['can_view_budget']]
    total_budget = sum((item['object'].budget or 0) for item in budget_visible_projects)
    status_counts = projects_qs.aggregate(
        total=Count('id'),
        in_progress=Count('id', filter=Q(status=Project.STATUS_IN_PROGRESS)),
        planned=Count('id', filter=Q(status=Project.STATUS_PLANNED)),
        completed=Count('id', filter=Q(status=Project.STATUS_COMPLETED)),
        on_hold=Count('id', filter=Q(status=Project.STATUS_ON_HOLD)),
    )

    context = build_dashboard_base_context(request, user)
    context.update({
        'projects': project_cards,
        'project_status_counts': status_counts,
        'project_total_budget': total_budget,
        'active_project_filters': {
            'status': status_filter,
            'date_from': date_from,
            'date_to': date_to,
        },
        'team_options': Users.objects.exclude(id=user.id).order_by('first_name', 'last_name', 'username'),
        'project_role_options': get_project_role_options(),
        'project_color_options': ['#4f7cff', '#7c5cfc', '#30d87d', '#ffb547', '#ff5470', '#00d4aa', '#e06030', '#8b5cf6'],
        'project_icon_options': ['globe', 'server', 'diagram-3', 'people', 'phone', 'bar-chart-line', 'shield-lock', 'lightning-charge', 'brush', 'gear'],
    })
    return render(request, 'dashboard/projects.html', context)


def tasks(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    today_date = timezone.localdate()
    user_tasks = Task.objects.select_related('project', 'assigned_to').annotate(
        comment_count=Count('comments')
    ).filter(assigned_to=user).order_by(
        Case(
            When(status=Task.STATUS_COMPLETED, then=1),
            default=0,
            output_field=IntegerField(),
        ),
        'due_date',
        '-created_at',
    )

    task_status_counts = {
        'total': user_tasks.count(),
        'todo': user_tasks.filter(status=Task.STATUS_TODO).count(),
        'in_progress': user_tasks.filter(status=Task.STATUS_IN_PROGRESS).count(),
        'completed': user_tasks.filter(status=Task.STATUS_COMPLETED).count(),
        'overdue': user_tasks.exclude(status=Task.STATUS_COMPLETED).filter(due_date__lt=today_date).count(),
    }

    task_priority_counts = {
        'high': user_tasks.filter(priority=Task.PRIORITY_HIGH).count(),
        'medium': user_tasks.filter(priority=Task.PRIORITY_MEDIUM).count(),
        'low': user_tasks.filter(priority=Task.PRIORITY_LOW).count(),
    }

    context = build_dashboard_base_context(request, user)
    context.update({
        'tasks': user_tasks,
        'task_status_counts': task_status_counts,
        'task_priority_counts': task_priority_counts,
        'today_date': today_date,
    })
    return render(request, 'dashboard/tasks.html', context)


def budget_tracking(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    project = get_default_finance_project(user)
    if not project:
        messages.info(request, 'Create or join a project to use Budget Management.')
        return redirect('projects')
    return redirect('project_budget', project_id=project.id)


def project_budget(request, project_id):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    project = get_accessible_projects(user).filter(id=project_id).first()
    if not project:
        messages.error(request, 'Project budget not found.')
        return redirect('projects')

    is_owner_finance = can_manage_project_finances(project, user)
    active_tab = request.GET.get('tab', 'all').strip() or 'all'
    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    date_from = request.GET.get('date_from', '').strip()
    date_to = request.GET.get('date_to', '').strip()

    transactions = Expense.objects.select_related(
        'project',
        'assigned_user',
    ).filter(project=project).order_by('-issue_date', '-created_at')

    if is_owner_finance:
        if active_tab == 'salary':
            transactions = transactions.filter(assigned_user__isnull=False)
        elif active_tab in {Expense.TYPE_INCOME, Expense.TYPE_EXPENSE}:
            transactions = transactions.filter(transaction_type=active_tab)

        if search_query:
            transactions = transactions.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(reference_id__icontains=search_query)
                | Q(assigned_user__first_name__icontains=search_query)
                | Q(assigned_user__last_name__icontains=search_query)
                | Q(assigned_user__username__icontains=search_query)
                | Q(assigned_user__email__icontains=search_query)
            )
    else:
        transactions = transactions.filter(assigned_user=user)
        if active_tab not in {'all', 'paid', 'pending'}:
            active_tab = 'all'
        if active_tab == 'paid':
            transactions = transactions.filter(status=Expense.STATUS_PAID)
        elif active_tab == 'pending':
            transactions = transactions.exclude(status=Expense.STATUS_PAID)

        if search_query:
            transactions = transactions.filter(
                Q(title__icontains=search_query)
                | Q(description__icontains=search_query)
                | Q(reference_id__icontains=search_query)
            )

    if status_filter in {choice[0] for choice in Expense.PAYMENT_STATUS_CHOICES}:
        transactions = transactions.filter(status=status_filter)

    if date_from:
        transactions = transactions.filter(issue_date__gte=date_from)

    if date_to:
        transactions = transactions.filter(issue_date__lte=date_to)

    transaction_list = list(transactions)
    finance_rows, finance_income_total, finance_expense_total, finance_salary_total, finance_net_total = build_finance_rows(transaction_list)
    paid_count = sum(1 for item in finance_rows if item['status'] == Expense.STATUS_PAID)
    overdue_count = sum(1 for item in finance_rows if item['status'] == Expense.STATUS_OVERDUE)
    pending_count = sum(1 for item in finance_rows if item['status'] == Expense.STATUS_PENDING)

    if is_owner_finance and request.GET.get('export') == 'csv':
        response = HttpResponse(content_type='text/csv')
        response['Content-Disposition'] = f'attachment; filename="taskly-budget-{project.id}.csv"'
        response.write('Title,Kind,Category,Paid To,Reference ID,Issue Date,Paid Date,Status,Amount\r\n')
        for item in finance_rows:
            response.write(
                f'"{item["title"]}","{item["entry_kind_label"]}","{item["category_name"]}","{item["assigned_user_name"]}","{item["reference_id"]}","{item["issue_date"] or ""}","{item["paid_date"] or ""}","{item["status_label"]}","{item["amount"]}"\r\n'
            )
        return response

    expense_total = project.expenses.filter(transaction_type=Expense.TYPE_EXPENSE).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    income_total = project.expenses.filter(transaction_type=Expense.TYPE_INCOME).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    remaining_balance = (project.budget or Decimal('0')) + income_total - expense_total
    budget_usage_percent = min(100, round((expense_total / project.budget) * 100)) if project.budget else 0
    project_members = list(project.project_members.select_related('user').all())
    owner_projects = list(get_budget_visible_projects(user)) if is_owner_finance else [project]
    finance_project_member_map = {}
    for finance_project in owner_projects:
        finance_project_member_map[str(finance_project.id)] = [
            {
                'id': member.user.id,
                'name': member.user.display_name,
                'role': member.display_role,
            }
            for member in finance_project.project_members.select_related('user').all()
            if not member.is_manager
        ]

    context = build_dashboard_base_context(request, user)
    context.update({
        'project': project,
        'is_owner_finance': is_owner_finance,
        'can_view_project_budget': can_view_project_budget(project, user),
        'budget_total': project.budget or Decimal('0'),
        'finance_income_total': finance_income_total if is_owner_finance else Decimal('0'),
        'finance_expense_total': finance_expense_total if is_owner_finance else Decimal('0'),
        'finance_salary_total': finance_salary_total,
        'budget_remaining_total': remaining_balance,
        'budget_usage_percent': budget_usage_percent,
        'finance_rows': finance_rows,
        'finance_transaction_count': len(finance_rows),
        'finance_paid_count': paid_count,
        'finance_pending_count': pending_count,
        'finance_overdue_count': overdue_count,
        'finance_active_tab': active_tab,
        'finance_filters': {
            'search': search_query,
            'status': status_filter,
            'date_from': date_from,
            'date_to': date_to,
        },
        'finance_status_choices': Expense.PAYMENT_STATUS_CHOICES,
        'finance_entry_kind_choices': FINANCE_ENTRY_KIND_CHOICES,
        'finance_team_members': [member for member in project_members if not member.is_manager],
        'finance_project_options': owner_projects,
        'finance_project_member_map': finance_project_member_map,
        'finance_transactions_url': get_project_budget_url(project),
        'project_budget_income_total': income_total,
        'project_budget_expense_total': expense_total,
        'project_salary_latest_date': next((item['paid_date'] for item in finance_rows if item['paid_date']), None),
        'project_budget_membership': get_project_membership(project, user),
    })
    return render(request, 'dashboard/budget_tracking.html', context)


def employees(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    search_query = request.GET.get('search', '').strip()
    selected_employee_id = request.GET.get('employee', '').strip()
    detail_tab = request.GET.get('detail_tab', 'projects').strip() or 'projects'
    if detail_tab not in {'projects', 'details'}:
        detail_tab = 'projects'

    employee_users = Users.objects.filter(project_memberships__isnull=False).distinct()
    if search_query:
        employee_users = employee_users.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(role__icontains=search_query)
            | Q(project_memberships__project__name__icontains=search_query)
        )

    employee_rows = build_user_directory_rows(employee_users, include_profiles=True)
    for row in employee_rows:
        profile = row['profile'] or ensure_employee_profile(row['user'])
        row['profile'] = profile
        row['salary_display'] = profile.salary
        row['status_badge_class'] = get_profile_badge_class(profile.status)

    paginator = Paginator(employee_rows, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    selected_employee = None

    if selected_employee_id:
        selected_employee = next((row for row in employee_rows if str(row['user'].id) == selected_employee_id), None)

    if not selected_employee and page_obj.object_list:
        selected_employee = page_obj.object_list[0]

    assignment_rows = []
    detail_profile = None

    if selected_employee:
        detail_profile = selected_employee['profile']
        memberships = ProjectMember.objects.select_related('project').filter(user=selected_employee['user']).order_by('-assignment_start_date', '-joined_at')
        for membership in memberships:
            start_date = membership.assignment_start_date or membership.project.start_date
            end_date = membership.assignment_end_date or membership.project.end_date
            total_days = ''
            if start_date and end_date:
                total_days = max((end_date - start_date).days + 1, 1)
            project_tasks = membership.project.tasks.count()
            completed_tasks = membership.project.tasks.filter(status=Task.STATUS_COMPLETED).count()
            progress = round((completed_tasks / project_tasks) * 100) if project_tasks else 0
            assignment_rows.append({
                'membership': membership,
                'project': membership.project,
                'progress': progress,
                'status_label': (membership.assignment_status or 'active').replace('_', ' ').title(),
                'status_badge_class': get_assignment_badge_class(membership.assignment_status),
                'start_date': start_date,
                'end_date': end_date,
                'total_days': total_days,
            })

    context = build_dashboard_base_context(request, user)
    context.update({
        'employee_page_obj': page_obj,
        'employee_search': search_query,
        'selected_employee': selected_employee,
        'employee_detail_tab': detail_tab,
        'employee_assignment_rows': assignment_rows,
        'employee_type_choices': EmployeeProfile.EMPLOYEE_TYPE_CHOICES,
        'employee_status_choices': EmployeeProfile.EMPLOYMENT_STATUS_CHOICES,
        'assignment_status_choices': [
            ('active', 'Active'),
            ('planned', 'Planned'),
            ('on_hold', 'On Hold'),
            ('completed', 'Completed'),
        ],
    })
    return render(request, 'dashboard/employees.html', context)


def users(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    search_query = request.GET.get('search', '').strip()
    selected_user_id = request.GET.get('user', '').strip()

    all_users = Users.objects.all()
    if search_query:
        all_users = all_users.filter(
            Q(first_name__icontains=search_query)
            | Q(last_name__icontains=search_query)
            | Q(username__icontains=search_query)
            | Q(email__icontains=search_query)
            | Q(role__icontains=search_query)
        )

    user_rows = build_user_directory_rows(all_users, include_profiles=True)

    paginator = Paginator(user_rows, 8)
    page_obj = paginator.get_page(request.GET.get('page'))
    selected_user = None

    if selected_user_id:
        selected_user = next((row for row in user_rows if str(row['user'].id) == selected_user_id), None)

    if not selected_user and page_obj.object_list:
        selected_user = page_obj.object_list[0]

    context = build_dashboard_base_context(request, user)
    context.update({
        'user_page_obj': page_obj,
        'user_search': search_query,
        'selected_user': selected_user,
    })
    return render(request, 'dashboard/users.html', context)


def calendar(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    accessible_projects = list(
        get_accessible_projects(user)
        .prefetch_related('tasks__assigned_to', 'project_members__user')
        .order_by('start_date', 'name')
    )

    events = []
    legend_counts = []

    for project in accessible_projects:
        project_color = project.color or '#4f7cff'
        member_names = ", ".join(
            membership.user.display_name
            for membership in project.project_members.select_related('user').all()[:3]
        ) or 'Project team'

        project_events_added = 0
        board_url = reverse('project_board', args=[project.id])

        if project.start_date:
            events.append({
                'id': f'project-start-{project.id}',
                'title': f'{project.name} kickoff',
                'date': project.start_date.isoformat(),
                'time': '09:00',
                'project': project.name,
                'color': project_color,
                'type': 'project_start',
                'meta': 'Project start date',
                'team': member_names,
                'url': board_url,
            })
            project_events_added += 1

        if project.end_date:
            events.append({
                'id': f'project-end-{project.id}',
                'title': f'{project.name} deadline',
                'date': project.end_date.isoformat(),
                'time': '18:00',
                'project': project.name,
                'color': project_color,
                'type': 'project_deadline',
                'meta': 'Project deadline',
                'team': member_names,
                'url': board_url,
            })
            project_events_added += 1

        for task in project.tasks.select_related('assigned_to').all():
            if not task.due_date:
                continue

            assignee_name = task.assigned_to.display_name if task.assigned_to else 'Unassigned'
            events.append({
                'id': f'task-{task.id}',
                'title': task.title,
                'date': task.due_date.isoformat(),
                'time': '17:00',
                'project': project.name,
                'color': project_color,
                'type': 'task_due',
                'meta': f'Task due · {task.get_status_display()}',
                'team': assignee_name,
                'url': board_url,
            })
            project_events_added += 1

        legend_counts.append({
            'project': project,
            'count': project_events_added,
        })

    events.sort(key=lambda item: (item['date'], item['time'], item['title']))
    today = timezone.localdate()
    upcoming_events = [item for item in events if item['date'] >= today.isoformat()][:8]

    context = build_dashboard_base_context(request, user)
    context.update({
        'calendar_today': today.isoformat(),
        'calendar_events': events,
        'calendar_upcoming_events': upcoming_events,
        'calendar_project_legend': [item for item in legend_counts if item['count'] > 0][:6],
        'calendar_total_events': len(events),
        'calendar_total_projects': len(accessible_projects),
    })
    return render(request, 'dashboard/calendar.html', context)


def income_visualization(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    finance_projects = get_budget_visible_projects(user).order_by('name')
    if not finance_projects.exists():
        messages.info(request, 'Create or manage a project budget to view income analytics.')
        return redirect('projects')

    search_query = request.GET.get('search', '').strip()
    status_filter = request.GET.get('status', '').strip()
    project_filter = request.GET.get('project', '').strip()

    finance_entries = Expense.objects.select_related('project').filter(project__in=finance_projects)
    filtered_projects = finance_projects
    if project_filter:
        filtered_projects = finance_projects.filter(id=project_filter)
        finance_entries = finance_entries.filter(project_id=project_filter)

    incomes = finance_entries.filter(transaction_type=Expense.TYPE_INCOME)

    valid_statuses = {choice[0] for choice in Expense.PAYMENT_STATUS_CHOICES}
    if status_filter in valid_statuses:
        incomes = incomes.filter(status=status_filter)

    if search_query:
        incomes = incomes.filter(
            Q(title__icontains=search_query)
            | Q(description__icontains=search_query)
            | Q(reference_id__icontains=search_query)
            | Q(project__name__icontains=search_query)
        )

    visible_projects = list(filtered_projects)
    project_budget_map = {}
    budget_month_map = {}
    project_start_months = []
    project_budget_total = Decimal('0')
    for project in visible_projects:
        budget_amount = project.budget or Decimal('0')
        project_budget_map[project.id] = budget_amount
        project_budget_total += budget_amount

        start_month = project.start_date.replace(day=1) if project.start_date else None
        if start_month:
            project_start_months.append(start_month)
            if budget_amount:
                budget_month_map[start_month] = budget_month_map.get(start_month, Decimal('0')) + budget_amount

    income_list = list(incomes.order_by('-issue_date', '-created_at'))
    income_rows, income_total, _, _, income_net_total = build_finance_rows(income_list)
    income_total += project_budget_total
    paid_income_total = sum(item['amount'] for item in income_rows if item['status'] == Expense.STATUS_PAID)
    pending_income_total = sum(item['amount'] for item in income_rows if item['status'] != Expense.STATUS_PAID)
    total_expense_amount = finance_entries.filter(transaction_type=Expense.TYPE_EXPENSE).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    total_profit_amount = income_total - total_expense_amount

    current_month = timezone.localdate().replace(day=1)
    monthly_income_total = (
        (incomes.filter(issue_date__gte=current_month).aggregate(total=Sum('amount'))['total'] or Decimal('0'))
        + budget_month_map.get(current_month, Decimal('0'))
    )
    monthly_expense_total = finance_entries.filter(
        transaction_type=Expense.TYPE_EXPENSE,
        issue_date__gte=current_month,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    monthly_profit_total = monthly_income_total - monthly_expense_total

    project_totals_qs = list(
        incomes.values('project_id', 'project__name', 'project__color')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('-total', 'project__name')
    )
    project_totals_map = {
        project.id: {
            'project_id': project.id,
            'project_name': project.name,
            'project_color': project.color or '#4f7cff',
            'total': project_budget_map.get(project.id, Decimal('0')),
            'count': 0,
            'budget_amount': project_budget_map.get(project.id, Decimal('0')),
        }
        for project in visible_projects
    }
    for item in project_totals_qs:
        row = project_totals_map.setdefault(item['project_id'], {
            'project_id': item['project_id'],
            'project_name': item['project__name'],
            'project_color': item['project__color'] or '#4f7cff',
            'total': Decimal('0'),
            'count': 0,
            'budget_amount': Decimal('0'),
        })
        row['project_name'] = item['project__name']
        row['project_color'] = item['project__color'] or row['project_color']
        row['total'] += item['total'] or Decimal('0')
        row['count'] = item['count']

    ordered_project_totals = sorted(
        project_totals_map.values(),
        key=lambda item: (-(item['total'] or Decimal('0')), item['project_name'].lower()),
    )
    highest_project_total = max((item['total'] or Decimal('0') for item in ordered_project_totals), default=Decimal('0'))
    project_income_rows = []
    for item in ordered_project_totals:
        total = item['total'] or Decimal('0')
        percent = round((total / highest_project_total) * 100) if highest_project_total else 0
        project_income_rows.append({
            'project_id': item['project_id'],
            'project_name': item['project_name'],
            'project_color': item['project_color'] or '#4f7cff',
            'total': total,
            'count': item['count'],
            'budget_amount': item['budget_amount'],
            'percent': percent,
        })

    month_totals_qs = list(
        incomes.annotate(month=TruncMonth('issue_date'))
        .values('month')
        .annotate(total=Sum('amount'), count=Count('id'))
        .order_by('month')
    )
    income_month_map = {item['month']: item['total'] or Decimal('0') for item in month_totals_qs if item['month']}
    income_month_count_map = {item['month']: item['count'] for item in month_totals_qs if item['month']}
    for month, budget_total in budget_month_map.items():
        income_month_map[month] = income_month_map.get(month, Decimal('0')) + budget_total
    highest_month_total = max(income_month_map.values(), default=Decimal('0'))
    monthly_income_rows = []
    for month in sorted(income_month_map.keys())[-6:]:
        total = income_month_map.get(month, Decimal('0'))
        percent = round((total / highest_month_total) * 100) if highest_month_total else 0
        monthly_income_rows.append({
            'label': month.strftime('%b %Y'),
            'total': total,
            'count': income_month_count_map.get(month, 0),
            'percent': percent,
        })

    monthly_expense_totals_qs = list(
        finance_entries.filter(transaction_type=Expense.TYPE_EXPENSE)
        .annotate(month=TruncMonth('issue_date'))
        .values('month')
        .annotate(total=Sum('amount'))
        .order_by('month')
    )
    expense_month_map = {item['month']: item['total'] or Decimal('0') for item in monthly_expense_totals_qs if item['month']}

    def iter_months(start_month, end_month):
        cursor = start_month
        while cursor <= end_month:
            yield cursor
            next_month = cursor.month + 1
            next_year = cursor.year
            if next_month > 12:
                next_month = 1
                next_year += 1
            cursor = date(next_year, next_month, 1)

    chart_month_candidates = [
        *income_month_map.keys(),
        *expense_month_map.keys(),
        *budget_month_map.keys(),
        current_month,
    ]
    first_project_month = min(project_start_months, default=None)
    last_chart_month = max(chart_month_candidates, default=current_month)
    if first_project_month:
        combined_months = list(iter_months(first_project_month, last_chart_month))
    else:
        combined_months = sorted({month for month in chart_month_candidates if month})
    combined_months = combined_months[-12:]

    pnl_max_total = max(
        [income_month_map.get(month, Decimal('0')) + expense_month_map.get(month, Decimal('0')) for month in combined_months],
        default=Decimal('0')
    )
    profit_max_total = max(
        [abs(income_month_map.get(month, Decimal('0')) - expense_month_map.get(month, Decimal('0'))) for month in combined_months],
        default=Decimal('0')
    )
    pnl_chart_rows = []
    for month in combined_months:
        income_value = income_month_map.get(month, Decimal('0'))
        expense_value = expense_month_map.get(month, Decimal('0'))
        profit_value = income_value - expense_value
        pnl_chart_rows.append({
            'label': month.strftime('%b'),
            'full_label': month.strftime('%b %Y'),
            'income': income_value,
            'expense': expense_value,
            'profit': profit_value,
            'income_height': round((income_value / pnl_max_total) * 100) if pnl_max_total else 0,
            'expense_height': round((expense_value / pnl_max_total) * 100) if pnl_max_total else 0,
            'profit_point': round((profit_value / profit_max_total) * 100) if profit_max_total and profit_value > 0 else 0,
            'show_profit_marker': bool(profit_value > 0 and profit_max_total),
        })

    previous_month_start = (current_month.replace(day=1) - timedelta(days=1)).replace(day=1)
    previous_month_income_total = (
        (incomes.filter(issue_date__gte=previous_month_start, issue_date__lt=current_month).aggregate(total=Sum('amount'))['total'] or Decimal('0'))
        + budget_month_map.get(previous_month_start, Decimal('0'))
    )
    previous_month_expense_total = finance_entries.filter(
        transaction_type=Expense.TYPE_EXPENSE,
        issue_date__gte=previous_month_start,
        issue_date__lt=current_month,
    ).aggregate(total=Sum('amount'))['total'] or Decimal('0')
    previous_month_profit_total = previous_month_income_total - previous_month_expense_total

    def build_change(current_value, previous_value):
        if previous_value:
            delta = ((current_value - previous_value) / previous_value) * 100
            return round(delta, 1)
        return 100.0 if current_value else 0.0

    leading_project = project_income_rows[0] if project_income_rows else None

    context = build_dashboard_base_context(request, user)
    context.update({
        'income_rows': income_rows,
        'income_total': income_total,
        'income_budget_total': project_budget_total,
        'income_paid_total': paid_income_total,
        'income_pending_total': pending_income_total,
        'income_month_total': monthly_income_total,
        'income_net_total': income_net_total,
        'income_total_expense_amount': total_expense_amount,
        'income_total_profit_amount': total_profit_amount,
        'income_month_expense_total': monthly_expense_total,
        'income_month_profit_total': monthly_profit_total,
        'income_project_rows': project_income_rows[:6],
        'income_monthly_rows': monthly_income_rows,
        'income_pnl_chart_rows': pnl_chart_rows,
        'income_leading_project': leading_project,
        'income_transaction_count': len(income_rows),
        'income_status_choices': Expense.PAYMENT_STATUS_CHOICES,
        'income_project_options': finance_projects,
        'income_current_month_label': current_month.strftime('%b %Y'),
        'income_revenue_change': build_change(monthly_income_total, previous_month_income_total),
        'income_expense_change': build_change(monthly_expense_total, previous_month_expense_total),
        'income_profit_change': build_change(monthly_profit_total, previous_month_profit_total),
        'income_filters': {
            'search': search_query,
            'status': status_filter,
            'project': project_filter,
        },
    })
    return render(request, 'dashboard/income_visualization.html', context)


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
    if not has_project_full_access(project, user):
        messages.error(request, 'Only the project owner or manager can update this project.')
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
    elif not can_transition_project_status(project.status, status):
        messages.error(
            request,
            f'Project status can only move from {project.status_label} to a valid next stage.',
        )
        return redirect('projects')

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
    if not has_project_full_access(project, user):
        messages.error(request, 'Only the project owner or manager can manage team members.')
        return redirect('projects')

    selected_member_ids = {int(member_id) for member_id in request.POST.getlist('members') if member_id.isdigit()}
    selected_member_ids.add(project.manager_id or user.id)
    role_map = {}
    for member_id in selected_member_ids:
        role_map[member_id] = normalize_project_role_value(
            request.POST.get(f'role_{member_id}', ''),
            is_manager=member_id == (project.manager_id or user.id),
        )

    current_members = {membership.user_id: membership for membership in project.project_members.all()}

    for member_id, membership in current_members.items():
        if member_id not in selected_member_ids and member_id != project.manager_id:
            membership.delete()

    valid_users = Users.objects.filter(id__in=selected_member_ids)
    for member in valid_users:
        is_manager_member = member.id == project.manager_id
        if member.id not in current_members:
            ProjectMember.objects.create(
                project=project,
                user=member,
                role=role_map.get(member.id, 'Project Manager' if is_manager_member else 'Team Member'),
                is_manager=is_manager_member,
            )
        else:
            membership = current_members[member.id]
            membership.role = role_map.get(member.id, membership.role)
            membership.is_manager = is_manager_member
            membership.save(update_fields=['role', 'is_manager'])

    sync_project_manager_membership(project, user if project.manager_id is None else project.manager)

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
    if not has_project_full_access(project, user):
        messages.error(request, 'Only the project owner or manager can delete this project.')
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

    project = Project.objects.select_related('manager', 'owner').prefetch_related(
        'tasks__assigned_to',
        'tasks__comments__user',
        'project_members__user',
        'activity_logs__user',
    ).filter(id=project_id).first()

    if not project:
        messages.error(request, 'Project not found.')
        return redirect('projects')
    if not is_project_member(project, user):
        messages.error(request, 'You do not have access to this project.')
        return redirect('projects')

    ensure_default_expense_categories(project)

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
    project_files = list(project.files.select_related('uploaded_by').all()[:8])
    can_view_budget = can_view_project_budget(project, user)
    project_expenses = list(project.expenses.filter(transaction_type=Expense.TYPE_EXPENSE).order_by('-created_at')[:6]) if can_view_budget else []
    total_actual_expenses = project.expenses.filter(transaction_type=Expense.TYPE_EXPENSE).aggregate(total=Sum('amount'))['total'] or Decimal('0') if can_view_budget else Decimal('0')
    budget_remaining = project.budget - total_actual_expenses if can_view_budget else Decimal('0')

    context = build_dashboard_base_context(request, user)
    context.update({
        'project': project,
        'project_summary': summary,
        'project_memberships': [
            build_member_entry(member, current_user_id=user.id)
            for member in project.project_members.select_related('user').all()
        ],
        'current_project_membership': get_project_membership(project, user),
        'can_manage_project': has_project_full_access(project, user),
        'can_view_project_budget': can_view_project_budget(project, user),
        'board_columns': [
            {'key': Task.STATUS_TODO, 'label': 'To Do', 'tasks': task_columns[Task.STATUS_TODO], 'icon': 'list-task'},
            {'key': Task.STATUS_IN_PROGRESS, 'label': 'In Progress', 'tasks': task_columns[Task.STATUS_IN_PROGRESS], 'icon': 'activity'},
            {'key': Task.STATUS_COMPLETED, 'label': 'Completed', 'tasks': task_columns[Task.STATUS_COMPLETED], 'icon': 'patch-check'},
        ],
        'project_recent_activity': recent_activity,
        'project_files': project_files,
        'project_expenses': project_expenses,
        'project_actual_expenses': total_actual_expenses,
        'project_budget_remaining': budget_remaining,
        'project_budget_usage_percent': min(100, round((total_actual_expenses / project.budget) * 100)) if can_view_budget and project.budget else 0,
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

    next_url = request.POST.get('next', '').strip() or 'projects'

    task = Task.objects.select_related('project').filter(id=task_id).first()
    if not task:
        messages.error(request, 'Task not found.')
        return redirect('projects')
    if not is_project_member(task.project, user):
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'You do not have access to this task.'}, status=403)
        messages.error(request, 'You do not have access to this task.')
        return redirect('projects')
    if not has_project_full_access(task.project, user) and task.assigned_to_id != user.id:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Only the assignee or project manager can update this task.'}, status=403)
        messages.error(request, 'Only the assignee or project manager can update this task.')
        return redirect(next_url)

    new_status = request.POST.get('status', '').strip()
    valid_statuses = {choice[0] for choice in Task.STATUS_CHOICES}

    if new_status not in valid_statuses:
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': 'Invalid task status.'}, status=400)
        messages.error(request, 'Invalid task status.')
        return redirect(next_url)

    if not can_transition_task_status(task.status, new_status):
        message = f'Task status cannot move directly from {task.get_status_display()} to {dict(Task.STATUS_CHOICES).get(new_status, new_status)}.'
        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({'success': False, 'message': message}, status=400)
        messages.error(request, message)
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
    if not is_project_member(task.project, user):
        return JsonResponse({'success': False, 'message': 'You do not have access to this task.'}, status=403)

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
    if not has_project_full_access(task.project, user):
        return JsonResponse({'success': False, 'message': 'Only the project owner or manager can edit task details.'}, status=403)

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
    if not can_transition_task_status(task.status, status):
        return JsonResponse({
            'success': False,
            'message': f'Task status cannot move directly from {task.get_status_display()} to {dict(Task.STATUS_CHOICES).get(status, status)}.',
        }, status=400)

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

    previous_assigned_to_id = task.assigned_to_id

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
    if not is_project_member(task.project, user):
        return JsonResponse({'success': False, 'message': 'You do not have access to this task.'}, status=403)

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

    for mentioned_user in get_user_mentions(comment_text):
        if mentioned_user.id == user.id:
            continue
        if not is_project_member(task.project, mentioned_user):
            continue
        ActivityLog.objects.create(
            user=user,
            action=f'mentioned @{mentioned_user.username} in a comment on "{task.title}"',
            project=task.project,
            task=task,
        )
        send_user_email_notification(
            mentioned_user,
            f'You were mentioned in {task.title}',
            (
                f'Hi {mentioned_user.display_name},\n\n'
                f'{user.display_name} mentioned you in a comment on "{task.title}" '
                f'for project "{task.project.name}".\n\n'
                f'Comment:\n{comment_text}\n\n'
                'Open Taskly to reply.'
            ),
        )

    return JsonResponse({
        'success': True,
        'message': 'Comment added.',
        'comment': {
            'id': comment.id,
            'user_id': user.id,
            'user_name': user.display_name,
            'user_initials': user.initials,
            'user_avatar_url': user.avatar_url,
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
    if not has_project_full_access(task.project, user):
        return JsonResponse({'success': False, 'message': 'Only the project owner or manager can delete this task.'}, status=403)

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
def upload_project_file(request, project_id):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    project = Project.objects.filter(id=project_id).first()
    if not project or not is_project_member(project, user):
        messages.error(request, 'You do not have access to this project.')
        return redirect('projects')

    uploaded_file = request.FILES.get('project_file')
    next_view = request.POST.get('next', '').strip()
    if not uploaded_file:
        messages.error(request, 'Please choose a file to upload.')
        return redirect(next_view or reverse('project_board', args=[project.id]))

    project_files_dir = os.path.join(settings.MEDIA_ROOT, "project_files", str(project.id))
    os.makedirs(project_files_dir, exist_ok=True)
    safe_name = os.path.basename(uploaded_file.name or "file")
    file_path = os.path.join(project_files_dir, safe_name)
    relative_path = os.path.relpath(file_path, settings.MEDIA_ROOT).replace(os.sep, "/")

    with open(file_path, "wb+") as destination:
        for chunk in uploaded_file.chunks():
            destination.write(chunk)

    ProjectFile.objects.create(
        project=project,
        uploaded_by=user,
        file=relative_path,
    )
    ActivityLog.objects.create(
        user=user,
        action=f'uploaded file "{safe_name}"',
        project=project,
    )
    messages.success(request, 'Project file uploaded successfully.')
    return redirect(next_view or reverse('project_board', args=[project.id]))


def download_project_file(request, file_id):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    project_file = ProjectFile.objects.select_related('project').filter(id=file_id).first()
    if not project_file or not is_project_member(project_file.project, user):
        raise Http404("File not found.")

    absolute_path = get_project_file_absolute_path(project_file)
    if not os.path.exists(absolute_path):
        raise Http404("File not found.")

    return FileResponse(open(absolute_path, "rb"), as_attachment=True, filename=os.path.basename(absolute_path))


@require_POST
@csrf_protect
def add_project_expense(request, project_id):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    project = Project.objects.filter(id=project_id).first()
    if not project or not can_manage_project_finances(project, user):
        messages.error(request, 'Only the project owner can add expenses.')
        return redirect('projects')

    next_view = request.POST.get('next', '').strip()
    description = request.POST.get('description', '').strip()
    amount_raw = request.POST.get('amount', '').strip()
    category_id = request.POST.get('category', '').strip()
    if not description or not amount_raw or not category_id:
        messages.error(request, 'Expense category, description, and amount are required.')
        return redirect(next_view or get_project_budget_url(project))

    try:
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError):
        messages.error(request, 'Expense amount must be a valid positive number.')
        return redirect(next_view or get_project_budget_url(project))

    category = ExpenseCategory.objects.filter(id=category_id, project=project).first()
    if not category:
        messages.error(request, 'Please choose a valid expense category.')
        return redirect(next_view or get_project_budget_url(project))

    Expense.objects.create(
        project=project,
        category=category,
        title=description,
        description=description,
        amount=amount,
        transaction_type=Expense.TYPE_EXPENSE,
        status=Expense.STATUS_PAID,
        issue_date=timezone.localdate(),
        paid_date=timezone.localdate(),
    )
    ActivityLog.objects.create(
        user=user,
        action=f'logged expense "{description}" under {category.name}',
        project=project,
    )
    messages.success(request, 'Expense added successfully.')
    return redirect(next_view or get_project_budget_url(project))


@require_POST
@csrf_protect
def create_expense_category(request, project_id):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    project = Project.objects.filter(id=project_id).first()
    if not project or not can_manage_project_finances(project, user):
        messages.error(request, 'Only the project owner can create expense categories.')
        return redirect('projects')

    next_view = request.POST.get('next', '').strip()
    category_name = normalize_category_name(request.POST.get('name', ''))
    if not category_name:
        messages.error(request, 'Category name is required.')
        return redirect(next_view or get_project_budget_url(project))

    category, created = ExpenseCategory.objects.get_or_create(
        project=project,
        name=category_name,
        defaults={'is_fixed': False},
    )
    if created:
        ActivityLog.objects.create(
            user=user,
            action=f'created expense category "{category.name}"',
            project=project,
        )
        messages.success(request, 'Expense category created successfully.')
    else:
        messages.info(request, 'That expense category already exists.')

    return redirect(next_view or get_project_budget_url(project))


@require_POST
@csrf_protect
def create_finance_transaction(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    next_view = request.POST.get('next', '').strip()
    title = request.POST.get('title', '').strip()
    project_id = request.POST.get('project', '').strip()
    entry_kind = request.POST.get('entry_kind', 'expense').strip()
    assigned_user_id = request.POST.get('assigned_user', '').strip()
    amount_raw = request.POST.get('amount', '').strip()
    status = request.POST.get('status', Expense.STATUS_PENDING).strip()
    issue_date = request.POST.get('issue_date', '').strip()
    paid_date = request.POST.get('paid_date', '').strip()
    description = request.POST.get('description', '').strip()

    project = get_accessible_projects(user).filter(id=project_id).first()
    if not project:
        messages.error(request, 'Please choose a valid project.')
        return redirect(next_view or reverse('projects'))
    if not can_manage_project_finances(project, user):
        messages.error(request, 'Only the project owner can add transactions.')
        return redirect(next_view or get_project_budget_url(project))
    if not next_view:
        next_view = get_project_budget_url(project)

    if not title:
        messages.error(request, 'Transaction title is required.')
        return redirect(next_view)

    try:
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError):
        messages.error(request, 'Amount must be a valid positive number.')
        return redirect(next_view)

    valid_statuses = {choice[0] for choice in Expense.PAYMENT_STATUS_CHOICES}
    if status not in valid_statuses:
        status = Expense.STATUS_PENDING

    assigned_user = None
    transaction_type = Expense.TYPE_EXPENSE
    if entry_kind == 'salary':
        assigned_user = Users.objects.filter(id=assigned_user_id, project_memberships__project=project).distinct().first()
        if not assigned_user:
            messages.error(request, 'Please choose a valid team member for the salary payment.')
            return redirect(next_view)
    else:
        transaction_type = Expense.TYPE_INCOME if entry_kind == 'income' else Expense.TYPE_EXPENSE

    transaction = Expense.objects.create(
        project=project,
        category=None,
        assigned_user=assigned_user,
        amount=amount,
        title=title,
        description=description or title,
        transaction_type=transaction_type,
        status=status,
        issue_date=parse_date(issue_date) if issue_date else None,
        paid_date=parse_date(paid_date) if paid_date else None,
        note=description or None,
    )
    ensure_transaction_reference_id(transaction)
    ActivityLog.objects.create(
        user=user,
        action=f'added a {"salary payment" if entry_kind == "salary" else entry_kind} transaction for "{project.name}"',
        project=project,
    )
    messages.success(request, 'Transaction saved successfully.')
    return redirect(next_view)


@require_POST
@csrf_protect
def update_finance_transaction(request, transaction_id):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    transaction = Expense.objects.select_related('project', 'assigned_user').filter(id=transaction_id).first()
    if not transaction or not can_manage_project_finances(transaction.project, user):
        messages.error(request, 'Transaction not found.')
        return redirect('projects')
    project_id = request.POST.get('project', '').strip()
    target_project = get_accessible_projects(user).filter(id=project_id).first() if project_id else transaction.project
    if not target_project or not can_manage_project_finances(target_project, user):
        messages.error(request, 'Please choose a valid project.')
        return redirect(get_project_budget_url(transaction.project))
    next_view = request.POST.get('next', '').strip() or get_project_budget_url(target_project)
    title = request.POST.get('title', '').strip()
    entry_kind = request.POST.get(
        'entry_kind',
        'salary' if transaction.is_salary_payment else ('income' if transaction.transaction_type == Expense.TYPE_INCOME else 'expense'),
    ).strip()
    amount_raw = request.POST.get('amount', '').strip()
    status = request.POST.get('status', transaction.status).strip()
    issue_date = request.POST.get('issue_date', '').strip()
    paid_date = request.POST.get('paid_date', '').strip()
    description = request.POST.get('description', '').strip()
    assigned_user_id = request.POST.get('assigned_user', '').strip()

    if not title:
        messages.error(request, 'Transaction title is required.')
        return redirect(next_view)

    try:
        amount = Decimal(amount_raw)
        if amount <= 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError):
        messages.error(request, 'Amount must be a valid positive number.')
        return redirect(next_view)

    assigned_user = None
    if entry_kind == 'salary':
        assigned_user = Users.objects.filter(id=assigned_user_id, project_memberships__project=target_project).distinct().first()
        if not assigned_user:
            messages.error(request, 'Please choose a valid team member for the salary payment.')
            return redirect(next_view)
        transaction_type = Expense.TYPE_EXPENSE
    else:
        transaction_type = Expense.TYPE_INCOME if entry_kind == 'income' else Expense.TYPE_EXPENSE

    transaction.project = target_project
    transaction.title = title
    transaction.description = description or title
    transaction.note = description or None
    transaction.transaction_type = transaction_type
    transaction.amount = amount
    transaction.status = status if status in {choice[0] for choice in Expense.PAYMENT_STATUS_CHOICES} else Expense.STATUS_PENDING
    transaction.issue_date = parse_date(issue_date) if issue_date else None
    transaction.paid_date = parse_date(paid_date) if paid_date else None
    transaction.category = None
    transaction.assigned_user = assigned_user
    transaction.save()
    ensure_transaction_reference_id(transaction)

    ActivityLog.objects.create(
        user=user,
        action=f'updated finance transaction "{transaction.display_title}"',
        project=transaction.project,
    )
    messages.success(request, 'Transaction updated successfully.')
    return redirect(next_view)


@require_POST
@csrf_protect
def create_employee(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    current_user = get_current_user(request)
    if not current_user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    first_name = request.POST.get('first_name', '').strip()
    last_name = request.POST.get('last_name', '').strip()
    username = request.POST.get('username', '').strip()
    email = request.POST.get('email', '').strip().lower()
    role = request.POST.get('role', '').strip() or 'employee'
    employee_type = request.POST.get('employee_type', EmployeeProfile.TYPE_FULL_TIME).strip()
    salary_raw = request.POST.get('salary', '').strip() or '0'
    join_date = request.POST.get('join_date', '').strip()
    status = request.POST.get('status', EmployeeProfile.STATUS_ACTIVE).strip()
    password = request.POST.get('password', '').strip() or 'taskly123'

    if not all([first_name, last_name, username, email]):
        messages.error(request, 'First name, last name, username, and email are required.')
        return redirect('employees')

    if Users.objects.filter(email__iexact=email).exists():
        messages.error(request, 'That email is already registered.')
        return redirect('employees')

    if Users.objects.filter(username__iexact=username).exists():
        messages.error(request, 'That username is already taken.')
        return redirect('employees')

    try:
        salary = Decimal(salary_raw)
        if salary < 0:
            raise InvalidOperation
    except (InvalidOperation, TypeError):
        messages.error(request, 'Salary must be a valid positive amount.')
        return redirect('employees')

    employee = Users(
        first_name=first_name,
        last_name=last_name,
        username=username,
        email=email,
        role=role,
        created_at=timezone.now(),
    )
    employee.set_password(password)
    employee.save()

    profile = EmployeeProfile.objects.create(
        user=employee,
        employee_type=employee_type if employee_type in {choice[0] for choice in EmployeeProfile.EMPLOYEE_TYPE_CHOICES} else EmployeeProfile.TYPE_FULL_TIME,
        salary=salary,
        join_date=parse_date(join_date) if join_date else timezone.localdate(),
        status=status if status in {choice[0] for choice in EmployeeProfile.EMPLOYMENT_STATUS_CHOICES} else EmployeeProfile.STATUS_ACTIVE,
    )
    EmployeePayroll.objects.create(
        employee=profile,
        month=date(timezone.localdate().year, timezone.localdate().month, 1),
        base_salary=salary,
        bonus=Decimal('0'),
        deduction=Decimal('0'),
        payment_status=EmployeePayroll.STATUS_PENDING,
    )
    ActivityLog.objects.create(
        user=current_user,
        action=f'added employee "{employee.display_name}"',
    )
    messages.success(request, 'Employee added successfully.')
    return redirect(f"{reverse('employees')}?employee={employee.id}")


@require_POST
@csrf_protect
def assign_employee_project(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    current_user = get_current_user(request)
    if not current_user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    employee_id = request.POST.get('employee', '').strip()
    project_id = request.POST.get('project', '').strip()
    assignment_status = request.POST.get('assignment_status', 'active').strip() or 'active'
    start_date = request.POST.get('start_date', '').strip()
    end_date = request.POST.get('end_date', '').strip()
    description = request.POST.get('description', '').strip()

    employee = Users.objects.filter(id=employee_id).first()
    project = get_accessible_projects(current_user).filter(id=project_id).first()
    if not employee or not project:
        messages.error(request, 'Please select a valid employee and project.')
        return redirect('employees')
    membership, created = ProjectMember.objects.get_or_create(
        project=project,
        user=employee,
        defaults={
            'role': employee.role.title() if employee.role else 'Team Member',
        },
    )
    membership.assignment_status = assignment_status
    membership.assignment_start_date = parse_date(start_date) if start_date else project.start_date
    membership.assignment_end_date = parse_date(end_date) if end_date else project.end_date
    membership.assignment_notes = description or None
    membership.save()

    ActivityLog.objects.create(
        user=current_user,
        action=f'{"assigned" if created else "updated assignment for"} "{employee.display_name}" on "{project.name}"',
        project=project,
    )
    messages.success(request, 'Project assignment saved successfully.')
    return redirect(f"{reverse('employees')}?employee={employee.id}&detail_tab=projects")

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
            owner=user,
            manager=user,
            status=status,
            color=color,
            icon=icon,
        )

        member_queryset = Users.objects.filter(id__in=member_ids).distinct()
        sync_project_manager_membership(project, user)
        ensure_default_expense_categories(project, user)

        existing_member_ids = {user.id}
        for member in member_queryset:
            if member.id in existing_member_ids:
                continue
            ProjectMember.objects.create(
                project=project,
                user=member,
                role=normalize_project_role_value(request.POST.get(f'role_{member.id}', '')),
                is_manager=False,
            )
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

@csrf_protect
def settings_view(request):
    if not request.session.get('user_id'):
        messages.warning(request, "Please login to continue.")
        return redirect('login')

    user = get_current_user(request)
    if not user:
        messages.error(request, "User not found.")
        request.session.flush()
        return redirect('login')

    timezone_name = request.session.get('user_timezone') or timezone.get_current_timezone_name()
    settings_zone = get_safe_timezone(timezone_name)
    settings_now = timezone.now().astimezone(settings_zone)
    managed_projects = get_accessible_projects(user).filter(manager=user).count()
    assigned_tasks = Task.objects.filter(assigned_to=user).count()

    if request.method == 'POST':
        action = request.POST.get('action', '').strip()

        if action == 'account':
            first_name = request.POST.get('first_name', '').strip()
            last_name = request.POST.get('last_name', '').strip()
            username = request.POST.get('username', '').strip()
            email = request.POST.get('email', '').strip().lower()
            selected_timezone = request.POST.get('timezone', '').strip() or timezone_name
            email_notifications_enabled = request.POST.get('email_notifications_enabled') == 'on'

            if not first_name or not last_name or not username or not email:
                messages.error(request, 'First name, last name, username, and email are required.')
                return redirect('settings')

            if Users.objects.exclude(id=user.id).filter(email__iexact=email).exists():
                messages.error(request, 'That email address is already in use.')
                return redirect('settings')

            if Users.objects.exclude(id=user.id).filter(username__iexact=username).exists():
                messages.error(request, 'That username is already taken.')
                return redirect('settings')

            user.first_name = first_name
            user.last_name = last_name
            user.username = username
            user.email = email
            user.email_notifications_enabled = email_notifications_enabled
            user.save(update_fields=['first_name', 'last_name', 'username', 'email', 'email_notifications_enabled'])

            request.session['user_email'] = user.email
            request.session['user_full_name'] = f"{user.first_name or ''} {user.last_name or ''}".strip()
            request.session['user_username'] = user.username
            request.session['user_timezone'] = selected_timezone

            ActivityLog.objects.create(
                user=user,
                action='updated account settings',
            )
            messages.success(request, 'Settings updated successfully.')
            return redirect('settings')

        if action == 'password':
            current_password = request.POST.get('current_password', '')
            new_password = request.POST.get('new_password', '')
            confirm_password = request.POST.get('confirm_password', '')

            if not current_password or not new_password or not confirm_password:
                messages.error(request, 'All password fields are required.')
                return redirect('settings')

            if not user.check_password(current_password):
                messages.error(request, 'Current password is incorrect.')
                return redirect('settings')

            if len(new_password) < 8:
                messages.error(request, 'New password must be at least 8 characters long.')
                return redirect('settings')

            if new_password != confirm_password:
                messages.error(request, 'New password and confirmation do not match.')
                return redirect('settings')

            user.set_password(new_password)
            user.save(update_fields=['password'])

            ActivityLog.objects.create(
                user=user,
                action='changed account password',
            )
            messages.success(request, 'Password updated successfully.')
            return redirect('settings')

    context = build_dashboard_base_context(request, user)
    context.update({
        'settings_timezone': timezone_name,
        'settings_timezone_label': f"{timezone_name.replace('_', ' ')} ({format_utc_offset(settings_now.utcoffset())})",
        'settings_joined': user.created_at.strftime('%b %d, %Y') if user.created_at else 'Recently',
        'settings_project_count': managed_projects,
        'settings_task_count': assigned_tasks,
        'settings_member_count': ProjectMember.objects.filter(user=user).count(),
        'settings_email_notification_count': EmailNotificationLog.objects.filter(
            user=user,
            status=EmailNotificationLog.STATUS_SENT,
        ).count(),
        'timezone_options': build_timezone_options(timezone_name),
    })
    return render(request, 'dashboard/settings.html', context)


@require_POST
@csrf_protect
def upload_settings_avatar(request):
    if not request.session.get('user_id'):
        return JsonResponse({'success': False, 'message': 'Authentication required.'}, status=401)

    user = get_current_user(request)
    if not user:
        request.session.flush()
        return JsonResponse({'success': False, 'message': 'User not found.'}, status=401)

    avatar = request.FILES.get('avatar')
    if not avatar:
        return JsonResponse({'success': False, 'message': 'Please choose an image.'}, status=400)

    extension = os.path.splitext(avatar.name or "")[1].lower().lstrip(".")
    allowed_extensions = {"jpg", "jpeg", "png", "webp", "gif"}
    if extension not in allowed_extensions or not (avatar.content_type or "").startswith("image/"):
        return JsonResponse({'success': False, 'message': 'Only image files are allowed.'}, status=400)

    avatar_dir = os.path.join(settings.MEDIA_ROOT, "profile_avatars")
    os.makedirs(avatar_dir, exist_ok=True)

    for old_ext in allowed_extensions:
        old_path = os.path.join(avatar_dir, f"user_{user.id}.{old_ext}")
        if os.path.exists(old_path):
            os.remove(old_path)

    file_path = os.path.join(avatar_dir, f"user_{user.id}.{extension}")
    with open(file_path, "wb+") as destination:
        for chunk in avatar.chunks():
            destination.write(chunk)

    ActivityLog.objects.create(
        user=user,
        action='updated account photo',
    )

    return JsonResponse({
        'success': True,
        'message': 'Photo updated successfully.',
        'user_id': user.id,
        'avatar_url': user.avatar_url,
        'user_initials': user.initials,
    })
