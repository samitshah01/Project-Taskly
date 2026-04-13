import os
from typing import TYPE_CHECKING
from django.conf import settings
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from django.utils import timezone

class Users(models.Model):
    if TYPE_CHECKING:
        tasks: "models.Manager[Task]"
        project_memberships: "models.Manager[ProjectMember]"
        managed_projects: "models.Manager[Project]"
        activity_logs: "models.Manager[ActivityLog]"

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

    @property
    def avatar_relative_path(self):
        if not self.id:
            return ""
        for ext in ("jpg", "jpeg", "png", "webp", "gif"):
            relative = f"profile_avatars/user_{self.id}.{ext}"
            absolute = os.path.join(settings.MEDIA_ROOT, relative.replace("/", os.sep))
            if os.path.exists(absolute):
                return relative
        return ""

    @property
    def avatar_url(self):
        relative = self.avatar_relative_path
        if not relative:
            return ""
        absolute = os.path.join(settings.MEDIA_ROOT, relative.replace("/", os.sep))
        version = int(os.path.getmtime(absolute)) if os.path.exists(absolute) else 0
        return f"{settings.MEDIA_URL}{relative}?v={version}"


class Project(models.Model):
    if TYPE_CHECKING:
        manager_id: int | None
        tasks: "models.Manager[Task]"
        project_members: "models.Manager[ProjectMember]"
        files: "models.Manager[ProjectFile]"
        expenses: "models.Manager[Expense]"
        activity_logs: "models.Manager[ActivityLog]"

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
    owner = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        related_name='owned_projects',
        blank=True,
        null=True,
    )
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
    if TYPE_CHECKING:
        user_id: int
        project_id: int

    id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='project_members')
    user = models.ForeignKey(Users, on_delete=models.CASCADE, related_name='project_memberships')
    role = models.CharField(max_length=100, blank=True, null=True)
    is_manager = models.BooleanField(default=False)
    assignment_status = models.CharField(max_length=20, default='active')
    allocation_hours_per_day = models.DecimalField(max_digits=4, decimal_places=1, default=0)
    assignment_start_date = models.DateField(blank=True, null=True)
    assignment_end_date = models.DateField(blank=True, null=True)
    assignment_notes = models.TextField(blank=True, null=True)
    joined_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'project_members'
        unique_together = ('project', 'user')
        ordering = ['project_id', 'joined_at']

    def __str__(self):
        return f'{self.user.display_name} - {self.project.name}'

    @property
    def display_role(self):
        if self.is_manager:
            return self.role or 'Project Manager'
        return self.role or 'Team Member'


class Task(models.Model):
    if TYPE_CHECKING:
        project_id: int
        assigned_to_id: int | None
        comments: "models.Manager[TaskComment]"
        activity_logs: "models.Manager[ActivityLog]"

        def get_status_display(self) -> str: ...

        def get_priority_display(self) -> str: ...

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


class ExpenseCategory(models.Model):
    id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expense_categories')
    name = models.CharField(max_length=120)
    is_fixed = models.BooleanField(default=False)
    created_by = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        related_name='created_expense_categories',
        blank=True,
        null=True,
    )
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'expense_categories'
        ordering = ['name']
        unique_together = ('project', 'name')


