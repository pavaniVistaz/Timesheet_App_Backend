from django.urls import path
from timesheet_app.views.message_view import CustomMessageView
urlpatterns = [
    path("send-telegram/",CustomMessageView.as_view(),name="custom_message")
]
