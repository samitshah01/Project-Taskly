import logging
import smtplib
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
from typing import Iterable
from email.message import EmailMessage

from django.conf import settings
from django.db import close_old_connections, transaction
from django.template.loader import render_to_string
from django.utils.dateparse import parse_date
from django.utils import timezone
from django.utils.html import strip_tags

from .models import EmailNotificationLog, Expense, Task, Users

logger = logging.getLogger(__name__)

EMAIL_EXECUTOR = ThreadPoolExecutor(max_workers=2, thread_name_prefix='taskly-email')


def _open_smtp_connection():
    smtp_class = smtplib.SMTP_SSL if settings.EMAIL_USE_SSL else smtplib.SMTP
    server = smtp_class(settings.EMAIL_HOST, settings.EMAIL_PORT)
    if settings.EMAIL_USE_TLS and not settings.EMAIL_USE_SSL:
        server.starttls()
    if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    return server


def _format_date(value):
    if not value:
        return 'Not set'
    if isinstance(value, str):
        parsed_value = parse_date(value)
        if parsed_value:
            value = parsed_value
        else:
            return value
    return value.strftime('%b %d, %Y')


def _get_site_url():
    allowed_hosts = [host.strip() for host in getattr(settings, 'ALLOWED_HOSTS', []) if host and host.strip() and host.strip() != '*']
    primary_host = allowed_hosts[0] if allowed_hosts else '127.0.0.1'
    if primary_host.startswith('http://') or primary_host.startswith('https://'):
        return primary_host.rstrip('/')
    return f'http://{primary_host}'.rstrip('/')


def _build_absolute_url(path=''):
    path = (path or '').lstrip('/')
    return f'{_get_site_url()}/{path}' if path else _get_site_url()


def _render_email(template_name, context):
    html_body = render_to_string(template_name, context)
    text_body = strip_tags(html_body)
    return html_body, text_body


def _mark_log(log_id, *, status, error_message=None):
    update_fields = ['status', 'updated_at']
    values = {
        'status': status,
        'updated_at': timezone.now(),
    }
    if status == EmailNotificationLog.STATUS_SENT:
        values['sent_at'] = timezone.now()
        values['error_message'] = None
        update_fields.extend(['sent_at', 'error_message'])
    else:
        values['error_message'] = error_message
        update_fields.append('error_message')
    EmailNotificationLog.objects.filter(id=log_id).update(**values)


def _deliver_email(log_id, subject, recipient_email, template_name, context):
    close_old_connections()
    sender = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER
    if not sender:
        logger.warning('No sender configured for email notification log_id=%s', log_id)
        _mark_log(log_id, status=EmailNotificationLog.STATUS_FAILED, error_message='Email sender is not configured.')
        close_old_connections()
        return

    try:
        html_body, text_body = _render_email(template_name, context)
        message = EmailMessage()
        message['Subject'] = subject
        message['From'] = sender
        message['To'] = recipient_email
        message.set_content(text_body or 'Your email client does not support HTML.')
        message.add_alternative(html_body, subtype='html')

        with _open_smtp_connection() as server:
            server.send_message(message)
        _mark_log(log_id, status=EmailNotificationLog.STATUS_SENT)
    except Exception as exc:
        logger.exception('Email delivery failed for log_id=%s', log_id)
        _mark_log(log_id, status=EmailNotificationLog.STATUS_FAILED, error_message=str(exc))
    finally:
        close_old_connections()


def _queue_delivery(log_id, subject, recipient_email, template_name, context, async_delivery=True):
    if async_delivery:
        EMAIL_EXECUTOR.submit(_deliver_email, log_id, subject, recipient_email, template_name, context)
        return True
    _deliver_email(log_id, subject, recipient_email, template_name, context)
    return True


@transaction.atomic
def _create_notification_log(
    *,
    user,
    notification_type,
    subject,
    idempotency_key,
    task=None,
    expense=None,
    reminder_stage=None,
):
    log, created = EmailNotificationLog.objects.get_or_create(
        idempotency_key=idempotency_key,
        defaults={
            'user': user,
            'task': task,
            'expense': expense,
            'notification_type': notification_type,
            'reminder_stage': reminder_stage,
            'recipient_email': user.email,
            'subject': subject,
            'status': EmailNotificationLog.STATUS_PENDING,
        },
    )
    return log, created


def _queue_notification(
    *,
    user,
    notification_type,
    subject,
    template_name,
    context,
    idempotency_key,
    task=None,
    expense=None,
    reminder_stage=None,
    async_delivery=True,
):
    if not user or not user.email:
        return False

    log, created = _create_notification_log(
        user=user,
        notification_type=notification_type,
        subject=subject,
        idempotency_key=idempotency_key,
        task=task,
        expense=expense,
        reminder_stage=reminder_stage,
    )

    if not created:
        return False

    if not user.email_notifications_enabled:
        _mark_log(log.id, status=EmailNotificationLog.STATUS_SKIPPED, error_message='User disabled email notifications.')
        return False

    payload = {
        **context,
        'app_name': 'Taskly',
        'recipient_name': user.display_name,
        'support_email': settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER or '',
        'site_url': _get_site_url(),
    }

    transaction.on_commit(
        lambda: _queue_delivery(log.id, subject, user.email, template_name, payload, async_delivery=async_delivery)
    )
    return True


def _build_detail_rows(details: Iterable[tuple[str, str]]):
    return [{'label': label, 'value': value} for label, value in details]


