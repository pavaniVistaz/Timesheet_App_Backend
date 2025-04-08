from django.urls import path
from timesheet_app.views.task_views import (
    CreateTaskView, FetchTasksView,
    EditTaskView, DeleteTaskView,AssignTaskView
)

urlpatterns = [
    path('create/', CreateTaskView.as_view(), name='create_task'),
    path('', FetchTasksView.as_view(), name='fetch_tasks'), 
    path('<int:task_id>/edit/', EditTaskView.as_view(), name='edit_task'),
    path('<int:task_id>/delete/', DeleteTaskView.as_view(), name='delete_task'),
    path('<int:task_id>/assign/', AssignTaskView.as_view(), name='assign_task'),
]
