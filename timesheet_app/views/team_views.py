from rest_framework.views import APIView
from rest_framework import permissions, status
from timesheet_app.models import CustomUser, Team, Project
from rest_framework.response import Response
from timesheet_app.utils import send_telegram_message
from django.db.models import Q
from collections import defaultdict
from django.shortcuts import get_object_or_404



# Create Team
class CreateTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        data = request.data
        name = data.get('name')
        description = data.get('description')
        account_manager_ids = data.get('account_manager_ids', [])  
        team_leader_search_id = data.get('team_leader_search')
        team_leader_development_id = data.get('team_leader_development')
        team_leader_creative_id = data.get('team_leader_creative')
        team = data.get('team')
        subteam = data.get('subteam')
        member_ids = data.get('member_ids', [])
        project_id = data.get('project_id')  
        created_by = request.user

        try:
            account_managers = CustomUser.objects.filter(id__in=account_manager_ids)
            if not account_managers.exists():
                return Response({"message": "Invalid Account Manager(s)", "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)

            team_leader_search = CustomUser.objects.get(id=team_leader_search_id) if team_leader_search_id else None
            team_leader_development = CustomUser.objects.get(id=team_leader_development_id) if team_leader_development_id else None
            team_leader_creative = CustomUser.objects.get(id=team_leader_creative_id) if team_leader_creative_id else None
            project = Project.objects.filter(id=project_id).first()
            if not project:
                return Response({"message": "Invalid Project ID", "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)

            # Create the team
            team_instance = Team.objects.create(
                name=name,
                description=description,
                team_leader_search=team_leader_search,
                team_leader_development=team_leader_development,
                team_leader_creative=team_leader_creative,
                team=team,
                subteam=subteam,
                created_by=created_by,
            )
            team_instance.account_managers.set(account_managers)
            team_instance.members.set(member_ids)
            team_instance.projects.set([project]) 
            team_instance.save()

            if project:
                team_members = list(team_instance.members.all())
                users_to_notify = set(team_members + list(account_managers))
                
                if team_leader_search:
                    users_to_notify.add(team_leader_search)
                if team_leader_development:
                    users_to_notify.add(team_leader_development)
                if team_leader_creative:
                    users_to_notify.add(team_leader_creative)

                for user in users_to_notify:
                    message = f"You have been added to the project: <b>{project.name}</b> as part of team <b>{team_instance.name}</b>."
                    send_telegram_message(user.chat_id, message)

            return Response({"message": "Team created successfully", "status": "success"}, status=status.HTTP_201_CREATED)
        except CustomUser.DoesNotExist as e:
            return Response({"message": str(e), "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)
        except Project.DoesNotExist as e:
            return Response({"message": str(e), "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            return Response({"message": str(e), "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Fetch Teams
class FetchTeamsView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user
        
        
        if user.usertype == "SuperAdmin":
            teams = Team.objects.all()
        elif user.usertype in ["Admin", "TeamLeader","User"]:
            teams = Team.objects.filter(
                Q(account_managers=user) |
                Q(team_leader_search=user) |
                Q(team_leader_development=user) |
                Q(team_leader_creative=user) |
                Q(members=user)
                
            ).distinct()
        else:
            return Response({"message": "Permission denied", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)

        if not teams.exists():
            return Response({"message": "No teams found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

        team_data = []
        for team in teams:
            subteam_dict = defaultdict(list)
            all_members = set()

            for member in team.members.all():
                subteam_dict[member.subteam or "Uncategorized"].append({
                    "id": member.id,
                    "username": member.username
                })
                all_members.add(member.id)

            account_managers = [
                {"id": manager.id, "username": manager.username}
                for manager in team.account_managers.all()
            ]

            all_members.update(manager["id"] for manager in account_managers)

            # Handling team leaders
            def get_team_leader(leader):
                return {"id": leader.id, "username": leader.username} if leader else None

            team_leader_search = get_team_leader(team.team_leader_search)
            team_leader_development = get_team_leader(team.team_leader_development)
            team_leader_creative = get_team_leader(team.team_leader_creative)

            for leader in [team_leader_search, team_leader_development, team_leader_creative]:
                if leader:
                    all_members.add(leader["id"])

            total_members_count = len(all_members)
            
            projects = [
                {"id": project.id, "name": project.name}
                for project in team.projects.all()
            ]


            team_data.append({
                "id": team.id,
                "name": team.name,
                "description": team.description,
                "account_managers": account_managers,
                "team_leader_search": team_leader_search,
                "team_leader_development": team_leader_development,
                "team_leader_creative": team_leader_creative,
                "subteams": [
                    {"subteam": subteam, "members": members}
                    for subteam, members in subteam_dict.items()
                ],
                "created_by": {
                    "id": team.created_by.id,
                    "username": team.created_by.username
                } if team.created_by else None,
                "projects": projects,
                "total_members": total_members_count
            })

        return Response({"teams": team_data}, status=status.HTTP_200_OK)

class GetAssignedTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        if user.usertype != 'TeamLeader':
            return Response({"message": "User is not a Team Leader", "status": "failure"}, status=status.HTTP_403_FORBIDDEN)

        try:
           
            team = Team.objects.filter(
                Q(team_leader_search=user) |
                Q(team_leader_development=user) |
                Q(team_leader_creative=user)
            ).first()

            if not team:
                return Response({"message": "No assigned team found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

            # Determine which subteam the leader manages
            if team.team_leader_search == user:
                team_type = "Search"
            elif team.team_leader_development == user:
                team_type = "Development"
            elif team.team_leader_creative == user:
                team_type = "Creative"
            else:
                team_type = None

            if not team_type:
                return Response({"message": "User is not assigned to a specific subteam", "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)

            
            assigned_team_members = team.members.filter(subteam=team_type).values("id", "username")

            return Response({
                "team": {
                    "team_type": team_type,
                    "members": list(assigned_team_members)  
                },
                "status": "success"
            }, status=status.HTTP_200_OK)

        except Exception as e:
            return Response({"message": str(e), "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Edit Team 
class EditTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def put(self, request, team_id, *args, **kwargs):
        data = request.data
        try:
            team = get_object_or_404(Team, id=team_id)

            old_account_managers = set(team.account_managers.all())
            old_team_leaders = {
                "search": team.team_leader_search,
                "development": team.team_leader_development,
                "creative": team.team_leader_creative,
            }
            old_members = set(team.members.all())

            team.name = data.get("name", team.name)
            team.description = data.get("description", team.description)

            account_manager_ids = [int(id) for id in data.get("account_manager_ids", []) if id]
            new_account_managers = set(CustomUser.objects.filter(id__in=account_manager_ids))
            team.account_managers.set(new_account_managers)

            def get_user_by_id(user_id):
               user_id = user_id if user_id and str(user_id).isdigit() else None
               return CustomUser.objects.filter(id=user_id).first() if user_id else None


            new_team_leaders = {
                "search": get_user_by_id(data.get("team_leader_search")),
                "development": get_user_by_id(data.get("team_leader_development")),
                "creative": get_user_by_id(data.get("team_leader_creative")),
            }
            team.team_leader_search = new_team_leaders["search"]
            team.team_leader_development = new_team_leaders["development"]
            team.team_leader_creative = new_team_leaders["creative"]

            team.team = data.get("team", team.team)
            team.subteam = data.get("subteam", team.subteam)

            member_ids = [int(id) for id in data.get("member_ids", []) if id]
            new_members = set(CustomUser.objects.filter(id__in=member_ids))
            team.members.set(new_members)

            team.save()

            added_members = new_members - old_members
            removed_members = old_members - new_members
            added_account_managers = new_account_managers - old_account_managers
            removed_account_managers = old_account_managers - new_account_managers

            added_team_leaders = {
                role: new_team_leaders[role]
                for role in old_team_leaders
                if new_team_leaders[role] and new_team_leaders[role] != old_team_leaders[role]
            }
            removed_team_leaders = {
                role: old_team_leaders[role]
                for role in old_team_leaders
                if old_team_leaders[role] and old_team_leaders[role] != new_team_leaders[role]
            }

            if team.projects.exists():
                for project in team.projects.all():
                    for user in added_members:
                        send_telegram_message(user.chat_id, f"You have been added to the project: <b>{project.name}</b> as part of team <b>{team.name}</b>.")
                    for user in removed_members:
                        send_telegram_message(user.chat_id, f"You have been removed from the project: <b>{project.name}</b> from team <b>{team.name}</b>.")
                    for user in added_account_managers:
                        send_telegram_message(user.chat_id, f"You have been assigned as an Account Manager for project: <b>{project.name}</b> in team <b>{team.name}</b>.")
                    for user in removed_account_managers:
                        send_telegram_message(user.chat_id, f"You have been removed as an Account Manager from project: <b>{project.name}</b> in team <b>{team.name}</b>.")
                    for role, user in added_team_leaders.items():
                        send_telegram_message(user.chat_id, f"You have been assigned as <b>{role.capitalize()} Team Leader</b> for project: <b>{project.name}</b> in team <b>{team.name}</b>.")
                    for role, user in removed_team_leaders.items():
                        send_telegram_message(user.chat_id, f"You have been removed as <b>{role.capitalize()} Team Leader</b> from project: <b>{project.name}</b> in team <b>{team.name}</b>.")

            return Response({"message": "Team updated successfully", "status": "success", "team_id": team.id}, status=status.HTTP_200_OK)

        except ValueError as ve:
            return Response({"message": "Invalid ID provided.", "status": "failure"}, status=status.HTTP_400_BAD_REQUEST)

        except Team.DoesNotExist:
            return Response({"message": "Team not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"message": str(e), "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

# Delete Team   
class DeleteTeamView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def delete(self, request, team_id, *args, **kwargs):
        try:
    
            team = Team.objects.get(id=team_id)
            projects_assigned = team.projects.all() 
            users_to_notify = list(team.members.all()) + list(team.account_managers.all())

            if team.team_leader_search:
                users_to_notify.append(team.team_leader_search)
            if team.team_leader_development:
                users_to_notify.append(team.team_leader_development)
            if team.team_leader_creative:
                users_to_notify.append(team.team_leader_creative)

            # Notify users if the team is associated with any projects
            if projects_assigned.exists():
                for project in projects_assigned:
                    for user in users_to_notify:
                        try:
                            message = f"The team <b>{team.name}</b> has been deleted. You have been removed from the project: <b>{project.name}</b>"
                            send_telegram_message(user.chat_id, message)
                        except Exception as notify_error:
                            print(f"Failed to send notification to {user.username}: {notify_error}")
                            
            team.projects.clear()
            # Delete the team
            team.delete()

            return Response({"message": "Team deleted successfully", "status": "success"}, status=status.HTTP_200_OK)

        except Team.DoesNotExist:
            return Response({"message": "Team not found", "status": "failure"}, status=status.HTTP_404_NOT_FOUND)

        except Exception as e:
            return Response({"message": f"Failed to delete team: {str(e)}", "status": "failure"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

"""
                            unused
"""

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

