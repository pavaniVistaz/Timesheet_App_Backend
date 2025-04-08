from django.urls import path
from timesheet_app.views.team_views import (
    CreateTeamView, FetchTeamsView, GetAssignedTeamView,
    EditTeamView, DeleteTeamView,
    FetchSubmittedToUsersView
)
urlpatterns = [
    path('create/', CreateTeamView.as_view(), name='create_team'),
    path('', FetchTeamsView.as_view(), name='fetch_teams'),
    path('teamleader/assigned_team/', GetAssignedTeamView.as_view(), name='get-assigned-team'),
    path('<int:team_id>/edit/', EditTeamView.as_view(), name='edit_team'),
    path('<int:team_id>/delete/', DeleteTeamView.as_view(), name='delete_team'),
    path('submitted-to-users/', FetchSubmittedToUsersView.as_view(), name='fetch_submitted_to_users')
    
]