def send_task_assignment_notification(task: Task, *, async_delivery=True):
    if not task.assigned_to:
        return False

    subject = f'Task Assigned: {task.title}'
    assigned_date = timezone.localtime(task.updated_at).date() if task.updated_at else timezone.localdate()
    return _queue_notification(
        user=task.assigned_to,
        notification_type=EmailNotificationLog.TYPE_TASK_ASSIGNMENT,
        subject=subject,
        template_name='emails/task_assignment_email.html',
        context={
            'email_title': 'A task has been assigned to you',
            'email_intro': f'You have a new responsibility in {task.project.name}.',
            'email_badge': 'Task Assignment',
            'cta_label': 'Open Dashboard',
            'cta_url': _build_absolute_url('dashboard/'),
            'detail_rows': _build_detail_rows([
                ('Task title', task.title),
                ('Project', task.project.name),
                ('Assigned date', _format_date(assigned_date)),
                ('Due date', _format_date(task.due_date)),
            ]),
            'task': task,
            'project': task.project,
        },
        idempotency_key=f'task-assignment:{task.id}:{task.assigned_to_id}:{task.updated_at.isoformat()}',
        task=task,
        async_delivery=async_delivery,
    )


def _infer_payment_type(expense: Expense):
    text = ' '.join(filter(None, [expense.title, expense.description, expense.category_name])).lower()
    if 'bonus' in text:
        return 'Bonus'
    if 'service' in text:
        return 'Service'
    if expense.is_salary_payment or 'salary' in text:
        return 'Salary'
    return expense.category_name.title() if expense.category_name else 'Payment'


def send_payment_notification(expense: Expense, *, async_delivery=True):
    if not expense.assigned_user:
        return False

    payment_type = _infer_payment_type(expense)
    subject = f'Payment Received: {expense.display_title}'
    transaction_date = expense.paid_date or expense.issue_date or timezone.localdate()
    return _queue_notification(
        user=expense.assigned_user,
        notification_type=EmailNotificationLog.TYPE_PAYMENT,
        subject=subject,
        template_name='emails/payment_notification_email.html',
        context={
            'email_title': 'A payment has been recorded for you',
            'email_intro': f'{payment_type} details are ready in Taskly.',
            'email_badge': 'Payment Update',
            'cta_label': 'Review Project Finance',
            'cta_url': _build_absolute_url(f'dashboard/projects/{expense.project_id}/budget/'),
            'detail_rows': _build_detail_rows([
                ('Amount received', f'{expense.amount}'),
                ('Payment type', payment_type),
                ('Project', expense.project.name),
                ('Transaction date', _format_date(transaction_date)),
            ]),
            'expense': expense,
            'project': expense.project,
        },
        idempotency_key=f'payment:{expense.id}:{expense.assigned_user_id}:{expense.status}:{expense.amount}:{transaction_date.isoformat()}',
        expense=expense,
        async_delivery=async_delivery,
    )


def send_task_due_reminder(task: Task, reminder_stage: int, *, async_delivery=True):
    if not task.assigned_to or not task.due_date:
        return False

    day_label = 'day' if reminder_stage == 1 else 'days'
    subject = f'Task Due in {reminder_stage} {day_label}: {task.title}'
    return _queue_notification(
        user=task.assigned_to,
        notification_type=EmailNotificationLog.TYPE_TASK_DUE_REMINDER,
        subject=subject,
        template_name='emails/task_due_reminder_email.html',
        context={
            'email_title': 'Upcoming task deadline',
            'email_intro': f'Your task is due in {reminder_stage} {day_label}.',
            'email_badge': f'{reminder_stage}-{day_label} reminder',
            'cta_label': 'View My Tasks',
            'cta_url': _build_absolute_url('dashboard/tasks'),
            'detail_rows': _build_detail_rows([
                ('Task title', task.title),
                ('Project', task.project.name),
                ('Due date', _format_date(task.due_date)),
                ('Reminder stage', f'{reminder_stage} {day_label} before due date'),
            ]),
            'task': task,
            'project': task.project,
            'days_remaining': reminder_stage,
        },
        idempotency_key=f'task-reminder:{task.id}:{task.assigned_to_id}:{reminder_stage}',
        task=task,
        reminder_stage=reminder_stage,
        async_delivery=async_delivery,
    )


def send_welcome_email(user: Users, *, async_delivery=True):
    subject = f'Welcome to Taskly, {user.display_name}'
    return _queue_notification(
        user=user,
        notification_type=EmailNotificationLog.TYPE_WELCOME,
        subject=subject,
        template_name='emails/welcome_email.html',
        context={
            'email_title': f'Welcome to Taskly, {user.display_name}',
            'email_intro': 'Your email is verified and your workspace is ready.',
            'email_badge': 'Welcome',
            'cta_label': 'Open Dashboard',
            'cta_url': _build_absolute_url('dashboard/'),
            'detail_rows': _build_detail_rows([
                ('Name', user.display_name),
                ('Workspace', 'Taskly'),
                ('Next step', 'Sign in and open your dashboard'),
            ]),
        },
        idempotency_key=f'welcome:{user.id}',
        async_delivery=async_delivery,
    )


def send_generic_notification(user: Users, subject: str, message: str, *, async_delivery=True):
    return _queue_notification(
        user=user,
        notification_type=EmailNotificationLog.TYPE_GENERIC,
        subject=subject,
        template_name='emails/generic_notification_email.html',
        context={
            'email_title': subject,
            'email_intro': message,
            'email_badge': 'Notification',
            'cta_label': 'Open Taskly',
            'cta_url': _build_absolute_url('dashboard/'),
            'detail_rows': [],
        },
        idempotency_key=f'generic:{uuid4()}',
        async_delivery=async_delivery,
    )
