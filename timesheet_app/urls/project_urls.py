from django.urls import path
from timesheet_app.views.project_views import (
    CreateProjectView, FetchProjectsView, FetchAssignedProjectsView,
    EditProjectView, DeleteProjectView,FetchProjectTeamLeadersView
    
)

urlpatterns = [
    path('create/', CreateProjectView.as_view(), name='create_project'),
    path('', FetchProjectsView.as_view(), name='fetch_projects'),
    path('assigned/', FetchAssignedProjectsView.as_view(), name='fetch_assigned_projects'),
    path('<int:project_id>/edit/', EditProjectView.as_view(), name='edit_project'),
    path('<int:project_id>/delete/', DeleteProjectView.as_view(), name='delete_project'),
    path('<int:project_id>/team-leaders/', FetchProjectTeamLeadersView.as_view(), name='fetch_project_team_leaders'),
]
