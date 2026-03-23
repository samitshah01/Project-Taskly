import random
import smtplib
from email.message import EmailMessage
from django.template.loader import render_to_string
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from datetime import timedelta
from .models import PasswordOTP
from django.conf import settings

def generate_otp(length=6):
    return ''.join([str(random.randint(0, 9)) for _ in range(length)])

def send_otp_email(email, otp):
    html_content = render_to_string('emails/otp_email.html', {'otp': otp})

    msg = EmailMessage()
    msg['Subject'] = 'Your OTP Code'
    msg['From'] = settings.DEFAULT_FROM_EMAIL
    msg['To'] = email
    msg.set_content("Your email client does not support HTML")
    msg.add_alternative(html_content, subtype='html')

    try:
        with smtplib.SMTP(settings.EMAIL_HOST, settings.EMAIL_PORT) as server:
            if settings.EMAIL_USE_TLS:
                server.starttls()
            server.login(settings.EMAIL_HOST_USER, settings.EMAIL_HOST_PASSWORD)
            server.send_message(msg)
        print(f"OTP sent to {email}")
    except Exception as e:
        print("Error sending OTP:", e)

def create_and_send_otp(email):
    now = timezone.now()

    last_otp = PasswordOTP.objects.filter(email=email).order_by('-created_at').first()
    if last_otp and (now - last_otp.created_at).total_seconds() < 60:
        return False, "Please wait before requesting a new OTP."

    otp = generate_otp()
    otp_hash = make_password(otp)
    expires_at = now + timedelta(minutes=10)

    try:
        send_otp_email(email, otp)

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