class Expense(models.Model):
    TYPE_EXPENSE = 'expense'
    TYPE_INCOME = 'income'

    STATUS_PAID = 'paid'
    STATUS_PENDING = 'pending'
    STATUS_CANCELLED = 'cancelled'
    STATUS_OVERDUE = 'overdue'

    TRANSACTION_TYPE_CHOICES = [
        (TYPE_EXPENSE, 'Expense'),
        (TYPE_INCOME, 'Income'),
    ]

    PAYMENT_STATUS_CHOICES = [
        (STATUS_PAID, 'Paid'),
        (STATUS_PENDING, 'Pending'),
        (STATUS_CANCELLED, 'Cancelled'),
        (STATUS_OVERDUE, 'Overdue'),
    ]

    id = models.AutoField(primary_key=True)
    project = models.ForeignKey(Project, on_delete=models.CASCADE, related_name='expenses')
    category = models.ForeignKey(
        ExpenseCategory,
        on_delete=models.SET_NULL,
        related_name='expenses',
        blank=True,
        null=True,
    )
    created_by = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        related_name='created_expenses',
        blank=True,
        null=True,
    )
    assigned_user = models.ForeignKey(
        Users,
        on_delete=models.SET_NULL,
        related_name='assigned_finance_transactions',
        blank=True,
        null=True,
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    title = models.CharField(max_length=255, blank=True, null=True)
    description = models.CharField(max_length=255)
    transaction_type = models.CharField(max_length=20, choices=TRANSACTION_TYPE_CHOICES, default=TYPE_EXPENSE)
    reference_id = models.CharField(max_length=120, blank=True, null=True)
    status = models.CharField(max_length=20, choices=PAYMENT_STATUS_CHOICES, default=STATUS_PENDING)
    issue_date = models.DateField(blank=True, null=True)
    paid_date = models.DateField(blank=True, null=True)
    note = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'expenses'
        ordering = ['-created_at']

    @property
    def display_title(self):
        return self.title or self.description

    @property
    def category_name(self):
        return self.category.name if self.category else 'General'

    @property
    def is_salary_payment(self):
        return bool(self.assigned_user_id) or self.category_name.lower() == 'salary'


class EmployeeProfile(models.Model):
    TYPE_FULL_TIME = 'full_time'
    TYPE_PART_TIME = 'part_time'
    TYPE_CONTRACT = 'contract'
    TYPE_INTERN = 'intern'

    STATUS_ACTIVE = 'active'
    STATUS_ON_LEAVE = 'on_leave'
    STATUS_INACTIVE = 'inactive'

    EMPLOYEE_TYPE_CHOICES = [
        (TYPE_FULL_TIME, 'Full Time'),
        (TYPE_PART_TIME, 'Part Time'),
        (TYPE_CONTRACT, 'Contract'),
        (TYPE_INTERN, 'Intern'),
    ]

    EMPLOYMENT_STATUS_CHOICES = [
        (STATUS_ACTIVE, 'Active'),
        (STATUS_ON_LEAVE, 'On Leave'),
        (STATUS_INACTIVE, 'Inactive'),
    ]

    user = models.OneToOneField(Users, on_delete=models.CASCADE, related_name='employee_profile')
    employee_type = models.CharField(max_length=20, choices=EMPLOYEE_TYPE_CHOICES, default=TYPE_FULL_TIME)
    salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    join_date = models.DateField(default=timezone.localdate)
    status = models.CharField(max_length=20, choices=EMPLOYMENT_STATUS_CHOICES, default=STATUS_ACTIVE)

    class Meta:
        db_table = 'employee_profiles'
        ordering = ['join_date', 'user_id']


class EmployeePayroll(models.Model):
    STATUS_PAID = 'paid'
    STATUS_PENDING = 'pending'
    STATUS_PROCESSING = 'processing'

    STATUS_CHOICES = [
        (STATUS_PAID, 'Paid'),
        (STATUS_PENDING, 'Pending'),
        (STATUS_PROCESSING, 'Processing'),
    ]

    employee = models.ForeignKey(EmployeeProfile, on_delete=models.CASCADE, related_name='payroll_entries')
    month = models.DateField()
    base_salary = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    bonus = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    deduction = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    payment_status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_PENDING)
    created_at = models.DateTimeField(default=timezone.now)

    class Meta:
        db_table = 'employee_payroll'
        ordering = ['-month', '-created_at']

    @property
    def net_pay(self):
        return (self.base_salary or 0) + (self.bonus or 0) - (self.deduction or 0)


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
