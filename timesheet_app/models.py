from django.db import models
from django.contrib.auth.models import AbstractUser, BaseUserManager
from django.db.models.signals import post_save, pre_delete
from django.dispatch import receiver

# from datetime import datetime
# from db_connection import db

# custom_user_collection = db['CustomUser']
# admin_collection = db['Admin']
# team_leader_collection = db['TeamLeader']
# user_collection = db['User']
# project_collection = db['Project']
# team_collection = db['Team']
# task_collection = db['Task']
# timesheet_collection = db['Timesheet']
# timesheet_table_collection = db['TimesheetTable']

# Base User
class CustomUserManager(BaseUserManager):
    def create_user(self, username, password=None, **extra_fields):
        if not username:
            raise ValueError('The Username field must be set')
        user = self.model(username=username, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
       
        # insert into Mongodb
        # user_data = {
        #     "username": user.username,
        #     "usertype": user.usertype,
        #     "firstname": user.firstname,
        #     "lastname": user.lastname,
        #     "email": user.email,
        #     "team": user.team,
        #     "subteam": user.subteam,
        #     "chat_id": user.chat_id,
        #     "password": user.password,  
        #     "is_superuser": user.is_superuser,
        #     "is_staff": user.is_staff
            
        # }
        # custom_user_collection.insert_one(user_data)

        return user
    

    def create_superuser(self, username, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        extra_fields.setdefault('usertype', 'SuperAdmin')

        if extra_fields.get('is_staff') is not True:
            raise ValueError('Superuser must have is_staff=True.')
        if extra_fields.get('is_superuser') is not True:
            raise ValueError('Superuser must have is_superuser=True.')

        return self.create_user(username, password, **extra_fields)

# Custom User
class CustomUser(AbstractUser):
    USERTYPE_CHOICES = [
        ('SuperAdmin', 'SuperAdmin'), 
        ('Admin', 'Admin'),           
        ('TeamLeader', 'TeamLeader'), 
        ('User', 'User')               
    ]

    TEAM_CHOICES = [
        ('Search', 'Search Team'),        
        ('Creative', 'Creative Team'),    
        ('Development', 'Development Team')  
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
    firstname = models.CharField(max_length=50, default='Narayan')
    lastname = models.CharField(max_length=50, default='Rajan')
    email = models.EmailField(unique=True)
    team = models.CharField(max_length=50, choices=TEAM_CHOICES, null=True, blank=True)
    subteam = models.CharField(max_length=50, choices=SUBTEAM_CHOICES, null=True, blank=True)
    chat_id = models.CharField(max_length=50, default='1234567890') 
    
    objects = CustomUserManager()

    class Meta:
        verbose_name = "Custom User"
        verbose_name_plural = "Custom Users"
        
    # def save(self, *args, **kwargs):
    #     """Ensure user is also stored in MongoDB when created via Django Admin."""
    #     super().save(*args, **kwargs)  # Save in Django DB
        
    #     #  Insert into MongoDB if not already present
    #     # if not custom_user_collection.find_one({"username": self.username}):
        #     user_data = {
        #         "username": self.username,
        #         "usertype": self.usertype,
        #         "firstname": self.firstname,
        #         "lastname": self.lastname,
        #         "email": self.email,
        #         "team": self.team,
        #         "subteam": self.subteam,
        #         "chat_id": self.chat_id,
        #         "is_superuser": self.is_superuser,
        #         "is_staff": self.is_staff,
        #     }
        #     custom_user_collection.insert_one(user_data)
    
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
        
        # existing_admin = admin_collection.find_one({"username": self.user.username})
        # if not existing_admin:
        #     admin_collection.insert_one({
        #         "username": self.user.username,
        #         "email": self.user.email,
        #         "usertype": self.user.usertype
        #     })

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
        
        # existing_team_leader = team_leader_collection.find_one({"username": self.user.username})
        # if not existing_team_leader:
        #     team_leader_collection.insert_one({
        #         "username": self.user.username,
        #         "email": self.user.email,
        #         "usertype": self.user.usertype
        #     })

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
        
        # existing_user = user_collection.find_one({"username": self.user.username})
        # if not existing_user:
        #     user_collection.insert_one({
        #         "username": self.user.username,
        #         "email": self.user.email,
        #         "usertype": self.user.usertype
        #     })


    def __str__(self):
        return self.user.username

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
    created_by = models.ForeignKey(CustomUser, related_name='created_projects', on_delete=models.CASCADE, default=1)  
    teams = models.ManyToManyField('Team', related_name='projects_assigned') 
    def __str__(self):
        return self.name
    
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs)  # Save in Django ORM first

    #     # # Fetch assigned teams' names
    #     # assigned_teams = list(self.teams.values_list('name', flat=True))

    #     # # Insert into MongoDB
    #     # project_collection.insert_one({
    #     #     "name": self.name,
    #     #     "description": self.description,
    #     #     "status": self.status,
    #     #     "start_date": str(self.start_date),
    #     #     "deadline": str(self.deadline),
    #     #     "created_by": self.created_by.username,
    #     #     "teams": assigned_teams  # Storing as a list of team names
    #     # })
       
# Team Model
class Team(models.Model):
    name = models.CharField(max_length=100)
    description = models.TextField()
    account_managers = models.ManyToManyField(CustomUser, related_name='managed_teams')  
    team_leader_search = models.ForeignKey(CustomUser, related_name='led_search_teams', on_delete=models.CASCADE, null=True, blank=True)
    team_leader_development = models.ForeignKey(CustomUser, related_name='led_development_teams', on_delete=models.CASCADE, null=True, blank=True)
    team_leader_creative = models.ForeignKey(CustomUser, related_name='led_creative_teams', on_delete=models.CASCADE, null=True, blank=True)
    team = models.CharField(max_length=50, choices=CustomUser.TEAM_CHOICES)
    subteam = models.CharField(max_length=50, choices=CustomUser.SUBTEAM_CHOICES, null=True, blank=True)
    members = models.ManyToManyField(CustomUser, related_name='teams')
    created_by = models.ForeignKey(CustomUser, related_name='created_teams', on_delete=models.CASCADE, default=1)
    projects = models.ManyToManyField(Project, related_name='teams_assigned')  
    def __str__(self):
        return self.name
    
    # def save(self, *args, **kwargs):
    #     """Insert new team data into MongoDB when saving."""
    #     super().save(*args, **kwargs)  # Save in Django ORM first

    #     # # Fetch team details
    #     # account_manager_names = list(self.account_managers.values_list('username', flat=True))
    #     # member_names = list(self.members.values_list('username', flat=True))
    #     # project_names = list(self.projects.values_list('name', flat=True))

    #     # # Insert into MongoDB
    #     # team_collection.insert_one({
    #     #     "name": self.name,
    #     #     "description": self.description,
    #     #     "account_managers": account_manager_names,
    #     #     "team_leader_search": self.team_leader_search.username if self.team_leader_search else None,
    #     #     "team_leader_development": self.team_leader_development.username if self.team_leader_development else None,
    #     #     "team_leader_creative": self.team_leader_creative.username if self.team_leader_creative else None,
    #     #     "team": self.team,
    #     #     "subteam": self.subteam,
    #     #     "members": member_names,
    #     #     "created_by": self.created_by.username,
    #     #     "projects": project_names
    #     # })
    # def delete(self, *args, **kwargs):
    #     for project in self.projects.all():
    #         project.teams.remove(self)  
    #     super().delete(*args, **kwargs)
    #     team_collection.delete_one({"name": self.name})

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
    
    # def save(self, *args, **kwargs):
    #     """Insert new task data into MongoDB when saving."""
    #     super().save(*args, **kwargs)  # Save in Django ORM first

    #     start_date_str = self.start_date.strftime("%Y-%m-%d") if isinstance(self.start_date, datetime) else str(self.start_date)
    #     end_date_str = self.end_date.strftime("%Y-%m-%d") if isinstance(self.end_date, datetime) else str(self.end_date)
    #     # Insert into MongoDB
        
    #     task_collection.insert_one({
    #         "title": self.title,
    #         "description": self.description,
    #         "status": self.status,
    #         "priority": self.priority,
    #         "start_date": start_date_str,
    #         "end_date": end_date_str,
    #         "created_by": self.created_by.username,
    #         "project": self.project.name,
    #         "superadmin_assigned_to": self.superadmin_assigned_to.username if self.superadmin_assigned_to else None,
    #         "admin_assigned_to": self.admin_assigned_to.username if self.admin_assigned_to else None,
    #         "teamleader_assigned_to": self.teamleader_assigned_to.username if self.teamleader_assigned_to else None
    #     })

    def assign_task(self, assigned_by, assigned_to):
        if assigned_by.usertype == 'SuperAdmin':
            self.superadmin_assigned_to = assigned_to
        elif assigned_by.usertype == 'Admin':
            self.admin_assigned_to = assigned_to
        elif assigned_by.usertype == 'TeamLeader':
            self.teamleader_assigned_to = assigned_to
            
        self.save()
    
    # def delete(self, *args, **kwargs):
    #     """Delete task from MongoDB when removed from Django."""
    #     super().delete(*args, **kwargs)
    #     task_collection.delete_one({"title": self.title})

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
    
    # def save(self, *args, **kwargs):
    #     super().save(*args, **kwargs) 

    #     # Insert into MongoDB
    #     timesheet_collection.insert_one({
    #         "date": self.date.strftime("%Y-%m-%d"),
    #         "task": self.task,
    #         "submitted_to": self.submitted_to.username,
    #         "status": self.status,
    #         "description": self.description,
    #         "hours": float(self.hours),
    #         "created_by": self.created_by.username,
    #         "project": self.project.name if self.project else None
    #     })

    # def delete(self, *args, **kwargs):
    #     """Delete timesheet from MongoDB when removed from Django."""
    #     super().delete(*args, **kwargs)
    #     timesheet_collection.delete_one({"date": self.date.strftime("%Y-%m-%d"), "created_by": self.created_by.username})

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
    
    # def save(self, *args, **kwargs):
    #     """Insert new Timesheet Table data into MongoDB when saving."""
    #     super().save(*args, **kwargs)  # Save in Django ORM first

    #     # Insert into MongoDB
    #     timesheet_table_collection.insert_one({
    #         "created_by": self.created_by.username,
    #         "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S"),
    #         "status": self.status,
    #         "comments": self.comments,
    #         "timesheets": [
    #             {"date": ts.date.strftime("%Y-%m-%d"), "task": ts.task, "status": ts.status, "hours": float(ts.hours)}
    #             for ts in self.timesheets.all()
    #         ]
    #     })
        

    def delete(self, *args, **kwargs):
        orphan_timesheets = self.timesheets.all()
        super().delete(*args, **kwargs)  
        # timesheet_table_collection.delete_one({"created_by": self.created_by.username, "created_at": self.created_at.strftime("%Y-%m-%d %H:%M:%S")})
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




