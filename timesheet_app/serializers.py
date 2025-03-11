from rest_framework import serializers
from .models import CustomUser, Timesheet, TimesheetTable, Project


# CustomUserSerializer is used to serialize the CustomUser model
class CustomUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'username', 'email', 'usertype', 'team', 'subteam', 'chat_id']

# TimesheetSerializer is used to serialize the Timesheet model
class TimesheetSerializer(serializers.ModelSerializer):
    submitted_to = serializers.SlugRelatedField(slug_field='username', queryset=CustomUser.objects.all())
    created_by = serializers.SlugRelatedField(slug_field='username', queryset=CustomUser.objects.all())
    project = serializers.SlugRelatedField(slug_field='name', queryset=Project.objects.all(), allow_null=True, required=False)

    class Meta:
        model = Timesheet
        fields = ['id', 'date', 'task', 'submitted_to', 'status', 'description', 'hours', 'created_by', 'project']

# TimesheetTableSerializer is used to serialize the TimesheetTable model
class TimesheetTableSerializer(serializers.ModelSerializer):
    timesheets = TimesheetSerializer(many=True)
    created_by = serializers.SlugRelatedField(slug_field='username', queryset=CustomUser.objects.all(), required=False)

    class Meta:
        model = TimesheetTable
        fields = ['id', 'created_by', 'timesheets', 'created_at', 'status']

    def create(self, validated_data):
        timesheets_data = validated_data.pop('timesheets')
        created_by = validated_data.pop('created_by', None)
        timesheet_table = TimesheetTable.objects.create(created_by=created_by, **validated_data)
        for timesheet_data in timesheets_data:
            timesheet = Timesheet.objects.create(**timesheet_data)
            timesheet_table.timesheets.add(timesheet)
        return timesheet_table

    def validate(self, data):
        return data

    def is_valid(self, raise_exception=False):
        valid = super().is_valid(raise_exception=raise_exception)
        if not valid:
            print(self.errors)
        return valid

    def delete(self, instance):
        instance.timesheets.all().delete()  # Delete related timesheets
        instance.delete()
