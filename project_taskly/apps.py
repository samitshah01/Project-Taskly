from django.apps import AppConfig


class ProjectTasklyConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'project_taskly'

    def ready(self):
        from . import signals
        from .scheduler import start_due_reminder_scheduler

        start_due_reminder_scheduler()
