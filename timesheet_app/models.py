from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

# Base User
class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)

# Custom User
class CustomUser(AbstractUser):
    USERTYPE_CHOICES = [
        ('SuperAdmin', 'SuperAdmin'),  # CEO
        ('Admin', 'Admin'),            # Main People, Account Managers
        ('TeamLeader', 'TeamLeader'),  # Team Leaders (Search, Creative, Development)
        ('User', 'User')               # Regular team members
    ]

    TEAM_CHOICES = [
        ('Search', 'Search Team'),         # SEO, SMO, SEM
        ('Creative', 'Creative Team'),     # Creative Team (Designers + Content Writers)
        ('Development', 'Development Team')  # Developers
    ]

    SUBTEAM_CHOICES = [
        # Search Team Sub-teams
        ('SEO', 'SEO'),
        ('SMO', 'SMO'),
        ('SEM', 'SEM'),
        
        # Creative Team Sub-teams
        ('Design', 'Design Team'),
        ('Content Writing', 'Content Writing'),
        
        # Development Team Sub-teams
        ('Python Development', 'Python Development'),
        ('Web Development', 'Web Development'),
    ]

    usertype = models.CharField(max_length=50, choices=USERTYPE_CHOICES)
    firstname = models.CharField(max_length=50, default='iVista')
    lastname = models.CharField(max_length=50, default='Solutions')
    email = models.EmailField(unique=True)
    team = models.CharField(max_length=50, choices=TEAM_CHOICES, null=True, blank=True)
    subteam = models.CharField(max_length=50, choices=SUBTEAM_CHOICES, null=True, blank=True)
    chat_id = models.CharField(max_length=50, default='1234567890')  # Add chat_id field
    objects = CustomUserManager()

    def __str__(self):
        return self.username

