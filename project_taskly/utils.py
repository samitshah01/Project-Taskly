import random
import logging
import smtplib
from email.message import EmailMessage
from datetime import timedelta
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from .models import PasswordOTP
from django.conf import settings

logger = logging.getLogger(__name__)
REMINDER_STAGES = (7, 3, 2, 1)


def _open_smtp_connection():
    smtp_class = smtplib.SMTP_SSL if settings.EMAIL_USE_SSL else smtplib.SMTP
    server = smtp_class(settings.EMAIL_HOST, settings.EMAIL_PORT)
    if settings.EMAIL_USE_TLS and not settings.EMAIL_USE_SSL:
        server.starttls()
    if settings.EMAIL_HOST_USER and settings.EMAIL_HOST_PASSWORD:
        server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
    return server

def generate_otp(length=6):
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])

OTP_EMAIL_CONTENT = {
    'login': {
        'subject': 'Verify your Taskly account',
        'headline': 'Taskly Login Verification',
        'message': 'Use the following one-time password (OTP) to verify your account and complete sign in.',
    },
    'password_reset': {
        'subject': 'Reset your Taskly password',
        'headline': 'Taskly Password Reset',
        'message': 'Use the following one-time password (OTP) to reset your password.',
    },
}


def send_otp_email(email, otp, purpose='password_reset'):
    email_content = OTP_EMAIL_CONTENT.get(purpose, OTP_EMAIL_CONTENT['password_reset'])
    html_content = render_to_string('emails/otp_email.html', {
        'otp': otp,
        'email_headline': email_content['headline'],
        'email_message': email_content['message'],
    })
    sender = settings.DEFAULT_FROM_EMAIL or settings.EMAIL_HOST_USER

    try:
        message = EmailMessage()
        message['Subject'] = email_content['subject']
        message['From'] = sender
        message['To'] = email
        message.set_content('Your email client does not support HTML.')
        message.add_alternative(html_content, subtype='html')

        with _open_smtp_connection() as server:
            server.send_message(message)
    except Exception as e:
        logger.exception("OTP email send failed for %s", email)
        raise

def create_and_send_otp(email, purpose='password_reset'):
    now = timezone.now()

    last_otp = PasswordOTP.objects.filter(email=email).order_by('-created_at').first()
    if last_otp and (now - last_otp.created_at).total_seconds() < 60:
        return False, "Please wait before requesting a new OTP."

    otp = generate_otp()
    otp_hash = make_password(otp)
    expires_at = now + timedelta(minutes=10)

    try:
        send_otp_email(email, otp, purpose=purpose)

        PasswordOTP.objects.filter(email=email).delete()

        PasswordOTP.objects.create(
            email=email,
            otp_hash=otp_hash,
            expires_at=expires_at
        )

        return True, "OTP sent successfully"

    except Exception as e:
        return False, "Failed to send OTP. Please try again."

def verify_otp(email, otp):
    otp_entry = PasswordOTP.objects.filter(email=email).order_by('-created_at').first()

    if not otp_entry:
        return False, "No OTP found"

    if otp_entry.is_expired():
        otp_entry.delete()
        return False, "OTP expired"

    if check_password(otp, otp_entry.otp_hash):
        otp_entry.delete()
        return True, "OTP verified"

    return False, "Invalid OTP"

def mask_email(email):
    try:
        name, domain = email.split('@')
        if len(name) <= 2:
            return name[0] + "***@" + domain
        return name[:2] + "***@" + domain
    except:
        return email


def process_due_task_reminders(*, async_delivery=True):
    from .models import Task
    from .notifications import send_task_due_reminder

    today = timezone.localdate()
    sent_count = 0

    for days_before in REMINDER_STAGES:
        due_date = today + timedelta(days=days_before)
        tasks = Task.objects.select_related('project', 'assigned_to').filter(
            due_date=due_date,
            assigned_to__isnull=False,
        ).exclude(status=Task.STATUS_COMPLETED)

        for task in tasks:
            try:
                if send_task_due_reminder(task, days_before, async_delivery=async_delivery):
                    sent_count += 1
            except Exception:
                logger.exception(
                    'Task due reminder processing failed for task_id=%s stage=%s',
                    task.id,
                    days_before,
                )

    return sent_count
