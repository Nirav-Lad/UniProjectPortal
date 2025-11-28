from rest_framework.views import APIView
from rest_framework.generics import (ListCreateAPIView,UpdateAPIView,ListAPIView,RetrieveAPIView,
                                     CreateAPIView)
from rest_framework.response import Response
from rest_framework import status
from ..serializers import (SetPasswordSerializer,GuideSetupSerializer,GuidePrioritySerializer,
    )
from ..utils.permissions import IsAdminUser,IsGuideUser,IsStudentUser
from rest_framework.permissions import IsAuthenticated
from api.utils.email_utils import send_registration_email
# New imports
import pandas as pd, random
from ..models import (UserMaster,Batch,GroupFormation,StudentDetails,GroupStudents,StudentBatch,
                     Idea,GuideGroup,Guide,GuideProjectInterest)
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction


# Stage -2 

# Single guide registration
class RegisterSingleGuideAPIView(APIView):
    permission_classes = [IsAuthenticated]  # Only Admin can register guides

    def post(self, request):
        email = request.data.get('email')
        name = request.data.get('name')
        status_value = request.data.get('status', 'Active')  # default Active

        if not email or not name:
            return Response({'error': 'Email and name are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_email(email)
        except ValidationError:
            return Response({'error': 'Invalid email format.'}, status=status.HTTP_400_BAD_REQUEST)

        if UserMaster.objects.filter(email=email).exists():
            return Response({'error': f'Email {email} is already registered.'}, status=status.HTTP_400_BAD_REQUEST)

        otp = ''.join(random.choices('0123456789', k=6))

        try:
            with transaction.atomic():
                created_by_user = request.user if request.user.is_authenticated else None

                # Create UserMaster for Guide
                user = UserMaster.objects.create(
                    email=email,
                    otp=otp,
                    usertype='Guide',
                    status='Active',
                    created_by=created_by_user
                )

                # Create Guide profile
                guide = Guide.objects.create(
                    user=user,
                    name=name,
                    status=status_value
                )

        except Exception as e:
            return Response({'error': f'Failed to create guide: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Send OTP email
        try:
            send_mail(
                'Guide Registration Successful',
                f'Your OTP is: {otp}',
                'admin@example.com',
                [email],
                fail_silently=False,
            )
        except Exception as e:
            return Response({'warning': f'Guide registered but failed to send OTP email: {str(e)}'},
                            status=status.HTTP_207_MULTI_STATUS)

        return Response({'message': 'Guide registered successfully.'}, status=status.HTTP_201_CREATED)
    
# Setting up the guide first login api view
class GuideFirstLoginAPIView(APIView):
    permission_classes = [IsGuideUser]

    def post(self, request):
        user = request.user

        # Ensure this is a Guide
        try:
            guide = user.guide_profile
        except Guide.DoesNotExist:
            return Response({"error": "Guide record not found."}, status=status.HTTP_404_NOT_FOUND)

        # First login: set password if not already set
        if user.last_login is None:
            password_serializer = SetPasswordSerializer(data=request.data, context={"request": request})
            if password_serializer.is_valid():
                password_serializer.save()
            else:
                return Response(password_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Check if guide details already updated
        if guide.mobile_no and guide.expertise_links.exists():
            return Response(
                {"message": "Password set successfully. Details are already updated."},
                status=status.HTTP_200_OK
            )

        # Update guide details (mobile + expertise)
        details_serializer = GuideSetupSerializer(guide, data=request.data, partial=True)
        if details_serializer.is_valid():
            details_serializer.save()
            return Response(
                {"message": "Password set and details updated successfully."},
                status=status.HTTP_200_OK
            )

        return Response(details_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class GuidePriorityAPIView(APIView):
    permission_classes = [IsGuideUser]
    serializer_class = GuidePrioritySerializer

    def get(self, request, *args, **kwargs):
        """Fetch all priorities for the logged-in guide"""
        guide = Guide.objects.get(user=request.user)
        priorities = GuideProjectInterest.objects.filter(guide=guide)

        data = [
            {"group": p.group.id, "priority": p.priority}
            for p in priorities
        ]
        return Response({"priorities": data}, status=status.HTTP_200_OK)


    def post(self, request, *args, **kwargs):
        """
        Submit priorities ONCE.
        After first submission, guide cannot update or delete.
        """
        guide = Guide.objects.get(user=request.user)

        # RULE: Guide can submit only once
        if GuideProjectInterest.objects.filter(guide=guide).exists():
            return Response(
                {"error": "You have already submitted priorities. Updates are not allowed."},
                status=status.HTTP_403_FORBIDDEN
            )

        priorities_data = request.data.get("priorities", [])
        if not priorities_data:
            return Response(
                {"error": "Priorities list is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = GuidePrioritySerializer(data=priorities_data, many=True)
        serializer.is_valid(raise_exception=True)

        try:
            with transaction.atomic():
                for item in serializer.validated_data:
                    GuideProjectInterest.objects.create(
                        guide=guide,
                        group_id=item["group"],
                        priority=item["priority"]
                    )

            return Response(
                {"message": "Priorities submitted successfully"},
                status=status.HTTP_201_CREATED
            )

        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

# ---------------------------------------------------------------------------------------
class AdminBatchWiseGuidePriorityAPIView(APIView):
    permission_classes = [IsAdminUser]

    def get(self, request, batch_name, *args, **kwargs):
        # Validate Batch
        try:
            batch = Batch.objects.get(batch_name=batch_name)
        except Batch.DoesNotExist:
            return Response({"error": "Batch not found"}, status=status.HTTP_404_NOT_FOUND)

        # Get all groups that have students in this batch
        groups = GroupFormation.objects.filter(
            group_students__student_batch_link__current_batch=batch
        ).distinct()

        if not groups.exists():
            return Response({"error": "No groups found for this batch"}, status=status.HTTP_404_NOT_FOUND)

        final_output = []

        for group in groups:
            # Fetch ideas for group (all fields)
            ideas_data = {}
            for idx, idea_field in enumerate(["idea_1", "idea_2", "idea_3"], start=1):
                idea = getattr(group, idea_field)
                if idea:
                    ideas_data[f"idea{idx}"] = {
                        "id": idea.id,
                        "title": idea.title,
                        "broad_area": idea.broad_area,
                        "objective": idea.objective,
                        "originality_innovativeness": idea.originality_innovativeness,
                        "key_activities": idea.key_activities,
                        "data_sources": idea.data_sources,
                        "technology_usage": idea.technology_usage,
                        "scalability": idea.scalability,
                        "social_impact": idea.social_impact,
                        "potent_users": idea.potent_users,
                        "created_by": idea.created_by.email if idea.created_by else None,
                    }
                else:
                    ideas_data[f"idea{idx}"] = None

            # Fetch guide priorities (P1/P2/P3)
            interests = GuideProjectInterest.objects.filter(group=group)
            priority_map = {"P1": [], "P2": [], "P3": []}

            for interest in interests:
                priority_map[interest.priority].append({
                    "guide_id": interest.guide.id,
                    "guide_email": interest.guide.user.email,
                    "guide_name": interest.guide.name,
                })

            # Fetch assigned guide (ONLY ONE final guide expected)
            assigned = group.assigned_guides.first()

            if assigned:
                assigned_guide = {
                    "guide_id": assigned.guide.id,
                    "guide_email": assigned.guide.user.email,
                    "guide_name": assigned.guide.name,
                    "assigned_on": assigned.assigned_on,
                }
            else:
                assigned_guide = False

            # Fetch group members
            members = []
            for gs in group.group_students.all():
                student_detail = gs.student_batch_link.enrollment
                members.append({
                    "enrollment_id": student_detail.enrollment_id,
                    "name": student_detail.name
                })

            final_output.append({
                "group_id": group.id,
                "ideas": ideas_data,
                "priorities": priority_map,
                "assigned_guide": assigned_guide,   # <-- Now a single guide OR False
                "members": members
            })

        return Response({"batch": batch_name, "groups": final_output}, status=status.HTTP_200_OK)

# -----------------------------------------------------
class AdminAssignFinalGuideAPIView(APIView):
    permission_classes = [IsAdminUser]

    def post(self, request, *args, **kwargs):
        guide_id = request.data.get("guide_id")
        group_id = request.data.get("group_id")

        # Validate payload
        if not guide_id or not group_id:
            return Response(
                {"error": "Both 'guide_id' and 'group_id' are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate group
        try:
            group = GroupFormation.objects.get(id=group_id)
        except GroupFormation.DoesNotExist:
            return Response(
                {"error": "Group not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Validate guide
        try:
            guide = Guide.objects.get(id=guide_id)
        except Guide.DoesNotExist:
            return Response(
                {"error": "Guide not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prevent duplicate assignment
        if GuideGroup.objects.filter(guide=guide, group=group).exists():
            return Response(
                {"error": "This guide is already assigned to this group"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Create assignment
        GuideGroup.objects.create(guide=guide, group=group)

        return Response(
            {
                "message": "Guide assigned successfully",
                "assigned_guide": {
                    "guide_id": guide.id,
                    "guide_name": guide.name,
                    "group_id": group.id
                }
            },
            status=status.HTTP_201_CREATED
        )
    
# -----------------------------------------------------------------------
class GuideDashboardAPIView(APIView):
    permission_classes = [IsGuideUser]

    def get(self, request, *args, **kwargs):
        guide = request.user.guide_profile   # correct relation

        # All groups assigned to this guide
        assigned_groups = GuideGroup.objects.filter(guide=guide)

        final_response = []

        for assigned in assigned_groups:
            group = assigned.group

            # Batch
            batch_name = (
                group.group_students.first()
                .student_batch_link.current_batch.batch_name
            )

            # Members
            members = [
                {
                    "name": gs.student_batch_link.enrollment.name,
                    "enrollment_id": gs.student_batch_link.enrollment.enrollment_id
                }
                for gs in group.group_students.all()
            ]

            # Ideas (full details)
            ideas = {}
            for idx, idea_field in enumerate(["idea_1", "idea_2", "idea_3"], start=1):
                idea = getattr(group, idea_field)
                key = f"idea{idx}"

                if idea:
                    ideas[key] = {
                        "id": idea.id,
                        "title": idea.title,
                        "broad_area": idea.broad_area,
                        "objective": idea.objective,
                        "originality_innovativeness": idea.originality_innovativeness,
                        "key_activities": idea.key_activities,
                        "data_sources": idea.data_sources,
                        "technology_usage": idea.technology_usage,
                        "scalability": idea.scalability,
                        "social_impact": idea.social_impact,
                        "potent_users": idea.potent_users,
                        "created_by": idea.created_by.email if idea.created_by else None,
                        "created_on": idea.created_on,
                    }
                else:
                    ideas[key] = None

            # Finalized idea
            finalized = group.finalized_idea
            finalized_data = {
                "id": finalized.id,
                "title": finalized.title,
                "broad_area": finalized.broad_area,
                "objective": finalized.objective,
                "originality_innovativeness": finalized.originality_innovativeness,
                "key_activities": finalized.key_activities,
                "data_sources": finalized.data_sources,
                "technology_usage": finalized.technology_usage,
                "scalability": finalized.scalability,
                "social_impact": finalized.social_impact,
                "potent_users": finalized.potent_users,
                "created_by": finalized.created_by.email if finalized.created_by else None,
                "created_on": finalized.created_on,
            } if finalized else False

            # Final response per group
            final_response.append({
                "group_id": group.id,
                "batch_name": batch_name,
                "members": members,
                "ideas": ideas,
                "finalized_idea": finalized_data
            })

        return Response(final_response, status=status.HTTP_200_OK)

# ------------------------------------------------------------------
from django.db.models import Q

class GuideFinalizeIdeaAPIView(APIView):
    permission_classes = [IsGuideUser]

    def post(self, request, *args, **kwargs):
        group_id = request.data.get("group_id")
        idea_id = request.data.get("idea_id")

        if not group_id or not idea_id:
            return Response(
                {"error": "group_id and idea_id are required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Fetch Guide Profile (correct related_name = guide_profile)
        try:
            guide = request.user.guide_profile
        except Guide.DoesNotExist:
            return Response(
                {"error": "Guide profile not found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Validate group exists
        try:
            group = GroupFormation.objects.get(id=group_id)
        except GroupFormation.DoesNotExist:
            return Response(
                {"error": "Group not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Ensure guide is assigned
        if not GuideGroup.objects.filter(guide=guide, group=group).exists():
            return Response(
                {"error": "You are not assigned to this group"},
                status=status.HTTP_403_FORBIDDEN
            )

        # Validate idea belongs to this group
        idea_belongs = (
            group.idea_1_id == int(idea_id) or
            group.idea_2_id == int(idea_id) or
            group.idea_3_id == int(idea_id)
        )

        if not idea_belongs:
            return Response(
                {"error": "Idea does not belong to this group"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Fetch idea instance
        try:
            idea = Idea.objects.get(id=idea_id)
        except Idea.DoesNotExist:
            return Response(
                {"error": "Idea not found"},
                status=status.HTTP_404_NOT_FOUND
            )

        # Prevent duplicate finalize
        if group.finalized_idea is not None:
            return Response(
                {"error": "This group already has a finalized idea"},
                status=status.HTTP_400_BAD_REQUEST
            )

        # Finalize Idea
        group.finalized_idea = idea
        group.save()

        return Response(
            {
                "message": "Idea finalized successfully",
                "finalized_idea": {
                    "idea_id": idea.id,
                    "title": idea.title,
                    "group_id": group.id,
                }
            },
            status=status.HTTP_200_OK
        )
# -----------------------------------------------------------------------------------
class StudentGroupDashboardAPIView(APIView):
    permission_classes = [IsStudentUser]  # Only students can access

    def get(self, request, *args, **kwargs):

        # 1️⃣ LOGINED STUDENT (UserMaster)
        user = request.user

        # 2️⃣ FIND STUDENT DETAILS
        try:
            student_details = user.student_details
        except StudentDetails.DoesNotExist:
            return Response(
                {"error": "Student details not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 3️⃣ FIND CURRENT StudentBatch ENTRY
        student_batch = StudentBatch.objects.filter(
            enrollment=student_details,
            status="Active"
        ).first()

        if not student_batch:
            return Response(
                {"error": "Active student batch not found."},
                status=status.HTTP_404_NOT_FOUND
            )

        # 4️⃣ FIND GROUP OF THIS STUDENT
        group_student = GroupStudents.objects.filter(
            student_batch_link=student_batch
        ).first()

        if not group_student:
            return Response(
                {"error": "Student is not assigned to any group."},
                status=status.HTTP_404_NOT_FOUND
            )

        group = group_student.group

        # 5️⃣ GET ALL GROUP MEMBERS
        members = []
        group_member_links = GroupStudents.objects.filter(group=group)

        for m in group_member_links:
            sd = m.student_batch_link.enrollment  # StudentDetails
            members.append({
                "name": sd.name,
                "email": sd.user.email if sd.user else None,
                "enrollment_id": sd.enrollment_id,
                "mobile_no": sd.mobile_no,
                "section": sd.section
            })

        # 6️⃣ FINALIZED IDEA
        finalized_idea = None
        if group.finalized_idea:
            idea = group.finalized_idea
            finalized_idea = {
                "id": idea.id,
                "title": idea.title,
                "broad_area": idea.broad_area,
                "objective": idea.objective,
                "originality_innovativeness": idea.originality_innovativeness,
                "key_activities": idea.key_activities,
                "data_sources": idea.data_sources,
                "technology_usage": idea.technology_usage,
                "scalability": idea.scalability,
                "social_impact": idea.social_impact,
                "potent_users": idea.potent_users,
                "created_by": idea.created_by.email if idea.created_by else None,
                "created_on": idea.created_on
            }

        # 7️⃣ FINALIZED GUIDE (from GuideGroup)
        guide_info = None
        guide_link = GuideGroup.objects.filter(group=group).first()

        if guide_link:
            guide = guide_link.guide
            
            # Expertise
            expertise_list = [
                {
                    "id": ex.expertise.id,
                    "title": ex.expertise.title,
                    "description": ex.expertise.description
                }
                for ex in guide.expertise_links.all()
            ]

            guide_info = {
                "id": guide.id,
                "name": guide.name,
                "email": guide.user.email,
                "mobile_no": guide.mobile_no,
                "status": guide.status,
                "expertise": expertise_list
            }

        # 8️⃣ FINAL RESPONSE
        return Response({
            "group": {
                "group_id": group.id,
                "is_freeze": group.is_freeze,
                "status": group.status,
            },
            "members": members,
            "finalized_idea": finalized_idea,
            "finalized_guide": guide_info
        }, status=status.HTTP_200_OK)
