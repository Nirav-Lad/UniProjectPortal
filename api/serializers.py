import datetime
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import Batch, UserMaster,StudentDetails,GroupFormation, GroupStudents, Idea
from django.contrib.auth.hashers import make_password


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password_or_otp = serializers.CharField(write_only=True) 

    def validate(self, data):
        email = data.get("email")
        password_or_otp = data.get("password_or_otp")

        try:
            user = UserMaster.objects.get(email=email)
        except UserMaster.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password")

        if not user.is_active:
            raise serializers.ValidationError("Account is disabled")

        # Detect First Login using `last_login`
        if user.usertype == "Student" and user.last_login is None:
            if password_or_otp == user.otp:  
                return {
                    "user": user,
                    "require_password_change": True,
                    "message": "OTP verified. Please set your password."
                }
            else:
                raise serializers.ValidationError("Invalid OTP")

        # If password is set, authenticate using password
        user = authenticate(email=email, password=password_or_otp)
        if user:
            return {
                "user": user,
                "require_password_change": False
            }

        raise serializers.ValidationError("Invalid email or password")

    def get_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        } 
# ------------------------------------------------------------
class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        user = self.context["request"].user

        if user.last_login is not None:
            raise serializers.ValidationError("Password has already been set.")

        return data

    def save(self, **kwargs):
        user = self.context["request"].user
        user.password = make_password(self.validated_data["password"], hasher="argon2")  
        user.last_login = datetime.datetime.now()
        user.save()
        return user
# ------------------------------------------------------------
class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['batch_id', 'batch_name', 'created_by', 'created_on']
        read_only_fields = ['batch_id', 'created_by', 'created_on']

    def to_representation(self, instance):
        request = self.context.get("request")
        if request and request.method == "GET":
            return {
                "batch_name": instance.batch_name
            }
        return super().to_representation(instance)

# -------------------------------------------------------------
class StudentDetailsSerializer(serializers.ModelSerializer):
    user = serializers.PrimaryKeyRelatedField(read_only=True)  
    class Meta:
        model = StudentDetails
        fields = ['section', 'mobile_no', 'user']  
# --------------------------------------------------------------
class StudentInBatchSerializer(serializers.ModelSerializer):
    user_email = serializers.EmailField(source="user.email", read_only=True)  
    class Meta:
        model = StudentDetails
        fields = ["enrollment_id", "name", "user_email"]
# --------------------------------------------------------------
class StudentDetailsRoleBasedSerializer(serializers.ModelSerializer):
    email = serializers.EmailField(source="user.email", read_only=True)
    batch_name = serializers.CharField(source="batch.batch_name", read_only=True)

    class Meta:
        model = StudentDetails
        fields = ["enrollment_id", "name", "email", "section", "mobile_no", "batch_name"]

    def to_representation(self, instance):
    
        data = super().to_representation(instance)
        user = self.context["request"].user

        if user.usertype == "Admin":
            # Admins should not see `section` and `mobile_no`
            data.pop("section", None)
            data.pop("mobile_no", None)

        return data

# --------------------------------------------------------------
class GroupSerializer(serializers.ModelSerializer):
    members = serializers.SerializerMethodField()
    member_count = serializers.SerializerMethodField()
    vacancies = serializers.SerializerMethodField()

    class Meta:
        model = GroupFormation
        fields = ["id", "status", "members", "member_count", "vacancies"]

    def get_members(self, obj):
        students = GroupStudents.objects.filter(group=obj).select_related("student_batch_link__enrollment")
        return [
            {
                "enrollment_id": student.student_batch_link.enrollment.enrollment_id,
                "name": student.student_batch_link.enrollment.name,
            }
            for student in students
        ]

    def get_member_count(self, obj):
        return GroupStudents.objects.filter(group=obj).count()

    def get_vacancies(self, obj):
        return 4 - self.get_member_count(obj)
    
# --------------------------------------------------------------
class IdeaSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Idea
        fields = ['title', 'broad_area', 'objective', 'originality_innovativeness', 
                  'key_activities', 'data_sources', 'technology_usage', 'scalability',
                  'social_impact', 'potent_users']

    def validate(self, data):
        user = self.context['request'].user
        group = GroupFormation.objects.filter(group_students__student_batch_link__enrollment__user=user).first()

        if not group:
            raise serializers.ValidationError("You are not part of any group.")

        existing_ideas_count = sum(1 for idea in [group.idea_1, group.idea_2, group.idea_3] if idea is not None)
        if existing_ideas_count >= 3:
            raise serializers.ValidationError("Your group has already submitted 3 ideas. No more ideas can be submitted.")

        return data

    def create(self, validated_data):
        return Idea.objects.create(**validated_data) 
        return idea