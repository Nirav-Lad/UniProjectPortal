from rest_framework.views import APIView
from rest_framework.generics import (ListCreateAPIView,UpdateAPIView,ListAPIView,RetrieveAPIView,
                                     CreateAPIView)
from rest_framework.response import Response
from rest_framework import status
from ..serializers import (
    UserLoginSerializer,BatchSerializer,SetPasswordSerializer,StudentDetailsSerializer,
    StudentInBatchSerializer,StudentDetailsRoleBasedSerializer,GroupSerializer,
    IdeaSubmissionSerializer,GuideSetupSerializer,RegisterUserSerializer,GuidePrioritySerializer,
    )
from ..utils.permissions import IsAdminUser,IsGuideUser
from rest_framework.permissions import IsAuthenticated
from api.utils.email_utils import send_registration_email
# New imports
import pandas as pd, random
from ..models import (UserMaster,Batch,StudentBatch,StudentDetails,GroupFormation,GroupStudents,
                     Idea,TokenTracking,Guide,GuideProjectInterest)
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.utils.timezone import now
from datetime import datetime
from django.utils.timezone import make_aware


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
        """Create or Update multiple priorities at once"""
        guide = Guide.objects.get(user=request.user)

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
                    group_id = item["group"]
                    priority = item["priority"]

                    # Rule: one priority per (guide, group)
                    GuideProjectInterest.objects.update_or_create(
                        guide=guide,
                        group_id=group_id,
                        defaults={"priority": priority},
                    )

            return Response(
                {"message": "Priorities saved successfully"},
                status=status.HTTP_200_OK
            )
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_400_BAD_REQUEST)

    def delete(self, request, *args, **kwargs):
        """Delete one or many priorities"""
        guide = Guide.objects.get(user=request.user)

        priorities_data = request.data.get("priorities", [])
        if not priorities_data:
            return Response(
                {"error": "Priorities list is required"},
                status=status.HTTP_400_BAD_REQUEST
            )

        serializer = GuidePrioritySerializer(data=priorities_data, many=True)
        serializer.is_valid(raise_exception=True)

        deleted_count = 0
        for item in serializer.validated_data:
            group_id = item["group"]
            deleted, _ = GuideProjectInterest.objects.filter(
                guide=guide, group_id=group_id
            ).delete()
            deleted_count += deleted

        if deleted_count > 0:
            return Response(
                {"message": f"{deleted_count} priorities deleted successfully"},
                status=status.HTTP_200_OK
            )
        else:
            return Response(
                {"error": "No matching priorities found to delete"},
                status=status.HTTP_404_NOT_FOUND
            )
