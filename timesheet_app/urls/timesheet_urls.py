from django.urls import path
from timesheet_app.views.timesheet_views import (
    FetchTimesheetsView, CreateTimesheetTableView,
    FetchPendingReviewTimesheetTablesView, EditTimesheetTableView,
    DeleteTimesheetTableView, SendTimesheetTableToReviewView,
    FetchTimesheetTablesForReviewView, TeamLeaderReviewTimesheetTableView,
    FetchTimesheetTableCommentsView, AdminReviewTimesheetTableView,
    FetchTimesheetTablesView
)

urlpatterns = [
    # Timesheet Tables CRUD Operations
    path('create/', CreateTimesheetTableView.as_view(), name='create_timesheet_table'),
    path('pending-review/', FetchPendingReviewTimesheetTablesView.as_view(), name='fetch_pending_review_timesheet_tables'),
    path('<int:timesheet_table_id>/edit/', EditTimesheetTableView.as_view(), name='edit_timesheet_table'),
    path('<int:timesheet_table_id>/delete/', DeleteTimesheetTableView.as_view(), name='delete_timesheet_table'),
   

    # Timesheet Tables Review Operations
    path('<int:timesheet_table_id>/send-to-review/', SendTimesheetTableToReviewView.as_view(), name='send_timesheet_table_to_review'),
    path('review/', FetchTimesheetTablesForReviewView.as_view(), name='fetch_timesheet_tables_for_review'),
    path('<int:timesheet_table_id>/team-leader-review/', TeamLeaderReviewTimesheetTableView.as_view(), name='team_leader_review_timesheet_table'),
    path('<int:timesheet_table_id>/comments/', FetchTimesheetTableCommentsView.as_view(), name='fetch_timesheet_table_comments'),
    path('<int:timesheet_table_id>/admin-review/', AdminReviewTimesheetTableView.as_view(), name='admin_review_timesheet_table'),

    # Fetch Timesheets In ViewTimesheet Page
    path('', FetchTimesheetTablesView.as_view(), name='fetch_timesheet_tables'),
    path('timesheets/', FetchTimesheetsView.as_view(), name='fetch_timesheets'),
]
