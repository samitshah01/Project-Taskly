from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings


class CustomUser(AbstractUser):
    profession = models.CharField(max_length=150, blank=True, null=True)
    company = models.CharField(max_length=200, blank=True, null=True)
    phone = models.CharField(max_length=30, blank=True, null=True)

    def __str__(self):
        return self.username


class Users(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    email = models.CharField(unique=True, max_length=150, blank=True, null=True)
    password = models.CharField(max_length=255, blank=True, null=True)
    role = models.CharField(max_length=50, blank=True, null=True)
    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'users'

    def __str__(self):
        return self.email

class Project(models.Model):

    STATUS_CHOICES = [
        ("planned", "Planned"),
        ("in_progress", "In Progress"),
        ("on_hold", "On Hold"),
        ("completed", "Completed"),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    start_date = models.DateField()
    end_date = models.DateField(null=True, blank=True)

    budget = models.DecimalField(max_digits=12, decimal_places=2)

    manager = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        related_name="managed_projects"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="planned"
    )

    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'projects'

    def __str__(self):
        return self.name

class TeamMember(models.Model):

    id = models.AutoField(primary_key=True)

    user = models.OneToOneField(
        Users,
        on_delete=models.CASCADE
    )

    role = models.CharField(max_length=100, blank=True)

    joined_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'team_members'

    def __str__(self):
        return str(self.user)

class Task(models.Model):

    STATUS_CHOICES = [
        ("todo", "To Do"),
        ("in_progress", "In Progress"),
        ("review", "Review"),
        ("done", "Done"),
    ]

    PRIORITY_CHOICES = [
        ("high", "High"),
        ("medium", "Medium"),
        ("low", "Low"),
    ]

    id = models.AutoField(primary_key=True)

    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="tasks"
    )

    assigned_to = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="assigned_tasks"
    )

    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default="todo"
    )

    priority = models.CharField(
        max_length=10,
        choices=PRIORITY_CHOICES,
        default="medium"
    )

    due_date = models.DateField(null=True, blank=True)

    created_at = models.DateTimeField(blank=True, null=True)
    updated_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'tasks'

    def __str__(self):
        return self.title

class TaskComment(models.Model):

    id = models.AutoField(primary_key=True)

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name="comments"
    )

    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE
    )

    comment = models.TextField()

    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'task_comments'

    def __str__(self):
        return f"{self.user.email} - {self.task.title}"

class ProjectFile(models.Model):

    id = models.AutoField(primary_key=True)

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="files"
    )

    uploaded_by = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        null=True
    )

    file = models.CharField(max_length=255)

    uploaded_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'project_files'

    def __str__(self):
        return self.file

class Expense(models.Model):

    id = models.AutoField(primary_key=True)

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name="expenses"
    )

    amount = models.DecimalField(max_digits=10, decimal_places=2)

    description = models.CharField(max_length=255)

    created_at = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'expenses'

    def __str__(self):
        return f"{self.project.name} - {self.amount}"

class ActivityLog(models.Model):

    id = models.AutoField(primary_key=True)

    user = models.ForeignKey(
        Users,
        on_delete=models.CASCADE
    )

    action = models.CharField(max_length=255)

    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        null=True,
        blank=True
    )

    timestamp = models.DateTimeField(blank=True, null=True)

    class Meta:
        managed = False
        db_table = 'activity_logs'

    def __str__(self):
        return f"{self.user.email} - {self.action}"