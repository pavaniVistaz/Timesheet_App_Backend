from django.contrib import admin
from .models import CustomUser, Admin, TeamLeader, User, Team, Project, Task, Timesheet, TimesheetTable

admin.site.register(CustomUser)
admin.site.register(Admin)
admin.site.register(TeamLeader)
admin.site.register(User)
admin.site.register(Team)
admin.site.register(Project)
admin.site.register(Task)
admin.site.register(Timesheet)
admin.site.register(TimesheetTable)
