from rest_framework.views import APIView
from rest_framework import permissions, status
from timesheet_app.models import Timesheet, TimesheetTable, CustomUser
from timesheet_app.serializers import TimesheetSerializer, TimesheetTableSerializer
from rest_framework.response import Response
from django.db.models import Min
from timesheet_app.utils import send_telegram_message


# Fetch Timesheets
class FetchTimesheetsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        timesheets = Timesheet.objects.filter(created_by=user)
        serializer = TimesheetSerializer(timesheets, many=True)
        return Response({"timesheets": serializer.data}, status=status.HTTP_200_OK)

# Edit Timesheet
class EditTimesheetView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, timesheet_id, *args, **kwargs):
        data = request.data
        try:
            timesheet = Timesheet.objects.get(id=timesheet_id, created_by=request.user)
            timesheet.date = data.get('date', timesheet.date)
            timesheet.task = data.get('task', timesheet.task)
            timesheet.submitted_to = data.get('submitted_to', timesheet.submitted_to)
            timesheet.status = data.get('status', timesheet.status)
            timesheet.description = data.get('description', timesheet.description)
            timesheet.hours = data.get('hours', timesheet.hours)
            timesheet.save()

            return Response({
                "message": "Timesheet updated successfully",
                "status": "success",
                "timesheet_id": timesheet.id,
            }, status=status.HTTP_200_OK)
        except Timesheet.DoesNotExist:
            return Response({"message": "Timesheet not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to update timesheet", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Delete Timesheet
class DeleteTimesheetView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, timesheet_id, *args, **kwargs):
        try:
            timesheet = Timesheet.objects.get(id=timesheet_id, created_by=request.user)
            timesheet.delete()
            return Response({"message": "Timesheet deleted successfully", "status": "success"}, status=status.HTTP_200_OK)
        except Timesheet.DoesNotExist:
            return Response({"message": "Timesheet not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to delete timesheet", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)



"""
                                Timesheet Table Views
"""
# Create Timesheet Table
class CreateTimesheetTableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        created_by = request.user.username  # Use username for created_by
        try:
            data['created_by'] = created_by  
            serializer = TimesheetTableSerializer(data=data)
            if serializer.is_valid():
                timesheet_table = serializer.save()
                return Response({
                    "message": "Timesheet table created successfully",
                    "status": "success",
                    "timesheet_table": serializer.data
                }, status=status.HTTP_201_CREATED)
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": "Failed to create timesheet table", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fetch Timesheet Tables for Pending Review
class FetchPendingReviewTimesheetTablesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        selected_user_id = request.query_params.get('user')
        view_mode = request.query_params.get('viewMode')
        date = request.query_params.get('date')

        if selected_user_id:
            timesheet_tables = TimesheetTable.objects.filter(
                created_by_id=selected_user_id
            )
        else:
            timesheet_tables = TimesheetTable.objects.filter(
                created_by=user
            )

        if view_mode == 'Daily':
            timesheet_tables = timesheet_tables.filter(timesheets__date=date)
        elif view_mode == 'Monthly':
            year, month, _ = date.split('-')
            timesheet_tables = timesheet_tables.filter(timesheets__date__year=year, timesheets__date__month=month)

        timesheet_tables = timesheet_tables.annotate(
            earliest_date=Min('timesheets__date')
        ).order_by('earliest_date')  # Order by the earliest date of the timesheets

        serializer = TimesheetTableSerializer(timesheet_tables, many=True)
        return Response({"timesheet_tables": serializer.data}, status=status.HTTP_200_OK)

# Edit Timesheet Table
class EditTimesheetTableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, timesheet_table_id, *args, **kwargs):
        data = request.data
        try:
            timesheet_table = TimesheetTable.objects.get(id=timesheet_table_id, created_by=request.user)
            timesheet_table.timesheets.clear()
            for timesheet_data in data.get('timesheets', []):
                submitted_to_username = timesheet_data.pop('submitted_to')
                submitted_to = CustomUser.objects.get(username=submitted_to_username)
                created_by_username = timesheet_data.pop('created_by')
                created_by = CustomUser.objects.get(username=created_by_username)
                timesheet_id = timesheet_data.get('id')
                if timesheet_id:
                    timesheet = Timesheet.objects.get(id=timesheet_id)
                    for key, value in timesheet_data.items():
                        setattr(timesheet, key, value)
                    timesheet.submitted_to = submitted_to
                    timesheet.created_by = created_by
                    timesheet.save()
                else:
                    timesheet = Timesheet.objects.create(submitted_to=submitted_to, created_by=created_by, **timesheet_data)
                timesheet_table.timesheets.add(timesheet)
            timesheet_table.save()
            serializer = TimesheetTableSerializer(timesheet_table)
            return Response({
                "message": "Timesheet table updated successfully",
                "status": "success",
                "timesheet_table": serializer.data
            }, status=status.HTTP_200_OK)
        except TimesheetTable.DoesNotExist:
            return Response({"message": "Timesheet table not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except CustomUser.DoesNotExist:
            return Response({"message": "User not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Timesheet.DoesNotExist:
            return Response({"message": "Timesheet not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to update timesheet table", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Delete Timesheet Table
class DeleteTimesheetTableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, timesheet_table_id, *args, **kwargs):
        try:
            timesheet_table = TimesheetTable.objects.get(id=timesheet_table_id)
            if timesheet_table.created_by != request.user:
                return Response({"message": "Permission denied", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)
            timesheet_table.delete()  # This will also delete related timesheets
            return Response({"message": "Timesheet table and related timesheets deleted successfully", "status": "success"}, status=status.HTTP_200_OK)
        except TimesheetTable.DoesNotExist:
            return Response({"message": "Timesheet table not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:

            return Response({"message": "Failed to delete timesheet table", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""
                                Timesheet Table Review Views
"""

# Send Timesheet Table to Review By User
class SendTimesheetTableToReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, timesheet_table_id, *args, **kwargs):
        try:
            timesheet_table = TimesheetTable.objects.get(id=timesheet_table_id, created_by=request.user)
            timesheet_table.status = 'Sent for Review'
            timesheet_table.save()
            # Send one notification to the user the timesheets are submitted to
            if timesheet_table.timesheets.exists():
                submitted_to_user = timesheet_table.timesheets.first().submitted_to
                
                message = f"📢 Timesheet table created by {request.user.username} has been sent for review."
                send_telegram_message(submitted_to_user.chat_id,message)
                
            return Response({"message": "Timesheet table sent for review successfully", "status": "success"}, status=status.HTTP_200_OK)
        except TimesheetTable.DoesNotExist:
            return Response({"message": "Timesheet table not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to send timesheet table to review", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fetch Timesheet Tables for Team Leader Sent for Review By User
class FetchTimesheetTablesForReviewView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.usertype == 'TeamLeader':
            timesheet_tables = TimesheetTable.objects.filter(
                timesheets__submitted_to=user,
                status='Sent for Review'
            ).distinct()
            serializer = TimesheetTableSerializer(timesheet_tables, many=True)
            return Response({"timesheet_tables": serializer.data}, status=status.HTTP_200_OK)
        elif user.usertype == 'Admin':  # Add this block
            timesheet_tables = TimesheetTable.objects.filter(
                timesheets__submitted_to=user,
                status='Sent for Review'
            ).distinct()
            serializer = TimesheetTableSerializer(timesheet_tables, many=True)
            return Response({"timesheet_tables": serializer.data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Permission denied", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)

# Team Leader Review Timesheet Table Either Approve or Reject
class TeamLeaderReviewTimesheetTableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, timesheet_table_id, *args, **kwargs):
        try:
            timesheet_table = TimesheetTable.objects.get(id=timesheet_table_id)
            action = request.data.get('action')
            feedback = request.data.get('feedback', '')

            if action == 'approve':
                timesheet_table.status = 'Approved by Team Leader'
                timesheet_table.comments = ''  # Clear comments on approval
                timesheet_table.save()
                
                # Telegram Notifications
                message = f"✅ Your timesheet table has been approved by {request.user.username}. 🎉"
                send_telegram_message(timesheet_table.created_by.chat_id,message)
                
            elif action == 'reject':
                timesheet_table.status = 'Rejected by Team Leader'
                timesheet_table.comments = feedback  # Save comments on rejection
                timesheet_table.save()
                
                # Telegram Notifications
                message = f"❌ Your timesheet table has been rejected by {request.user.username}. \n\n📝 Feedback: {feedback}"
                send_telegram_message(timesheet_table.created_by.chat_id,message)
                
            else:
                return Response({"message": "Invalid action", "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": "Timesheet table reviewed successfully", "status": "success"}, status=status.HTTP_200_OK)
        except TimesheetTable.DoesNotExist:
            return Response({"message": "Timesheet table not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to review timesheet table", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


# Fetch Comments for a Specific Timesheet Table
class FetchTimesheetTableCommentsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, timesheet_table_id, *args, **kwargs):
        try:
            timesheet_table = TimesheetTable.objects.get(id=timesheet_table_id)
            comments = timesheet_table.comments
            return Response({"comments": comments}, status=status.HTTP_200_OK)
        except TimesheetTable.DoesNotExist:
            return Response({"message": "Timesheet table not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to fetch comments", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class AdminReviewTimesheetTableView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, timesheet_table_id, *args, **kwargs):
        try:
            timesheet_table = TimesheetTable.objects.get(id=timesheet_table_id)
            action = request.data.get('action')
            feedback = request.data.get('feedback', '')

            if action == 'approve':
                timesheet_table.status = 'Approved by Admin'
                timesheet_table.comments = ''  # Clear comments on approval
                timesheet_table.save()
                # Send one notification to the user who created the timesheet table
                
                message = f"✅ Your timesheet table has been approved by {request.user.username}. 🎉"
                send_telegram_message(timesheet_table.created_by.chat_id,message)
            
            elif action == 'reject':
                timesheet_table.status = 'Rejected by Admin'
                timesheet_table.comments = feedback  # Save comments on rejection
                timesheet_table.save()
                # Send one notification to the user who created the timesheet table
                message = f"❌ Your timesheet table has been rejected by {request.user.username}. \n\n📝 Feedback: {feedback}"
                send_telegram_message(timesheet_table.created_by.chat_id,message)
                
            else:
                return Response({"message": "Invalid action", "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)

            return Response({"message": "Timesheet table reviewed successfully", "status": "success"}, status=status.HTTP_200_OK)
        except TimesheetTable.DoesNotExist:
            return Response({"message": "Timesheet table not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to review timesheet table", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fetch Timesheet Tables to  View By Admin , Team Leader and Super Admin
class FetchTimesheetTablesView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        selected_user_id = request.query_params.get('user')
        view_mode = request.query_params.get('viewMode')
        date = request.query_params.get('date')
        table_status = request.query_params.get('table_status')
       
        if selected_user_id:
            timesheet_tables = TimesheetTable.objects.filter(created_by_id=selected_user_id, status=table_status)
            print(timesheet_tables)
        else:
            timesheet_tables = TimesheetTable.objects.filter(created_by=user, status=table_status)
            print(timesheet_tables)

        if view_mode == 'Daily':
            timesheet_tables = timesheet_tables.filter(timesheets__date=date)
        elif view_mode == 'Monthly':
            year, month, _ = date.split('-')
            timesheet_tables = timesheet_tables.filter(timesheets__date__year=year, timesheets__date__month=month)

        timesheet_tables = timesheet_tables.annotate(
            earliest_date=Min('timesheets__date')
        ).order_by('earliest_date')  # Order by the earliest date of the timesheets

       

        serializer = TimesheetTableSerializer(timesheet_tables, many=True)
        return Response({"timesheet_tables": serializer.data}, status=status.HTTP_200_OK)
