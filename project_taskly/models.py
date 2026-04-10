from django.db import models
from django.contrib.auth.models import AbstractUser
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

class CustomUser(AbstractUser):
    pass


class Users(models.Model):
    id = models.AutoField(primary_key=True)
    first_name = models.CharField(max_length=100, blank=True, null=True)
    last_name = models.CharField(max_length=100, blank=True, null=True)
    username = models.CharField(max_length=50, blank=True, null=True)
    email = models.CharField(unique=True, max_length=150)
    password = models.CharField(max_length=255)
    role = models.CharField(max_length=50, default='user')
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'users'

    def __str__(self):
        return self.email

    def set_password(self, raw_password):
        self.password = make_password(raw_password)

    def check_password(self, raw_password):
        return check_password(raw_password, self.password)

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()

    @property
    def display_name(self):
        return self.full_name or self.username or self.email

    @property
    def initials(self):
        if self.first_name or self.last_name:
            return f"{(self.first_name or ' ')[:1]}{(self.last_name or ' ')[:1]}".strip().upper()
        if self.username:
            return self.username[:2].upper()
        return self.email[:2].upper()


class Project(models.Model):
    STATUS_PLANNED = 'planned'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'
    STATUS_ON_HOLD = 'on_hold'

    STATUS_CHOICES = [
        (STATUS_PLANNED, 'Planned'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
        (STATUS_ON_HOLD, 'On Hold'),
    ]

    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    budget = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    manager = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        related_name='managed_projects',
        blank=True,
        null=True,
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PLANNED)
    color = models.CharField(max_length=20, default='#4f7cff')
    icon = models.CharField(max_length=50, default='folder2')
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'projects'
        ordering = ['name']

    def __str__(self):
        return self.name

    @property
    def status_label(self):
        return dict(self.STATUS_CHOICES).get(self.status, self.status.replace('_', ' ').title())


class ProjectMember(models.Model):
    id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_members')
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=100, blank=True, null=True)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'project_members'
        unique_together = ('project', 'user')
        ordering = ['project_id', 'joined_at']

    def __str__(self):
        return f'{self.user.display_name} - {self.project.name}'


class Task(models.Model):
    STATUS_TODO = 'todo'
    STATUS_IN_PROGRESS = 'in_progress'
    STATUS_COMPLETED = 'completed'

    PRIORITY_LOW = 'low'
    PRIORITY_MEDIUM = 'medium'
    PRIORITY_HIGH = 'high'

    STATUS_CHOICES = [
        (STATUS_TODO, 'To Do'),
        (STATUS_IN_PROGRESS, 'In Progress'),
        (STATUS_COMPLETED, 'Completed'),
    ]

    PRIORITY_CHOICES = [
        (PRIORITY_LOW, 'Low'),
        (PRIORITY_MEDIUM, 'Medium'),
        (PRIORITY_HIGH, 'High'),
    ]

    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='tasks')
    assigned_to = models.ForeignKey(Users,on_delete=models.SET_NULL,related_name='tasks',blank=True,null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_TODO)
    priority = models.CharField(max_length=10, choices=PRIORITY_CHOICES, default=PRIORITY_MEDIUM)
    due_date = models.DateField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'tasks'
        ordering = ['status', 'due_date', '-created_at']

    def __str__(self):
        return self.title


class ProjectFile(models.Model):
    id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='files')
    uploaded_by = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        related_name='uploaded_project_files',
        blank=True,
        null=True,
    )
    file = models.CharField(max_length=255)
    uploaded_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'project_files'
        ordering = ['-uploaded_at']


class Expense(models.Model):
    id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expenses')
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.CharField(max_length=255)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'expenses'
        ordering = ['-created_at']


class TaskComment(models.Model):
    id = models.AutoField(primary_key=True)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name='comments')
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='task_comments')
    comment = models.TextField()
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'task_comments'
        ordering = ['-created_at']


class ActivityLog(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='activity_logs')
    action = models.CharField(max_length=255)
    project = models.ForeignKey(
        Project,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        blank=True,
        null=True,
    )
    task = models.ForeignKey(
        Task,
        on_delete=models.CASCADE,
        related_name='activity_logs',
        blank=True,
        null=True,
    )
    timestamp = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'activity_logs'
        ordering = ['-timestamp']


class PasswordOTP(models.Model):
    email = models.EmailField(db_index=True)
    otp_hash = models.CharField(max_length=128)
    created_at = models.DateTimeField(auto_now_add=True)
    expires_at = models.DateTimeField()

    def is_expired(self):
        return timezone.now() > self.expires_at

    def __str__(self):
        return f"{self.email} - OTP"

    class Meta:
        db_table = 'password_otps'
        ordering = ['-created_at']
