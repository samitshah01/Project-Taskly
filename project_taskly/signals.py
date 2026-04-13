from django.db.models.signals import post_save, pre_save
from django.dispatch import receiver

from .models import Expense, Task, Users
from .notifications import (
    send_payment_notification,
    send_task_assignment_notification,
    send_welcome_email,
)


@receiver(pre_save, sender=Task)
def capture_previous_task_assignment(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_assigned_to_id = None
        return
    previous = sender.objects.filter(pk=instance.pk).values('assigned_to_id').first()
    instance._previous_assigned_to_id = previous['assigned_to_id'] if previous else None


@receiver(post_save, sender=Task)
def send_task_assignment_email(sender, instance, created, **kwargs):
    previous_assigned_to_id = getattr(instance, '_previous_assigned_to_id', None)
    assignment_changed = created or previous_assigned_to_id != instance.assigned_to_id
    if assignment_changed and instance.assigned_to_id:
        send_task_assignment_notification(instance)


@receiver(pre_save, sender=Expense)
def capture_previous_payment_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_status = None
        instance._previous_assigned_user_id = None
        return
    previous = sender.objects.filter(pk=instance.pk).values('status', 'assigned_user_id').first() or {}
    instance._previous_status = previous.get('status')
    instance._previous_assigned_user_id = previous.get('assigned_user_id')


@receiver(post_save, sender=Expense)
def send_payment_email(sender, instance, created, **kwargs):
    transitioned_to_paid = instance.status == Expense.STATUS_PAID and (
        created
        or getattr(instance, '_previous_status', None) != Expense.STATUS_PAID
        or getattr(instance, '_previous_assigned_user_id', None) != instance.assigned_user_id
    )
    if transitioned_to_paid and instance.assigned_user_id:
        send_payment_notification(instance)


@receiver(pre_save, sender=Users)
def capture_previous_verification_state(sender, instance, **kwargs):
    if not instance.pk:
        instance._previous_is_email_verified = False
        return
    previous = sender.objects.filter(pk=instance.pk).values('is_email_verified').first()
    instance._previous_is_email_verified = previous['is_email_verified'] if previous else False


@receiver(post_save, sender=Users)
def send_welcome_after_verification(sender, instance, created, **kwargs):
    if created:
        return
    if not getattr(instance, '_previous_is_email_verified', False) and instance.is_email_verified:
        send_welcome_email(instance)
