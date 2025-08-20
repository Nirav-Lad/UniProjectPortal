import datetime
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import (Batch, UserMaster,StudentDetails,GroupFormation, GroupStudents, Idea, 
                     StudentBatch,
                     Guide,GuideExpertise,Expertise,GuideProjectInterest)
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
import random

class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)

    def validate(self, data):
        email = data.get("email")
        password = data.get("password")

        try:
            user = UserMaster.objects.get(email=email)
        except UserMaster.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password")

        if not user.is_active:
            raise serializers.ValidationError("Account is disabled")

        # Detect First Login using `last_login`
        if user.usertype in ["Student", "Guide"] and user.last_login is None:
            if password == user.otp:
                return {
                    "user": user,
                    "require_password_change": True,
                    "message": "OTP verified. Please set your password.",
                    "usertype": user.usertype,
                    "enrollment_id": user.student_details.enrollment_id if hasattr(user, 'student_details') else None,
                    "name": user.student_details.name if user.usertype=="Student" and hasattr(user,'student_details') else None
                }
            else:
                raise serializers.ValidationError("Invalid OTP")

        # If password is set, authenticate using password
        user = authenticate(email=email, password=password)
        if user:
            return {
                "user": user,
                "require_password_change": False,
                "usertype": user.usertype,
                "enrollment_id": user.student_details.enrollment_id if user.usertype == "Student" and hasattr(user, 'student_details') else None,
                "name": user.student_details.name if user.usertype=="Student" and hasattr(user,'student_details') else None
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
class RegisterUserSerializer(serializers.Serializer):
    # common
    email=serializers.EmailField()
    name=serializers.CharField()
    usertype=serializers.ChoiceField(choices=['External','Student','Guide'])

    # Student Only 
    enrollment_id=serializers.IntegerField(required=False,allow_null=True)
    batch_name=serializers.CharField(required=False,allow_blank=True)

    def validate(self, attrs):
        email = attrs.get('email')
        usertype = attrs.get('usertype')
        enrollment_id = attrs.get('enrollment_id')
        batch_name = attrs.get('batch_name')

        if UserMaster.objects.filter(email=email).exists():
            raise serializers.ValidationError({'email':f'Email {email} is already registered.'})

        if usertype=='Student':
            if enrollment_id is None:
                raise serializers.ValidationError({'enrollment_id':f'Enrollment id is required for student.'})
            if not batch_name:
                raise serializers.ValidationError({'batch_name':f'Batch name is required for student.'})
            if StudentDetails.objects.filter(enrollment_id=enrollment_id).exists():
                    raise serializers.ValidationError({'enrollment_id': f'Enrollment ID {enrollment_id} already exists.'})
            try:
                Batch.objects.get(batch_name=batch_name)
            except ObjectDoesNotExist:
                raise serializers.ValidationError({'batch_name': 'Invalid batch name.'})

        return attrs
    
    @transaction.atomic
    def create(self, validated_data):
        created_by_user = self.context['request'].user
        email = validated_data['email']
        name = validated_data['name']
        usertype = validated_data['usertype']

        otp = ''.join(random.choices('0123456789', k=6))

        # Create base user
        user = UserMaster.objects.create(
            email=email,
            otp=otp,
            usertype=usertype,
            status='Active',
            enrollment_id=validated_data.get('enrollment_id') if usertype == 'Student' else None,
            created_by=created_by_user
        )

        if usertype=='Student':
            batch = Batch.objects.get(batch_name=validated_data['batch_name'])

            # Student details table
            student_details = StudentDetails.objects.create(
                enrollment_id=validated_data['enrollment_id'],
                name=name,
                batch=batch,
                user=user
            )

            # Student Batch update details
            StudentBatch.objects.create(
                enrollment=student_details,
                current_batch=batch,
                status='Active'
            )

        elif usertype == 'Guide':
            Guide.objects.create(
                user=user,
                name=name,
                status=validated_data.get('status', 'Active')
            )

        user.name_for_email=validated_data['name']
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
    ideas = serializers.SerializerMethodField()
    finalized_idea = serializers.SerializerMethodField()
    batch_name = serializers.SerializerMethodField()

    class Meta:
        model = GroupFormation
        fields = [
            "id", "status", "is_freeze", "finalized_idea", "members", "ideas", "batch_name"
        ]

    def get_members(self, obj):
        students = GroupStudents.objects.filter(group=obj).select_related(
            "student_batch_link__enrollment__user"
        )

        return [
            {
                "enrollment_id": student.student_batch_link.enrollment.enrollment_id,
                "name": student.student_batch_link.enrollment.name,
                "email": student.student_batch_link.enrollment.user.email,
                "batch_name": student.student_batch_link.current_batch.batch_name
            }
            for student in students
        ]

    def get_ideas(self, obj):
        ideas = [obj.idea_1, obj.idea_2, obj.idea_3]
        return [{"id": idea.id, "title": idea.title} for idea in ideas if idea]

    def get_finalized_idea(self, obj):
        if obj.finalized_idea:
            return {"id": obj.finalized_idea.id, "title": obj.finalized_idea.title}
        return None

    def get_batch_name(self, obj):
        # Fetch batch name from one of the group members
        student = obj.group_students.first()
        return student.student_batch_link.current_batch.batch_name if student else None
      
# --------------------------------------------------------------
class IdeaSubmissionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Idea
        fields = ['title', 'broad_area', 'objective', 'originality_innovativeness', 
                  'key_activities', 'data_sources', 'technology_usage', 'scalability',
                  'social_impact', 'potent_users']

    def create(self, validated_data):
        return Idea.objects.create(**validated_data) 
        return idea
    
# ---------------------------------------------------------

class StudentSerializer(serializers.ModelSerializer):
    class Meta:
        model = StudentDetails
        fields = ['name', 'email', 'enrollement_id', 'batch_name']

# Stage - 2

# class GuideSerializer(serializers.ModelSerializer):

#     class Meta:
#         model=Guide
#         fields=['mobile_no']

class GuideSetupSerializer(serializers.ModelSerializer):

    expertise_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = Guide
        fields = ['mobile_no', 'expertise_names']

    def update(self, instance, validated_data):
        expertise_names = validated_data.pop('expertise_names', [])

        # Update mobile number
        instance.mobile_no = validated_data.get('mobile_no', instance.mobile_no)
        instance.save()

        # Update expertise (reset then add new ones)
        if expertise_names:
            GuideExpertise.objects.filter(guide=instance).delete()
            for name in expertise_names:
                expertise_obj, _ = Expertise.objects.get_or_create(
                    title=name.strip(),
                    defaults={"description": ""}  # description optional
                )
                GuideExpertise.objects.create(guide=instance, expertise=expertise_obj)

        return instance

from rest_framework import serializers
from .models import GuideProjectInterest

class GuideProjectInterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = GuideProjectInterest
        fields = ["id", "guide", "group", "priority"]
        extra_kwargs = {
            "guide": {"read_only": True}
        }

    def validate(self, data):
        request = self.context["request"]
        guide = request.user.guide_profile   # Guide linked to logged in user
        group = data["group"]
        priority = data["priority"]

        # Each group belongs to a batch → fetch batch
        batch = group.group_students.first().student_batch_link.current_batch
        if not batch:
            raise serializers.ValidationError("This group is not linked to a valid batch.")

        # Prevent duplicate priority per guide per batch
        if GuideProjectInterest.objects.filter(
            guide=guide,
            priority=priority,
            group__group_students__student_batch_link__current_batch=batch
        ).exists():
            raise serializers.ValidationError(
                f"You already assigned {priority} in this batch."
            )

        # Prevent same group assignment
        if GuideProjectInterest.objects.filter(
            guide=guide,
            group=group
        ).exists():
            raise serializers.ValidationError(
                f"You already assigned a priority to Group {group.id}."
            )

        # Enforce max 3 priorities per batch
        current_count = GuideProjectInterest.objects.filter(
            guide=guide,
            group__group_students__student_batch_link__current_batch=batch
        ).count()
        if current_count >= 3:
            raise serializers.ValidationError(
                "You have already assigned 3 priorities for this batch."
            )

        return data

    def create(self, validated_data):
        validated_data["guide"] = self.context["request"].user.guide_profile
        return super().create(validated_data)

    def update(self, instance, validated_data):
        raise serializers.ValidationError("You cannot modify an already assigned priority.")


