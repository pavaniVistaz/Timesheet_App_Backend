from django.urls import path
from timesheet_app.views.user_views import (
    FetchUserDetailsView, UpdateProfileView, FetchUsersView, FetchTeamLeadersView,FetchWorkingHoursView,FetchAllUsers
)
urlpatterns = [
    path('users/<int:user_id>/', FetchUserDetailsView.as_view(), name='fetch_user_details'),
    path('update-profile/<int:user_id>/', UpdateProfileView.as_view(), name='update_profile'), 
    path('users/', FetchUsersView.as_view(), name='fetch_users'),
    path('teams/<int:team_id>/leaders/', FetchTeamLeadersView.as_view(), name='fetch_team_leaders'), 
    path('teams/leaders/', FetchTeamLeadersView.as_view(), name='fetch_team_leaders'), 
    path('working-hours/', FetchWorkingHoursView.as_view(), name='fetch_working_hours'),
    path('all-users/',FetchAllUsers.as_view(),name ='fetch_all_users' )
]
