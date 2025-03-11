from rest_framework import permissions, status
from rest_framework.response import Response
from django.http import JsonResponse
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from .models import CustomUser, Team, Project, Task, Notification, Timesheet, TimesheetTable
from django.contrib.auth.hashers import check_password, make_password
from django.contrib.auth import authenticate
from django.db.models import Q, Min, Sum
from .serializers import TimesheetSerializer, TimesheetTableSerializer
from django.contrib.auth import update_session_auth_hash
from .utils import send_telegram_message
import random
# Login Check
class CustomTokenObtainPairView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username = request.data.get("username")
        password = request.data.get("password")
        user = authenticate(username=username, password=password)

        if user:
            return self.generate_token_response(user)

        try:
            user = CustomUser.objects.get(username=username)
            if check_password(password, user.password):
                return self.generate_token_response(user)
            return Response({"message": "Invalid password", "status": "failure"}, status=status.HTTP_401_UNAUTHORIZED)
        except CustomUser.DoesNotExist:
            return Response({"message": "User not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

    def generate_token_response(self, user):
        refresh = RefreshToken.for_user(user)
        
        response = JsonResponse({
            "message": "Login successful",
            "status": "success",
            "firstname": user.firstname,
            "username": user.username,
            "usertype": user.usertype,
            "email": user.email,
            "user_id": user.id,
        })

        # Set HttpOnly and Secure cookies
        response.set_cookie(
            key="access_token",
            value=str(refresh.access_token),
            httponly=True,  # Prevents JavaScript access (XSS protection)
            secure=True,  # Only works on HTTPS
            samesite="Strict",  # Prevents CSRF attacks
            max_age=3600,  # 1-hour expiry
        )

        response.set_cookie(
            key="refresh_token",
            value=str(refresh),
            httponly=True,
            secure=True,
            samesite="Strict",
            max_age=86400,  
        )

        return response

# Logout
class LogoutView(APIView):
    def post(self, request):
        response = JsonResponse({"message": "Logout successful", "status": "success"})
        
        # Remove authentication cookies by setting them to an empty value and expiring them
        response.delete_cookie("access_token")
        response.delete_cookie("refresh_token")

        return response
    
# check auth  
class AuthCheckView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request):
        return Response({"message": "Authenticated", "status": "success"})
    
# User Registration
class RegisterUserView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        data = request.data
        usertype = data.get('usertype')
        firstname = data.get('firstname')
        lastname = data.get('lastname')
        email = data.get('email')
        team = data.get('team')
        subteam = data.get('subteam')
        password = data.get('password')
        chat_id = data.get('chat_id')  
        
        username = firstname
        try:
            # Create the user
            user = CustomUser.objects.create(
                usertype=usertype,
                firstname=firstname,
                lastname=lastname,
                email=email,
                team=team,
                subteam=subteam,
                username=username,
                password=make_password(password),
                chat_id=chat_id 
            )
            message = f"Welcome to the Timesheet App! Your username is {username}, and your password is {password}. Please log in to the app and change your password immediately."
            send_telegram_message(chat_id, message)
            return Response({
                "message": "User registered successfully",
                "status": "success",
                "username": user.username,
                "usertype": user.usertype,
                "email": user.email,
            }, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({"message": "Registration failed", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Change Password
class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        user = request.user
        current_password = request.data.get('current_password')
        new_password = request.data.get('new_password')
        confirm_password = request.data.get('confirm_password')
        user_data = CustomUser.objects.get(id=user.id)
        if not check_password(current_password, user.password):
            return Response({"message": "Current password is incorrect"}, status=status.HTTP_400_BAD_REQUEST)

        if new_password != confirm_password:
            return Response({"message": "New passwords do not match"}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(new_password)
        user.save()
        message = f"Your password has been changed successfully. If you did not make this change, please contact the administrator immediately."
        send_telegram_message(user_data.chat_id, message)
        
        update_session_auth_hash(request, user)  # Important to update the session with the new password

        return Response({"message": "Password changed successfully"}, status=status.HTTP_200_OK)
   
# Fetch Users
class FetchUsersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        usertype = request.query_params.get('usertype')
        subteam = request.query_params.get('subteam')
        
        if user.usertype == 'SuperAdmin':
            users = CustomUser.objects.filter(
                Q(usertype='Admin') | Q(usertype='TeamLeader') | Q(usertype='User')
            ).exclude(username='Narayan')
        elif user.usertype == 'Admin':
            users = CustomUser.objects.filter(
                Q(usertype='TeamLeader') | Q(usertype='User')
            )
        elif user.usertype == 'TeamLeader':
            users = CustomUser.objects.filter(team=user.team).exclude(id=user.id)
        else:
            users = CustomUser.objects.none()

        if usertype:
            users = users.filter(usertype__in=usertype.split(','))
        if subteam:
            users = users.filter(subteam=subteam)
        
        user_data = [{"id": user.id, "username": user.username, "team": user.team} for user in users]
        return Response({"users": user_data}, status=status.HTTP_200_OK)

  
"""
                                Team View
"""
# Create Team
class CreateTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        name = data.get('name')
        description = data.get('description')
        account_manager_id = data.get('account_manager_id')
        team_leader_search_id = data.get('team_leader_search')
        team_leader_development_id = data.get('team_leader_development')
        team_leader_creative_id = data.get('team_leader_creative')
        team = data.get('team')
        subteam = data.get('subteam')
        member_ids = data.get('member_ids', [])
        created_by = request.user  
        try:
            account_manager = CustomUser.objects.get(id=account_manager_id)
            team_leader_search = CustomUser.objects.get(id=team_leader_search_id) if team_leader_search_id else None
            team_leader_development = CustomUser.objects.get(id=team_leader_development_id) if team_leader_development_id else None
            team_leader_creative = CustomUser.objects.get(id=team_leader_creative_id) if team_leader_creative_id else None
            members = CustomUser.objects.filter(id__in=member_ids)

            team = Team.objects.create(
                name=name,
                description=description,
                account_manager=account_manager,
                team_leader_search=team_leader_search,
                team_leader_development=team_leader_development,
                team_leader_creative=team_leader_creative,
                team=team,
                subteam=subteam,
                created_by=created_by  
            )
            team.members.set(members)
            team.save()

            return Response({
                "message": "Team created successfully",
                "status": "success",
                "team_id": team.id,
            }, status=status.HTTP_201_CREATED)
        except CustomUser.DoesNotExist as e:
            return Response({"message": "User not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to create team", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fetch Teams to Team List
class FetchTeamsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        teams = Team.objects.all()
        team_data = []
        for team in teams:
            team_data.append({
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "account_manager": {
                    "id": team.account_manager.id,
                    "username": team.account_manager.username
                },
                "team_leader_search": {
                    "id": team.team_leader_search.id,
                    "username": team.team_leader_search.username
                } if team.team_leader_search else None,
                "team_leader_development": {
                    "id": team.team_leader_development.id,
                    "username": team.team_leader_development.username
                } if team.team_leader_development else None,
                "team_leader_creative": {
                    "id": team.team_leader_creative.id,
                    "username": team.team_leader_creative.username
                } if team.team_leader_creative else None,
                "subteams": [
                    {
                        "id": member.id,
                        "username": member.username,
                        "subteam": member.subteam
                    } for member in team.members.all()
                ],
                "created_by": {
                    "id": team.created_by.id,
                    "username": team.created_by.username
                }
            })
        return Response({"teams": team_data}, status=status.HTTP_200_OK)

# Edit Team
class EditTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, team_id, *args, **kwargs):
        data = request.data
        try:
            team = Team.objects.get(id=team_id)
            current_members = set(team.members.all())

            team.name = data.get('name', team.name)
            team.description = data.get('description', team.description)
            team.account_manager_id = data.get('account_manager_id', team.account_manager_id)
            team.team_leader_search_id = data.get('team_leader_search', team.team_leader_search_id)
            team.team_leader_development_id = data.get('team_leader_development', team.team_leader_development_id)
            team.team_leader_creative_id = data.get('team_leader_creative', team.team_leader_creative_id)
            team.team = data.get('team', team.team)
            team.subteam = data.get('subteam', team.subteam)
            member_ids = data.get('member_ids', [])
            members = CustomUser.objects.filter(id__in=member_ids)
            team.members.set(members)
            team.save()

            new_members = set(members) - current_members
            removed_members = current_members - set(members)

            # Notify project members if the team is assigned to a project
            projects = Project.objects.filter(team=team)
            for project in projects:
                for user in new_members:
                    message = f"You have been added to the project: <b>{project.name}</b>"
                    send_telegram_message(user.chat_id, message)
                    Notification.objects.create(
                        user=user,
                        message=f"You have been added to the project: <b>{project.name}</b>"
                    )
                for user in removed_members:
                    message = f"You have been removed from the project: <b>{project.name}</b>"
                    send_telegram_message(user.chat_id, message)
                    Notification.objects.create(
                        user=user,
                        message=f"You have been removed from the project: <b>{project.name}</b>"
                    )

            return Response({
                "message": "Team updated successfully",
                "status": "success",
                "team_id": team.id,
            }, status=status.HTTP_200_OK)
        except Team.DoesNotExist:
            return Response({"message": "Team not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to update team", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR) 

# Delete Team     
class DeleteTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, team_id, *args, **kwargs):
        try:
            team = Team.objects.get(id=team_id)
            projects = Project.objects.filter(team=team)

            # Notify all team members if the team is assigned to any project
            if projects.exists():
                users_to_notify = list(team.members.all())
                if team.account_manager:
                    users_to_notify.append(team.account_manager)
                if team.team_leader_search:
                    users_to_notify.append(team.team_leader_search)
                if team.team_leader_development:
                    users_to_notify.append(team.team_leader_development)
                if team.team_leader_creative:
                    users_to_notify.append(team.team_leader_creative)

                for project in projects:
                    for user in users_to_notify:
                        message = f"The team <b>{team.name}</b> has been deleted. You have been removed from the project: <b>{project.name}</b>"
                        send_telegram_message(user.chat_id, message)
                        Notification.objects.create(
                            user=user,
                            message=message
                        )

            team.delete()
            return Response({"message": "Team deleted successfully", "status": "success"}, status=status.HTTP_200_OK)
        except Team.DoesNotExist:
            return Response({"message": "Team not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to delete team", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fetch Assigned Team Based on the Admin
class FetchAssignedTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.usertype == 'Admin':
            try:
                teams = Team.objects.filter(account_manager=user)
                if not teams.exists():
                    return Response({"message": "No teams found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
                
                team_data = []
                for team in teams:
                    team_data.append({
                        "id": team.id,
                        "name": team.name,
                        "description": team.description,
                        "account_manager": {
                            "id": team.account_manager.id,
                            "username": team.account_manager.username
                        },
                        "team_leader_search": {
                            "id": team.team_leader_search.id,
                            "username": team.team_leader_search.username
                        } if team.team_leader_search else None,
                        "team_leader_development": {
                            "id": team.team_leader_development.id,
                            "username": team.team_leader_development.username
                        } if team.team_leader_development else None,
                        "team_leader_creative": {
                            "id": team.team_leader_creative.id,
                            "username": team.team_leader_creative.username
                        } if team.team_leader_creative else None,
                        "subteams": [
                            {
                                "id": member.id,
                                "username": member.username,
                                "subteam": member.subteam
                            } for member in team.members.all()
                        ] if team.members.exists() else [],
                        "created_by": {
                            "id": team.created_by.id,
                            "username": team.created_by.username
                        }   
                    })
                return Response({"teams": team_data}, status=status.HTTP_200_OK)
            except Exception as e:
                return Response({"message": "Failed to fetch assigned teams", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({"message": "Permission denied", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)


"""
                                Project View
"""

# Create Project
class CreateProjectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        name = data.get('name')
        description = data.get('description')
        project_status = data.get('status')
        start_date = data.get('start_date')
        deadline = data.get('deadline')
        created_by = request.user  

        try:
            project = Project.objects.create(
                name=name,
                description=description,
                status=project_status,
                start_date=start_date,
                deadline=deadline,
                created_by=created_by  
            )
            return Response({
                "message": "Project created successfully",
                "status": "success",
                "project_id": project.id,
            }, status=status.HTTP_201_CREATED)
        except CustomUser.DoesNotExist as e:
            return Response({"message": "User not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to create project", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fetch Projects to Project List
class FetchProjectsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        projects = Project.objects.all()
        project_data = [
            {
                "id": project.id,
                "name": project.name,
                "description": project.description,
                "status": project.status,
                "start_date": project.start_date,
                "deadline": project.deadline,
                "created_by":project.created_by.username,
                "account_manager": {
                    "id": project.team.account_manager.id,
                    "username": project.team.account_manager.username
                } if project.team and project.team.account_manager else None,
                "team": {
                    "id": project.team.id,
                    "name": project.team.name,
                    "team_leader_search": {
                        "id": project.team.team_leader_search.id,
                        "username": project.team.team_leader_search.username
                    } if project.team.team_leader_search else None,
                    "team_leader_creative": {
                        "id": project.team.team_leader_creative.id,
                        "username": project.team.team_leader_creative.username
                    } if project.team.team_leader_creative else None,
                    "team_leader_development": {
                        "id": project.team.team_leader_development.id,
                        "username": project.team.team_leader_development.username
                    } if project.team.team_leader_development else None,
                    "subteams": [
                        {
                            "id": member.id,
                            "username": member.username,
                            "subteam": member.subteam
                        } for member in project.team.members.all()
                    ] if project.team else []
                } if project.team else None,
            }
            for project in projects
        ]
        return Response({"projects": project_data}, status=status.HTTP_200_OK)

# Edit Project
class EditProjectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, project_id, *args, **kwargs):
        data = request.data
        try:
            project = Project.objects.get(id=project_id)
            project.name = data.get('name', project.name)
            project.description = data.get('description', project.description)
            project.status = data.get('status', project.status)
            project.start_date = data.get('start_date', project.start_date)
            project.deadline = data.get('deadline', project.deadline)
            project.save()

            return Response({
                "message": "Project updated successfully",
                "status": "success",
                "project_id": project.id,
            }, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response({"message": "Project not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to update project", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Delete Project
class DeleteProjectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, project_id, *args, **kwargs):
        try:
            project = Project.objects.get(id=project_id)
            team = project.team 

            if team:
                users_to_notify = list(team.members.all())

                if team.account_manager and team.account_manager not in users_to_notify:
                    users_to_notify.append(team.account_manager)
                if team.team_leader_search and team.team_leader_search not in users_to_notify:
                    users_to_notify.append(team.team_leader_search)
                if team.team_leader_development and team.team_leader_development not in users_to_notify:
                    users_to_notify.append(team.team_leader_development)
                if team.team_leader_creative and team.team_leader_creative not in users_to_notify:
                    users_to_notify.append(team.team_leader_creative)

                for user in users_to_notify:
                    message = f"The project <b>{project.name}</b> has been deleted. You have been removed from this project."
                    send_telegram_message(user.chat_id, message)
                    Notification.objects.create(
                        user=user,
                        message=message
                    )
            project.delete()
            return Response({"message": "Project deleted successfully", "status": "success"}, status=status.HTTP_200_OK)

        except Project.DoesNotExist:
            return Response({"message": "Project not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to delete project", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Assign Team to Project
class AssignTeamToProjectView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, project_id, *args, **kwargs):
        data = request.data
        team_id = data.get('team_id')

        try:
            project = Project.objects.get(id=project_id)
            team = Team.objects.get(id=team_id)

            # Get current team members
            current_members = set(project.team.members.all()) if project.team else set()

            # Assign team to the project
            project.team = team
            project.save()

            # Get new team members
            new_members = set(team.members.all()) - current_members
            removed_members = current_members - set(team.members.all())

            # Create notifications for newly added users in the team, including team leaders and account managers
            users_to_notify = list(new_members)
            if team.account_manager and team.account_manager not in current_members:
                users_to_notify.append(team.account_manager)
            if team.team_leader_search and team.team_leader_search not in current_members:
                users_to_notify.append(team.team_leader_search)
            if team.team_leader_development and team.team_leader_development not in current_members:
                users_to_notify.append(team.team_leader_development)
            if team.team_leader_creative and team.team_leader_creative not in current_members:
                users_to_notify.append(team.team_leader_creative)

            for user in users_to_notify:
                message = f"You have been added to the project: <b>{project.name}</b>"
                send_telegram_message(user.chat_id, message)
                Notification.objects.create(
                    user=user,
                    message=f"You have been added to the project: <b>{project.name}</b>"
                )

            for user in removed_members:
                message = f"You have been removed from the project: <b>{project.name}</b>"
                send_telegram_message(user.chat_id, message)
                Notification.objects.create(
                    user=user,
                    message=f"You have been removed from the project: <b>{project.name}</b>"
                )

            return Response({
                "message": "Team assigned to project successfully",
                "status": "success",
                "project_id": project.id,
            }, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response({"message": "Project not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Team.DoesNotExist:
            return Response({"message": "Team not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to assign team to project", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fetch Project Progress
class FetchProjectProgressView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id, *args, **kwargs):
        try:
            project = Project.objects.get(id=project_id)
            progress = calculate_project_progress(project)
            return Response({"progress": progress}, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response({"message": "Project not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        
# Calculate Project Progress
def calculate_project_progress(project):
    total_tasks = project.tasks.count()
    if total_tasks == 0:
        return 0
    completed_tasks = project.tasks.filter(status='Completed').count()
    progress = (completed_tasks / total_tasks) * 100
    return int(progress)

"""
                                Notification View
"""
# Fetch Notifications
class FetchNotificationsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        notifications = Notification.objects.filter(user=user, is_read=False)
        notification_data = [
            {
                "id": notification.id,
                "message": notification.message,
                "created_at": notification.created_at,
            }
            for notification in notifications
        ]
        return Response({"notifications": notification_data}, status=status.HTTP_200_OK)

# Mark Notification as Read
class MarkNotificationAsReadView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, notification_id, *args, **kwargs):
        try:
            notification = Notification.objects.get(id=notification_id, user=request.user)
            notification.is_read = True
            notification.save()
            return Response({"message": "Notification marked as read", "status": "success"}, status=status.HTTP_200_OK)
        except Notification.DoesNotExist:
            return Response({"message": "Notification not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

"""
                                Admin Based Team View 
"""
# Fetch Teams Created by Admin At Assign Projects
class FetchAdminTeamsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.usertype == 'Admin':
            teams = Team.objects.filter(created_by=user)
            team_data = [
                {
                    "id": team.id,
                    "name": team.name,
                    "description": team.description,
                    "account_manager": {
                        "id": team.account_manager.id,
                        "username": team.account_manager.username
                    },
                    "team_leader_search": {
                        "id": team.team_leader_search.id,
                        "username": team.team_leader_search.username
                    } if team.team_leader_search else None,
                    "team_leader_development": {
                        "id": team.team_leader_development.id,
                        "username": team.team_leader_development.username
                    } if team.team_leader_development else None,
                    "team_leader_creative": {
                        "id": team.team_leader_creative.id,
                        "username": team.team_leader_creative.username
                    } if team.team_leader_creative else None,
                    "subteams": [
                        {
                            "id": member.id,
                            "username": member.username,
                            "subteam": member.subteam
                        } for member in team.members.all()
                    ]
                }
                for team in teams
            ]
            return Response({"teams": team_data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Permission denied", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)

# Fetch Account Managers Used in  Create Task  Functionality
class FetchAccountManagersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        account_managers = CustomUser.objects.filter(usertype='Admin')
        account_manager_data = [{"id": user.id, "username": user.username} for user in account_managers]
        return Response({"account_managers": account_manager_data}, status=status.HTTP_200_OK)

# Fetch Subteams and Members for TeamLeader  Used in  Create Task  Functionality
class FetchSubteamsAndMembersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        project_id = request.query_params.get('project_id')
        team_leader_id = request.query_params.get('team_leader')
        if user.usertype == 'TeamLeader':
            subteams = []
            members = []
            try:
                project = Project.objects.get(id=project_id)
                team_leader = CustomUser.objects.get(id=team_leader_id)

                # Filter subteams based on the project assignment
                if team_leader.team == 'Search':
                    subteams = ['SEO', 'SMO', 'SEM']
                elif team_leader.team == 'Creative':
                    subteams = ['Design', 'Content Writing']
                elif team_leader.team == 'Development':
                    subteams = ['Python Development', 'Web Development']

                # Filter members based on the selected subteams and project
                team_members = CustomUser.objects.filter(
                    team=team_leader.team,
                    subteam__in=subteams,
                    teams__projects=project
                )
                members = [{"id": member.id, "username": member.username, "subteam": member.subteam} for member in team_members]

                # Filter subteams to include only those assigned to the project
                assigned_subteams = set(member.subteam for member in team_members)
                subteams = [subteam for subteam in subteams if subteam in assigned_subteams]

                return Response({"subteams": subteams, "members": members}, status=status.HTTP_200_OK)
            except Project.DoesNotExist:
                return Response({"message": "Project not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
            except CustomUser.DoesNotExist:
                return Response({"message": "Team leader not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
            except Exception as e:
                return Response({"message": "Failed to fetch subteams and members", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            print("Error")
            return Response({"message": "Permission denied", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)

"""
                                Admin Based Project View
"""
# Fetch Projects Created by Admin and Assigned to Admin
class FetchAdminProjectsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.usertype == 'Admin':
            created_projects = Project.objects.filter(created_by=user)
            assigned_projects = Project.objects.filter(team__account_manager=user)
            projects = created_projects | assigned_projects
            project_data = [
                {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "status": project.status,
                    "start_date": project.start_date,
                    "deadline": project.deadline,
                }
                for project in projects
            ]
            return Response({"projects": project_data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Permission denied", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)

# Fetch Assigned Projects for Admin, TeamLeader and User
class FetchAssignedProjectsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.usertype in ['Admin', 'TeamLeader', 'User']:
            if user.usertype == 'Admin':
                created_projects = Project.objects.filter(created_by=user)
                assigned_projects = Project.objects.filter(team__account_manager=user)
                projects = created_projects | assigned_projects
            elif user.usertype == 'TeamLeader':
                teams = Team.objects.filter(
                    team_leader_search=user) | Team.objects.filter(
                    team_leader_development=user) | Team.objects.filter(
                    team_leader_creative=user)
                projects = Project.objects.filter(team__in=teams)
            elif user.usertype == 'User':
                teams = Team.objects.filter(members=user)
                projects = Project.objects.filter(team__in=teams)

            project_data = [
                {
                    "id": project.id,
                    "name": project.name,
                    "description": project.description,
                    "status": project.status,
                    "start_date": project.start_date,
                    "deadline": project.deadline,
                    "created_by": project.created_by.username,
                    "account_manager": {
                        "id": project.team.account_manager.id,
                        "username": project.team.account_manager.username
                    } if project.team and project.team.account_manager else None,
                    "team": {
                        "id": project.team.id,
                        "name": project.team.name,
                        "team_leader_search": {
                            "id": project.team.team_leader_search.id,
                            "username": project.team.team_leader_search.username
                        } if project.team.team_leader_search else None,
                        "team_leader_creative": {
                            "id": project.team.team_leader_creative.id,
                            "username": project.team.team_leader_creative.username
                        } if project.team.team_leader_creative else None,
                        "team_leader_development": {
                            "id": project.team.team_leader_development.id,
                            "username": project.team.team_leader_development.username
                        } if project.team.team_leader_development else None,
                        "subteams": [
                            {
                                "id": member.id,
                                "username": member.username,
                                "subteam": member.subteam
                            } for member in project.team.members.all()
                        ] if project.team else []
                    } if project.team else None,
                }
                for project in projects
            ]
            return Response({"projects": project_data}, status=status.HTTP_200_OK)
        else:
            return Response({"message": "Permission denied", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)

# Fetch Team Leaders for a Specific Project and Team
class FetchProjectTeamLeadersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id, *args, **kwargs):
        team = request.query_params.get('team')
        if team not in ['Search', 'Creative', 'Development']:
            return Response({"message": "Invalid team"}, status=status.HTTP_400_BAD_REQUEST)

        try:
            project = Project.objects.get(id=project_id)
            team_leaders = []
            if team == 'Search' and project.team and project.team.team_leader_search:
                team_leaders.append(project.team.team_leader_search)
            elif team == 'Creative' and project.team and project.team.team_leader_creative:
                team_leaders.append(project.team.team_leader_creative)
            elif team == 'Development' and project.team and project.team.team_leader_development:
                team_leaders.append(project.team.team_leader_development)

            team_leader_data = [
                {"id": leader.id, "username": leader.username}
                for leader in team_leaders
            ]
            return Response({"team_leaders": team_leader_data}, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response({"message": "Project not found"}, status=status.HTTP_404_NOT_FOUND)

"""
                                    Waste Code
"""

# Fetch Team Leaders for a Specific Team
class FetchTeamLeadersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        team = request.query_params.get('team')
        if team not in ['Search', 'Creative', 'Development']:
            return Response({"message": "Invalid team"}, status=status.HTTP_400_BAD_REQUEST)

        team_leaders = CustomUser.objects.filter(
            usertype='TeamLeader',
            team=team
        )
        team_leader_data = [
            {"id": leader.id, "username": leader.username}
            for leader in team_leaders
        ]
        return Response({"team_leaders": team_leader_data}, status=status.HTTP_200_OK)

# Fetch Tasks to Task List based on the Project
class FetchProjectTasksView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, project_id, *args, **kwargs):
        try:
            project = Project.objects.get(id=project_id)
            user = request.user
            tasks = project.tasks.filter(created_by=user)
            task_data = [
                {
                    "id": task.id,
                    "title": task.title,
                    "description": task.description,
                    "status": task.status,
                    "priority": task.priority,
                    "start_date": task.start_date,
                    "end_date": task.end_date,
                    "project": task.project.id,
                    "assigned_to": {
                        "id": task.assigned_to.id,
                        "username": task.assigned_to.username
                    } if task.assigned_to else None,
                    "assigned_by": {
                        "id": task.assigned_by.id,
                        "username": task.assigned_by.username
                    } if task.assigned_by else None,
                }
                for task in tasks
            ]
            print(task_data)
            return Response({"tasks": task_data}, status=status.HTTP_200_OK)
        except Project.DoesNotExist:
            return Response({"message": "Project not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

"""
                                Task View
"""

# Create Task
class CreateTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        title = data.get('title')
        description = data.get('description')
        project_id = data.get('project')
        task_status = data.get('status', 'To Do')
        priority = data.get('priority', 'Medium')
        start_date = data.get('start_date')
        end_date = data.get('end_date')
        created_by = request.user  # The logged-in user
        assigned_to_id = data.get('assigned_to')

        try:
            project = Project.objects.get(id=project_id)
            assigned_to = CustomUser.objects.get(id=assigned_to_id) if assigned_to_id else None

            # Validate assignment logic
            if created_by.usertype == 'SuperAdmin' and assigned_to and assigned_to.usertype != 'Admin':
                return Response({"message": "SuperAdmin can only assign tasks to Admins"}, status=status.HTTP_400_BAD_REQUEST)
            if created_by.usertype == 'Admin' and assigned_to and assigned_to.usertype != 'TeamLeader':
                return Response({"message": "Admin can only assign tasks to TeamLeaders"}, status=status.HTTP_400_BAD_REQUEST)
            if created_by.usertype == 'TeamLeader' and assigned_to and assigned_to.usertype != 'User':
                return Response({"message": "TeamLeader can only assign tasks to Users"}, status=status.HTTP_400_BAD_REQUEST)

            task = Task.objects.create(
                title=title,
                description=description,
                project=project,
                status=task_status,
                priority=priority,
                start_date=start_date,
                end_date=end_date,
                created_by=created_by,
            )

            # Assign task based on the creator's role
            if created_by.usertype == 'SuperAdmin':
                task.superadmin_assigned_to = assigned_to
            elif created_by.usertype == 'Admin':
                task.admin_assigned_to = assigned_to
            elif created_by.usertype == 'TeamLeader':
                task.teamleader_assigned_to = assigned_to

            task.save()
            
            if assigned_to and assigned_to.chat_id:
                message = (
                    f"📢 <b>New Task Assigned</b>\n\n"
                    f"🔹 <b>Title:</b> {task.title}\n"
                    f"📝 <b>Description:</b> {task.description}\n"
                    f"📌 <b>Priority:</b> {task.priority}\n"
                    f"📅 <b>Deadline:</b> {task.end_date}\n"
                    f"👤 <b>Assigned By:</b> {created_by.username}"
                )
                send_telegram_message(assigned_to.chat_id, message)
            return Response({"message": "Task created successfully", "task_id": task.id}, status=status.HTTP_201_CREATED)

        except Project.DoesNotExist:
            return Response({"message": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
        except CustomUser.DoesNotExist:
            return Response({"message": "Assigned user not found"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": f"Error: {str(e)}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fetch Tasks in the TaskList
class FetchTasksView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        project_id = request.query_params.get('project_id')

        # Fetch tasks created by the user
        tasks = Task.objects.filter(created_by=user)
        if project_id:
            tasks = tasks.filter(project_id=project_id)

        task_data = [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "start_date": task.start_date,
                "end_date": task.end_date,
                "project": task.project.id,
                "assigned_to": {
                    "id": task.superadmin_assigned_to.id,
                    "username": task.superadmin_assigned_to.username
                } if task.superadmin_assigned_to else {
                    "id": task.admin_assigned_to.id,
                    "username": task.admin_assigned_to.username
                } if task.admin_assigned_to else {
                    "id": task.teamleader_assigned_to.id,
                    "username": task.teamleader_assigned_to.username
                } if task.teamleader_assigned_to else None,
                "created_by": {
                    "id": task.created_by.id,
                    "username": task.created_by.username
                }
            }
            for task in tasks
        ]

        return Response({"tasks": task_data}, status=status.HTTP_200_OK)

# Fetch Task Details For Editing
class FetchTaskDetailsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, task_id, *args, **kwargs):
        try:
            task = Task.objects.get(id=task_id)

            task_data = {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "start_date": task.start_date,
                "end_date": task.end_date,
                "project": task.project.id,
                "assigned_to": {
                    "superadmin": {
                        "id": task.superadmin_assigned_to.id,
                        "username": task.superadmin_assigned_to.username
                    } if task.superadmin_assigned_to else None,
                    "admin": {
                        "id": task.admin_assigned_to.id,
                        "username": task.admin_assigned_to.username
                    } if task.admin_assigned_to else None,
                    "teamleader": {
                        "id": task.teamleader_assigned_to.id,
                        "username": task.teamleader_assigned_to.username
                    } if task.teamleader_assigned_to else None,
                },
                "created_by": {
                    "id": task.created_by.id,
                    "username": task.created_by.username
                }
            }
            
            return Response(task_data, status=status.HTTP_200_OK)
        
        except Task.DoesNotExist:
            return Response({"message": "Task not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

# Saving Data After Editing Task
class EditTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, task_id, *args, **kwargs):
        data = request.data
        try:
            task = Task.objects.get(id=task_id)
            task.title = data.get('title', task.title)
            task.description = data.get('description', task.description)
            task.status = data.get('status', task.status)
            task.priority = data.get('priority', task.priority)
            task.start_date = data.get('start_date', task.start_date)
            task.end_date = data.get('end_date', task.end_date)
            task.save()

            return Response({
                "message": "Task updated successfully",
                "status": "success",
                "task_id": task.id,
            }, status=status.HTTP_200_OK)
        except Task.DoesNotExist:
            return Response({"message": "Task not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to update task", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fetch Tasks Assigned to the Logged-in User
class FetchAssignedTasksView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        project_id = request.query_params.get('project_id')

        tasks = Task.objects.filter(
            Q(superadmin_assigned_to=user) |
            Q(admin_assigned_to=user) |
            Q(teamleader_assigned_to=user)
        )

        if project_id:
            tasks = tasks.filter(project_id=project_id)

        task_data = [
            {
                "id": task.id,
                "title": task.title,
                "description": task.description,
                "status": task.status,
                "priority": task.priority,
                "start_date": task.start_date,
                "end_date": task.end_date,
                "project": task.project.id,
                "assigned_to": {
                    "superadmin": {
                        "id": task.superadmin_assigned_to.id,
                        "username": task.superadmin_assigned_to.username
                    } if task.superadmin_assigned_to else None,
                    "admin": {
                        "id": task.admin_assigned_to.id,
                        "username": task.admin_assigned_to.username
                    } if task.admin_assigned_to else None,
                    "teamleader": {
                        "id": task.teamleader_assigned_to.id,
                        "username": task.teamleader_assigned_to.username
                    } if task.teamleader_assigned_to else None,
                },
                "created_by": {
                    "id": task.created_by.id,
                    "username": task.created_by.username
                }
            }
            for task in tasks
        ]

        return Response({"tasks": task_data}, status=status.HTTP_200_OK)

# Delete Task
class DeleteTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, task_id, *args, **kwargs):
        try:
            task = Task.objects.get(id=task_id)
            task.delete()
            return Response({"message": "Task deleted successfully", "status": "success"}, status=status.HTTP_200_OK)
        except Task.DoesNotExist:
            return Response({"message": "Task not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": "Failed to delete task", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Assign Task to a User
class AssignTaskView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, task_id, *args, **kwargs):
        try:
            task = Task.objects.get(id=task_id)
            assigned_to_id = request.data.get("assigned_to")
            assigned_to = CustomUser.objects.get(id=assigned_to_id)


            if request.user.usertype == "Admin":
                if assigned_to.usertype != "TeamLeader":
                    return Response({"message": "Admin can only assign tasks to TeamLeaders", "status": "failure"},
                                    status=status.HTTP_400_BAD_REQUEST)
                task.admin_assigned_to = assigned_to  # Assigning to TeamLeader

            elif request.user.usertype == "TeamLeader":
                if assigned_to.usertype != "User":
                    return Response({"message": "TeamLeader can only assign tasks to Users", "status": "failure"},
                                    status=status.HTTP_400_BAD_REQUEST)
                task.teamleader_assigned_to = assigned_to  # Assigning to  User

            else:
                return Response({"message": "Invalid role for task assignment", "status": "failure"},
                                status=status.HTTP_403_FORBIDDEN)

            task.save()

            assigned_by_text = request.user.username if request.user else "N/A"
            # Create notification for the assigned user
            if assigned_to and assigned_to.chat_id:
                message = (
                    f"📢 <b>New Task Assigned</b>\n\n"
                    f"🔹 <b>Title:</b> {task.title}\n"
                    f"📝 <b>Description:</b> {task.description}\n"
                    f"📌 <b>Priority:</b> {task.priority}\n"
                    f"📅 <b>Deadline:</b> <span style='color:red;'>{task.end_date}</span>\n"
                    f"👤 <b>Assigned By:</b> {assigned_by_text}"
                )
                send_telegram_message(assigned_to.chat_id, message)
            
            Notification.objects.create(
                user=assigned_to,
                message=f"New Task Assigned: {task.title} with priority {task.priority}"
            )

            return Response({"message": "Task assigned successfully", "status": "success"}, status=status.HTTP_200_OK)

        except Task.DoesNotExist:
            return Response({"message": "Task not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except CustomUser.DoesNotExist:
            return Response({"message": "Assigned user not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"message": f"Failed to assign task: {str(e)}", "status": "failure"},
                            status=status.HTTP_500_INTERNAL_SERVER_ERROR)


"""
                                Timesheet View

"""
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

# Fetch Users for Submitted To Dropdown
class FetchSubmittedToUsersView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        if user.usertype == 'User':
            users = CustomUser.objects.filter(usertype='TeamLeader', team=user.team)
        elif user.usertype == 'TeamLeader':
            users = CustomUser.objects.filter(usertype='Admin')
        elif user.usertype == 'Admin':
            users = CustomUser.objects.filter(usertype='SuperAdmin')
        else:
            users = CustomUser.objects.none()

        user_data = [{"id": user.id, "username": user.username} for user in users]
        return Response({"users": user_data}, status=status.HTTP_200_OK)

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
                
                Notification.objects.create(
                    user=submitted_to_user,
                    message=f"Timesheet table created by {request.user.username} has been sent for review."
                )
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
                
                # App Notifications
                Notification.objects.create(
                    user=timesheet_table.created_by,
                    message=f"Timesheet table created by {timesheet_table.created_by.username} has been approved by {request.user.username}."
                )
            elif action == 'reject':
                timesheet_table.status = 'Rejected by Team Leader'
                timesheet_table.comments = feedback  # Save comments on rejection
                timesheet_table.save()
                
                # Telegram Notifications
                message = f"❌ Your timesheet table has been rejected by {request.user.username}. \n\n📝 Feedback: {feedback}"
                send_telegram_message(timesheet_table.created_by.chat_id,message)
                
                #App Notifications
                Notification.objects.create(
                    user=timesheet_table.created_by,
                    message=f"Timesheet table created by {timesheet_table.created_by.username} has been rejected by {request.user.username}: {feedback}"
                )
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
                
                Notification.objects.create(
                    user=timesheet_table.created_by,
                    message=f"Timesheet table created by {timesheet_table.created_by.username} has been approved by {request.user.username}."
                )
            elif action == 'reject':
                timesheet_table.status = 'Rejected by Admin'
                timesheet_table.comments = feedback  # Save comments on rejection
                timesheet_table.save()
                # Send one notification to the user who created the timesheet table
                message = f"❌ Your timesheet table has been rejected by {request.user.username}. \n\n📝 Feedback: {feedback}"
                send_telegram_message(timesheet_table.created_by.chat_id,message)
                
                Notification.objects.create(
                    user=timesheet_table.created_by,
                    message=f"Timesheet table created by {timesheet_table.created_by.username} has been rejected by {request.user.username}: {feedback}"
                )
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

# Fetch a specific user's details
class FetchUserDetailsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, user_id, *args, **kwargs):
        try:
            user = CustomUser.objects.get(id=user_id)
            user_data = {
                "id": user.id,
                "username": user.username,
                "first_name": user.first_name,
                "last_name": user.last_name,
                "usertype": user.usertype,
                "email": user.email,
                "team": user.team,
                "subteam": user.subteam,
            }
            return Response(user_data, status=status.HTTP_200_OK)
        except CustomUser.DoesNotExist:
            return Response({"message": "User not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

# Fetch Team for the Logged-in User
class FetchUserTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        teams = Team.objects.filter(members=user)  # Fetch all teams the user is part of

        if not teams.exists():
            return Response({"message": "No teams found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

        team_data = [
            {
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "account_manager": {
                    "id": team.account_manager.id,
                    "username": team.account_manager.username
                },
                "team_leader_search": {
                    "id": team.team_leader_search.id,
                    "username": team.team_leader_search.username
                } if team.team_leader_search else None,
                "team_leader_development": {
                    "id": team.team_leader_development.id,
                    "username": team.team_leader_development.username
                } if team.team_leader_development else None,
                "team_leader_creative": {
                    "id": team.team_leader_creative.id,
                    "username": team.team_leader_creative.username
                } if team.team_leader_creative else None,
                "subteams": [
                    {
                        "id": member.id,
                        "username": member.username,
                        "subteam": member.subteam
                    } for member in team.members.all()
                ],
                "created_by": {
                    "id": team.created_by.id,
                    "username": team.created_by.username
                }
            }
            for team in teams
        ]

        return Response({"teams": team_data}, status=status.HTTP_200_OK)

# Fetch Working Hours Data
class FetchWorkingHoursView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        usertype = user.usertype
        user_id = user.id

        if usertype == 'SuperAdmin' or usertype == 'Admin':
            users = CustomUser.objects.all()
        elif usertype == 'TeamLeader':
            users = CustomUser.objects.filter(team=user.team)
        elif usertype == 'User':
            users = CustomUser.objects.filter(id=user.id)
        else:
            users = CustomUser.objects.none()

        working_hours = Timesheet.objects.values('created_by__id').annotate(hours=Sum('hours'))
        working_hours_dict = {item['created_by__id']: item['hours'] for item in working_hours}

        working_hours_data = [
            {"name": user.username, "hours": working_hours_dict.get(user.id, 0)}
            for user in users
        ]

        return Response({"working_hours": working_hours_data}, status=status.HTTP_200_OK)

class RequestPasswordResetCodeView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        username_or_email = request.data.get("username_or_email")
        try:
            user = CustomUser.objects.get(username=username_or_email)
        except CustomUser.DoesNotExist:
            try:
                user = CustomUser.objects.get(email=username_or_email)
            except CustomUser.DoesNotExist:
                return Response({"message": "User not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

        # Generate a 6-digit verification code
        verification_code = str(random.randint(100000, 999999))

        # Send the verification code to the user's Telegram
        message = f"Your password reset verification code is: {verification_code}"
        send_telegram_message(user.chat_id, message)

        return Response({"code": verification_code, "message": "Verification code sent", "status": "success"}, status=status.HTTP_200_OK)
