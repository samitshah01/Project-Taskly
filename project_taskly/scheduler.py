import logging
import os
import sys
import threading
import time

from django.conf import settings
from django.db import close_old_connections

from .utils import process_due_task_reminders

logger = logging.getLogger(__name__)

_scheduler_started = False
_scheduler_lock = threading.Lock()


def _should_start_scheduler():
    blocked_commands = {
        'check',
        'makemigrations',
        'migrate',
        'collectstatic',
        'shell',
        'dbshell',
        'test',
    }
    if any(command in sys.argv for command in blocked_commands):
        return False

    if 'runserver' in sys.argv and os.environ.get('RUN_MAIN') != 'true':
        return False

    return True


def _scheduler_loop():
    interval_seconds = 3600
    logger.info('Taskly due reminder scheduler started with %s second interval.', interval_seconds)

    while True:
        close_old_connections()
        try:
            sent_count = process_due_task_reminders(async_delivery=True)
            if sent_count:
                logger.info('Taskly due reminder scheduler queued %s reminder email(s).', sent_count)
        except Exception:
            logger.exception('Taskly due reminder scheduler run failed.')
        finally:
            close_old_connections()
        time.sleep(interval_seconds)


def start_due_reminder_scheduler():
    global _scheduler_started

    if not _should_start_scheduler():
        return

    with _scheduler_lock:
        if _scheduler_started:
            return
        thread = threading.Thread(
            target=_scheduler_loop,
            name='taskly-due-reminder-scheduler',
            daemon=True,
        )
        thread.start()
        _scheduler_started = True