# Admin User
class Admin(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    additional_field = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.user.usertype != 'Admin':
            raise ValueError('Cannot assign Admin role to non-Admin user.')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username
  
# Team Leader User  
class TeamLeader(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    additional_field = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.user.usertype != 'TeamLeader':
            raise ValueError('Cannot assign TeamLeader role to non-TeamLeader user.')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

# User
class User(models.Model):
    user = models.OneToOneField(CustomUser, on_delete=models.CASCADE)
    additional_field = models.CharField(max_length=255, blank=True, null=True)

    def save(self, *args, **kwargs):
        if self.user.usertype != 'User':
            raise ValueError('Cannot assign User role to non-User.')
        super().save(*args, **kwargs)

    def __str__(self):
        return self.user.username

# Team Model
class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    account_manager = models.ForeignKey(CustomUser, related_name='managed_teams', on_delete=models.CASCADE)
    team_leader_search = models.ForeignKey(CustomUser, related_name='led_search_teams', on_delete=models.CASCADE, null=True, blank=True)
    team_leader_development = models.ForeignKey(CustomUser, related_name='led_development_teams', on_delete=models.CASCADE, null=True, blank=True)
    team_leader_creative = models.ForeignKey(CustomUser, related_name='led_creative_teams', on_delete=models.CASCADE, null=True, blank=True)
    team = models.CharField(max_length=50, choices=CustomUser.TEAM_CHOICES)
    subteam = models.CharField(max_length=50, choices=CustomUser.SUBTEAM_CHOICES, null=True, blank=True)
    members = models.ManyToManyField(CustomUser, related_name='teams')
    created_by = models.ForeignKey(CustomUser, related_name='created_teams', on_delete=models.CASCADE, default=1)

    def __str__(self):
        return self.name

    def delete(self, *args, **kwargs):
        # Remove the team reference from associated projects before deleting the team
        Project.objects.filter(team=self).update(team=None)
        super().delete(*args, **kwargs)

# Project Model
class Project(models.Model):
    STATUS_CHOICES = [
        ('Ongoing', 'Ongoing'),
        ('Completed', 'Completed'),
        ('Upcoming', 'Upcoming'),
    ]

    name = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES)
    start_date = models.DateField()
    deadline = models.DateField()
    progress = models.IntegerField(default=0)  # Progress field
    team = models.ForeignKey(Team, related_name='projects', on_delete=models.CASCADE, null=True, blank=True)  # Add this line
    created_by = models.ForeignKey(CustomUser, related_name='created_projects', on_delete=models.CASCADE, default=1)  # Add this line with default value

    def __str__(self):
        return self.name

# Notification Model
class Notification(models.Model):
    user = models.ForeignKey(CustomUser, on_delete=models.CASCADE)
    message = models.TextField()
    is_read = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Notification for {self.user.username} - {self.message[:20]}"

# Task Model
class Task(models.Model):
    STATUS_CHOICES = [
        ('To Do', 'To Do'),
        ('In Progress', 'In Progress'),
        ('Review', 'Review'),
        ('Completed', 'Completed'),
    ]

    project = models.ForeignKey(Project, related_name='tasks', on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    description = models.TextField()
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='To Do')
    priority = models.CharField(max_length=50, default='Medium')
    start_date = models.DateField()
    end_date = models.DateField()
    created_by = models.ForeignKey(CustomUser, related_name='created_tasks', on_delete=models.CASCADE)
    
    # Separate assignment fields
    superadmin_assigned_to = models.ForeignKey(CustomUser, related_name='superadmin_tasks', on_delete=models.SET_NULL, null=True, blank=True)
    admin_assigned_to = models.ForeignKey(CustomUser, related_name='admin_tasks', on_delete=models.SET_NULL, null=True, blank=True)
    teamleader_assigned_to = models.ForeignKey(CustomUser, related_name='teamleader_tasks', on_delete=models.SET_NULL, null=True, blank=True)
    
    def __str__(self):
        return self.title

    def assign_task(self, assigned_by, assigned_to):
        if assigned_by.usertype == 'SuperAdmin':
            self.superadmin_assigned_to = assigned_to
        elif assigned_by.usertype == 'Admin':
            self.admin_assigned_to = assigned_to
        elif assigned_by.usertype == 'TeamLeader':
            self.teamleader_assigned_to = assigned_to
            
        self.save()

# Timesheet Model
class Timesheet(models.Model):
    STATUS_CHOICES = [
        ('To Do', 'To Do'),
        ('On Progress', 'On Progress'),
        ('On Hold', 'On Hold'),
        ('Completed', 'Completed'),
    ]

    date = models.DateField()
    task = models.CharField(max_length=255)
    submitted_to = models.ForeignKey(CustomUser, related_name='submitted_timesheets', on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='To Do')
    description = models.TextField()
    hours = models.DecimalField(max_digits=5, decimal_places=1)
    created_by = models.ForeignKey(CustomUser, related_name='created_timesheets', on_delete=models.CASCADE)
    project = models.ForeignKey(Project, related_name='timesheets', on_delete=models.CASCADE, null=True, blank=True)

    def __str__(self):
        return f"Timesheet for {self.created_by.username} on {self.date}"

class TimesheetTable(models.Model):
    STATUS_CHOICES = [
        ('Pending Review', 'Pending Review'),
        ('Sent for Review', 'Sent for Review'),
        ('Approved by Team Leader', 'Approved by Team Leader'),
        ('Rejected by Team Leader', 'Rejected by Team Leader'),
        ('Approved by Admin', 'Approved by Admin'),  
        ('Rejected by Admin', 'Rejected by Admin'), 
    ]

    created_by = models.ForeignKey(CustomUser, related_name='created_timesheet_tables', on_delete=models.CASCADE)
    timesheets = models.ManyToManyField(Timesheet, related_name='timesheet_tables')
    created_at = models.DateTimeField(auto_now_add=True)
    status = models.CharField(max_length=50, choices=STATUS_CHOICES, default='Pending Review')
    comments = models.TextField(blank=True, null=True)

    def __str__(self):
        return f"Timesheet Table created by {self.created_by.username} on {self.created_at}"

    def delete(self, *args, **kwargs):
        orphan_timesheets = self.timesheets.all()
        super().delete(*args, **kwargs)  
        for timesheet in orphan_timesheets:
            if not timesheet.timesheet_tables.exists():
                timesheet.delete()

# Signals to automatically create role-specific models
@receiver(post_save, sender=CustomUser)
def create_role_specific_model(sender, instance, created, **kwargs):
    if created:
        if instance.usertype == 'Admin':
            Admin.objects.create(user=instance)
        elif instance.usertype == 'TeamLeader':
            TeamLeader.objects.create(user=instance)
        elif instance.usertype == 'User':
            User.objects.create(user=instance)

@receiver(post_save, sender=CustomUser)
def save_role_specific_model(sender, instance, **kwargs):
    if instance.usertype == 'Admin':
        instance.admin.save()
    elif instance.usertype == 'TeamLeader':
        instance.teamleader.save()
    elif instance.usertype == 'User':
        instance.user.save()




