from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView
from .views import (
    CustomTokenObtainPairView, RegisterUserView, CreateTeamView, FetchUsersView, FetchTeamsView, 
    EditTeamView, DeleteTeamView, CreateProjectView, FetchProjectsView, EditProjectView, DeleteProjectView,
    AssignTeamToProjectView, FetchNotificationsView, MarkNotificationAsReadView, 
    FetchProjectProgressView, CreateTaskView, FetchProjectTasksView, FetchTaskDetailsView, EditTaskView, DeleteTaskView,
    FetchAccountManagersView, 
    FetchAssignedProjectsView, FetchAssignedTeamView, FetchAdminProjectsView, FetchAdminTeamsView,
    FetchSubteamsAndMembersView, FetchAssignedTasksView, FetchTasksView, FetchTeamLeadersView, AssignTaskView, FetchProjectTeamLeadersView,
    FetchSubmittedToUsersView, CreateTimesheetTableView, FetchTimesheetTablesView, EditTimesheetTableView, DeleteTimesheetTableView,
    FetchTimesheetsView, SendTimesheetTableToReviewView, TeamLeaderReviewTimesheetTableView, FetchTimesheetTablesForReviewView,
    FetchPendingReviewTimesheetTablesView, FetchTimesheetTableCommentsView, AdminReviewTimesheetTableView,
    FetchUserDetailsView, ChangePasswordView, FetchUserTeamView, FetchWorkingHoursView,LogoutView,AuthCheckView,RequestPasswordResetCodeView,
)

urlpatterns = [
    # Login and Register
    path('login/', CustomTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path("logout/", LogoutView.as_view(), name="logout"),
    path('register/', RegisterUserView.as_view(), name='register_user'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path("auth-check/", AuthCheckView.as_view(), name="auth-check"),
    
    # Change Password
    path('request-password-reset-code/', RequestPasswordResetCodeView.as_view(), name='request_password_reset_code'),
    path('change-password/', ChangePasswordView.as_view(), name='change_password'),
    
    # Fetch All Users(Super Admin , Admin, Team Leader, User)
    path('users/', FetchUsersView.as_view(), name='fetch_users'),
   
    # Teams CRUD Operations
    path('teams/create/', CreateTeamView.as_view(), name='create_team'),
    path('teams/', FetchTeamsView.as_view(), name='fetch_teams'),
    path('teams/<int:team_id>/edit/', EditTeamView.as_view(), name='edit_team'),
    path('teams/<int:team_id>/delete/', DeleteTeamView.as_view(), name='delete_team'),
    path('teams/assigned/', FetchAssignedTeamView.as_view(), name='fetch_assigned_team'),
    
    #  Admin Based Team View 
    path('teams/admin/', FetchAdminTeamsView.as_view(), name='fetch_admin_teams'), 
    path('account-managers/', FetchAccountManagersView.as_view(), name='fetch_account_managers'),
    path('subteams-and-users/', FetchSubteamsAndMembersView.as_view(), name='fetch_subteams_and_users'),
        
    # Projects CRUD Operations
    path('projects/create/', CreateProjectView.as_view(), name='create_project'),
    path('projects/', FetchProjectsView.as_view(), name='fetch_projects'),
    path('projects/<int:project_id>/edit/', EditProjectView.as_view(), name='edit_project'),
    path('projects/<int:project_id>/delete/', DeleteProjectView.as_view(), name='delete_project'),
    path('projects/<int:project_id>/assign-team/', AssignTeamToProjectView.as_view(), name='assign_team_to_project'),
    path('projects/<int:project_id>/progress/', FetchProjectProgressView.as_view(), name='fetch_project_progress'),
   
    # Notifications
    path('notifications/', FetchNotificationsView.as_view(), name='fetch_notifications'),
    path('notifications/<int:notification_id>/read/', MarkNotificationAsReadView.as_view(), name='mark_notification_as_read'),
    
    # Admin Based Project View
    path('projects/assigned/', FetchAssignedProjectsView.as_view(), name='fetch_assigned_projects'),
    path('projects/admin/', FetchAdminProjectsView.as_view(), name='fetch_admin_projects'), 
    path('projects/<int:project_id>/team-leaders/', FetchProjectTeamLeadersView.as_view(), name='fetch_project_team_leaders'),
   
    # Tasks CRUD Operations
    path('tasks/create/', CreateTaskView.as_view(), name='create_task'),
    path('tasks/', FetchTasksView.as_view(), name='fetch_tasks'), 
    path('tasks/<int:task_id>/', FetchTaskDetailsView.as_view(), name='fetch_task_details'),
    path('tasks/<int:task_id>/edit/', EditTaskView.as_view(), name='edit_task'),
    path('tasks/<int:task_id>/delete/', DeleteTaskView.as_view(), name='delete_task'),
    
    # Assign Tasks 
    path('tasks/assigned/', FetchAssignedTasksView.as_view(), name='fetch_assigned_tasks'),
    path('tasks/<int:task_id>/assign/', AssignTaskView.as_view(), name='assign_task'),
   
    # Timesheet Tables CRUD Operations
    path('timesheet-tables/create/', CreateTimesheetTableView.as_view(), name='create_timesheet_table'),
    path('timesheet-tables/pending-review/', FetchPendingReviewTimesheetTablesView.as_view(), name='fetch_pending_review_timesheet_tables'),
    path('timesheet-tables/<int:timesheet_table_id>/edit/', EditTimesheetTableView.as_view(), name='edit_timesheet_table'),
    path('timesheet-tables/<int:timesheet_table_id>/delete/', DeleteTimesheetTableView.as_view(), name='delete_timesheet_table'),
   

    # Timesheet Tables Review Operations
    path('timesheet-tables/<int:timesheet_table_id>/send-to-review/', SendTimesheetTableToReviewView.as_view(), name='send_timesheet_table_to_review'),
    path('timesheet-tables/review/', FetchTimesheetTablesForReviewView.as_view(), name='fetch_timesheet_tables_for_review'),
    path('timesheet-tables/<int:timesheet_table_id>/team-leader-review/', TeamLeaderReviewTimesheetTableView.as_view(), name='team_leader_review_timesheet_table'),
    path('timesheet-tables/<int:timesheet_table_id>/comments/', FetchTimesheetTableCommentsView.as_view(), name='fetch_timesheet_table_comments'),
    path('timesheet-tables/<int:timesheet_table_id>/admin-review/', AdminReviewTimesheetTableView.as_view(), name='admin_review_timesheet_table'),

    # Fetch Timesheets In ViewTimesheet Page
    path('timesheet-tables/', FetchTimesheetTablesView.as_view(), name='fetch_timesheet_tables'),
    path('timesheets/', FetchTimesheetsView.as_view(), name='fetch_timesheets'),
    path('users/<int:user_id>/', FetchUserDetailsView.as_view(), name='fetch_user_details'),
    path('user/team/', FetchUserTeamView.as_view(), name='fetch_user_team'),
    path('working-hours/', FetchWorkingHoursView.as_view(), name='fetch_working_hours'),

    # Not used
    
    path('projects/<int:project_id>/tasks/', FetchProjectTasksView.as_view(), name='fetch_project_tasks'),
    path('teams/<int:team_id>/leaders/', FetchTeamLeadersView.as_view(), name='fetch_team_leaders'), 
    path('teams/leaders/', FetchTeamLeadersView.as_view(), name='fetch_team_leaders'), 
    path('submitted-to-users/', FetchSubmittedToUsersView.as_view(), name='fetch_submitted_to_users'),
  
]
