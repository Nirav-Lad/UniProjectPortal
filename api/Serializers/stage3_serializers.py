from rest_framework import serializers
from ..models import LogMaster, GroupFormation,UserMaster,GuideGroup,Guide



class MeetingLogCreateSerializer(serializers.ModelSerializer):
    group_id = serializers.IntegerField(write_only=True)

    class Meta:
        model = LogMaster
        fields = [
            "group_id",
            "changes_suggested_prev",
            "changes_done_prev",
            "suggested_changes_next",
            "guide_remarks",
            "approval_status",
            "created_at",
        ]

    def validate_group_id(self, value):
        """Check if the given group exists"""
        if not GroupFormation.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Invalid group_id. Group does not exist.")
        return value
    
class MeetingLogUpdateSerializer(serializers.ModelSerializer):
    log_id = serializers.IntegerField(write_only=True)
    guide_id = serializers.IntegerField(write_only=True)
    approve_status = serializers.BooleanField(write_only=True)

    class Meta:
        model = LogMaster
        fields = [
            "log_id",
            "approve_status",
            "guide_id",
            "changes_suggested_prev",
            "changes_done_prev",
            "suggested_changes_next",
            "guide_remarks",
        ]
    

    def validate_log_id(self, value):
        """Check if the given group exists"""
        if not LogMaster.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Invalid log_id. Meeting Log does not exist.")
        return value
    
    def  validate_approve_status(self, value):
        """Check if approve_status is false and is of Boolean type"""
        if not isinstance(value, bool):
            raise serializers.ValidationError("approve_status must be a boolean value.")
        else:
            if LogMaster.objects.filter(log_id=self.initial_data['log_id'], approval_status=True).exists() and value==True:
                raise serializers.ValidationError("This Meeting Log is already approved.")
        return value
    
    def validate_guide_id(self, value):
        """Check if the given guide exists"""
        if not Guide.objects.filter(pk=value).exists():
            raise serializers.ValidationError("Invalid guide_id. Guide does not exist_1.")
        else:
            group_id = LogMaster.objects.get(pk=self.initial_data['log_id']).group_id_id
            # guide_assigned_id = GuideGroup.objects.filter(group_id=group_id).guide_id
            guide_group = GuideGroup.objects.filter(group_id=group_id).first()

            if not guide_group:
                raise serializers.ValidationError("No guide assigned to this group.")

            guide_assigned_id = guide_group.guide_id_id

            if(guide_assigned_id is None):
                raise serializers.ValidationError("Error in validate_guide_id_Serializer: \n No Guide is assigned to this Group.")
            if guide_assigned_id != value:
                raise serializers.ValidationError("Error in validate_guide_id_Serializer: \n This Approval is Not from the assigned guide.")
        return value
