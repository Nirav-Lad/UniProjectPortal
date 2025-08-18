from rest_framework.views import APIView
from rest_framework.generics import (ListCreateAPIView,UpdateAPIView,ListAPIView,RetrieveAPIView,
                                     CreateAPIView)
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    UserLoginSerializer,BatchSerializer,SetPasswordSerializer,StudentDetailsSerializer,
    StudentInBatchSerializer,StudentDetailsRoleBasedSerializer,GroupSerializer,
    IdeaSubmissionSerializer,GuideSerializer,RegisterUserSerializer)
from .utils.permissions import IsAdminUser
from rest_framework.permissions import IsAuthenticated
# New imports
import pandas as pd, random
from .models import (UserMaster,Batch,StudentBatch,StudentDetails,GroupFormation,GroupStudents,
                     Idea,TokenTracking,Guide)
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenRefreshView
from django.utils.timezone import now
from datetime import datetime
from django.utils.timezone import make_aware

# Common APIs accross whole app
# -----------------------------------------------------------------------------------------
class LoginAPIView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            require_password_change = serializer.validated_data["require_password_change"]
            usertype = serializer.validated_data["usertype"]
            enrollment_id = serializer.validated_data.get("enrollment_id")
            name = serializer.validated_data.get("name")

            # Get client's IP address
            ip_address = request.META.get("REMOTE_ADDR")

            # Get all active sessions for the user
            active_sessions = TokenTracking.objects.filter(user=user, refresh_expires_at__gt=now())

            # ❌ DENY: Prevent multiple logins from the same IP
            if active_sessions.filter(ip_address=ip_address).exists():
                return Response({"error": "You are already logged in from this IP address."}, 
                                status=status.HTTP_403_FORBIDDEN)

            # Extract active refresh tokens and their IPs
            existing_tokens = {session.refresh_token: session.ip_address for session in active_sessions}
            provided_refresh_token = request.data.get("refresh")

            # ❌ DENY: If a refresh token is reused from a different IP
            if provided_refresh_token in existing_tokens and existing_tokens[provided_refresh_token] != ip_address:
                # Logout and revoke all sessions for security
                active_sessions.delete()
                return Response({"error": "Suspicious activity detected. Logged out for security."}, 
                                status=status.HTTP_403_FORBIDDEN)

            # ❌ DENY: If the user exceeds the allowed number of unique IPs (max 3)
            unique_ips = active_sessions.values_list("ip_address", flat=True).distinct()
            if len(unique_ips) >= 3:
                return Response({"error": "You have reached the limit of 3 different login locations."}, 
                                status=status.HTTP_403_FORBIDDEN)

            # ✅ Generate new JWT tokens
            tokens = RefreshToken.for_user(user)
            access_token = str(tokens.access_token)
            refresh_token = str(tokens)

            # Get token expiration times
            access_expires_at = make_aware(datetime.utcfromtimestamp(tokens.access_token.payload.get("exp")))
            refresh_expires_at = make_aware(datetime.utcfromtimestamp(tokens.payload.get("exp")))

            # ✅ Revoke all previous refresh tokens (prevents replay attacks)
            active_sessions.delete()

            # ✅ Store the new session in the database
            TokenTracking.objects.create(
                user=user,
                access_token=access_token,
                refresh_token=refresh_token,
                ip_address=ip_address,
                access_expires_at=access_expires_at,
                refresh_expires_at=refresh_expires_at
            )

            return Response({
                "message": "Login successful" if not require_password_change else "OTP verified. Please set your password.",
                "require_password_change": require_password_change,
                "tokens": {
                    "refresh": refresh_token,
                    "access": access_token,
                },
                "user_details": {
                    "usertype": usertype,
                    "enrollment_id": enrollment_id,
                    "name": name
                }
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

# -----------------------------------------------------------------------------------------
class LogoutAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        # Get the refresh token and client's IP address
        refresh_token = request.data.get("refresh_token","").strip()
        ip_address = request.META.get("REMOTE_ADDR")
        print("Refresh_token",refresh_token)
        print("IP address",ip_address)

        if not refresh_token:
            print("1")
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve the session entry
            token_entry = TokenTracking.objects.get(refresh_token=refresh_token, user=request.user)
            print("2")
            # ❌ Prevent logout if IP mismatch (potential stolen token)
            if token_entry.ip_address != ip_address:
                return Response({"error": "Suspicious activity detected. Cannot logout from a different IP."},
                                status=status.HTTP_403_FORBIDDEN)
            print("3")
            # ✅ Delete only the session associated with this token
            token_entry.delete()
            print("4")
            return Response({"message": "Logout successful."}, status=status.HTTP_200_OK)

        except TokenTracking.DoesNotExist:
            print("5")
            return Response({"error": "Session not found or already logged out."}, status=status.HTTP_404_NOT_FOUND)
# -----------------------------------------------------------------------------------------
class CustomTokenRefreshView(TokenRefreshView):
    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get("refresh")
        ip_address = request.META.get("REMOTE_ADDR")

        if not refresh_token:
            return Response({"error": "Refresh token is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Retrieve session entry
            token_entry = TokenTracking.objects.get(refresh_token=refresh_token)

            # Prevent refresh if IP mismatch (security check)
            if token_entry.ip_address != ip_address:
                return Response({"error": "Suspicious activity detected. Cannot refresh token from a different IP."}, 
                                status=status.HTTP_403_FORBIDDEN)

            # Generate new tokens
            new_tokens = RefreshToken(refresh_token)
            new_access_token = str(new_tokens.access_token)
            new_refresh_token = str(new_tokens)

            # Update TokenTracking entry with new tokens
            token_entry.access_token = new_access_token
            token_entry.refresh_token = new_refresh_token

            # Update expiration times
            token_entry.access_expires_at = make_aware(datetime.utcfromtimestamp(new_tokens.access_token.payload.get("exp")))
            token_entry.refresh_expires_at = make_aware(datetime.utcfromtimestamp(new_tokens.payload.get("exp")))

            token_entry.save()

            return Response({
                "message": "Token refreshed successfully",
                "tokens": {
                    "access": new_access_token,
                    "refresh": new_refresh_token
                }
            }, status=status.HTTP_200_OK)

        except TokenTracking.DoesNotExist:
            return Response({"error": "Invalid or expired refresh token."}, status=status.HTTP_400_BAD_REQUEST)

class RegisterUserAPIView(APIView):
    permission_classes=[IsAdminUser]

    def post(self,request):
        serializer=RegisterUserSerializer(data=request.data,context={'request':request})

        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user=serializer.save()
        except Exception as e:
            return Response({'error':f'Failed to create user : {str(e)} '},status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        

        # Send OTP
        try:
            send_mail(
                f'Registration successful at UniProject Portal as {user.usertype}',
                f'Your OTP is : {user.otp} ',
                'admin@example.com',
                [user.email],
                fail_silently=False
            )
        except Exception as e:
            return Response(
                {'Warning':f'User registered but failed to send OTP email : {str(e)}'},
                 status=status.HTTP_207_MULTI_STATUS
            )
        
        return Response({'message':f'{user.usertype} registered successfully.'},status=status.HTTP_201_CREATED)
        

# -----------------------------------------------------------------------------------------
# Stage - 1 APIs
# There exists no such api view for batch creation 
class BatchCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BatchSerializer

    def get_queryset(self):
        return Batch.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.usertype != 'Admin':
            raise Exception("You do not have permission to perform this action.")

        # Check if a batch with the same name already exists
        batch_name = serializer.validated_data.get('batch_name')
        if Batch.objects.filter(batch_name=batch_name).exists():
            raise Exception({"error": "Batch with this name already exists."})

        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response(
            {"message": "Batch created successfully"},
            status=status.HTTP_201_CREATED
        )

# -----------------------------------------------------------------------------------------
# Student upload api via excel sheet and pandas to break it
class StudentUploadView(APIView):
    permission_classes = [IsAuthenticated]  # Ensure only logged-in users (Admins) can access

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded.'}, status=400)

        try:
            data = pd.read_excel(file, engine='openpyxl')  # Load Excel file
        except Exception as e:
            return Response({'error': 'Invalid file format.'}, status=400)

        batch_name = request.data.get('batch_name')  # Get batch name instead of batch_id
        if not batch_name:
            return Response({'error': 'Batch name is required.'}, status=400)

        try:
            batch = Batch.objects.get(batch_name=batch_name)  # Fetch batch using batch_name
        except Batch.DoesNotExist:
            return Response({'error': f'Batch with name "{batch_name}" not found.'}, status=400)

        created_by_user = request.user if request.user.is_authenticated else None  # Get admin who is uploading

        errors = []
        for row in data.to_dict('records'):
            email = row.get('email')
            name = row.get('name')
            enrollment_id = row.get('enrollment_id')

            if not email or not name or not enrollment_id:
                errors.append(f"Missing required fields in row: {row}")
                continue

            try:
                validate_email(email)
            except ValidationError:
                errors.append(f"Invalid email format: {email}")
                continue

            if StudentDetails.objects.filter(enrollment_id=enrollment_id).exists():
                errors.append(f"Enrollment ID {enrollment_id} already exists.")
                continue

            if UserMaster.objects.filter(email=email).exists():
                errors.append(f"Email {email} is already registered.")
                continue

            otp = ''.join(random.choices('0123456789', k=6))  # Generate OTP

            try:
                with transaction.atomic():
                    # Create UserMaster with `created_by`
                    user = UserMaster.objects.create(
                        email=email,
                        otp=otp,
                        usertype='Student',
                        status='Active',
                        enrollment_id=enrollment_id,  # Link enrollment ID to UserMaster
                        created_by=created_by_user  # Assign created_by
                    )

                    # Create StudentDetails and link to UserMaster
                    student_details = StudentDetails.objects.create(
                        enrollment_id=enrollment_id,
                        name=name,
                        batch=batch,
                        user=user  # Ensure StudentDetails is linked to UserMaster
                    )

                    # Create StudentBatch entry
                    StudentBatch.objects.create(
                        enrollment=student_details,
                        current_batch=batch,
                        status='Active'
                    )
            except Exception as e:
                errors.append(f"Failed to create user {email}: {str(e)}")
                continue

            # Send email with OTP
            try:
                send_mail(
                    'Registration Successful',
                    f'Your OTP is: {otp}',
                    'admin@example.com',
                    [email],
                    fail_silently=False,
                )
            except Exception as e:
                errors.append(f"Failed to send email to {email}: {str(e)}")
                continue

        if errors:
            return Response({'message': 'Students registered with some errors.', 'errors': errors}, status=207)

        return Response({'message': 'Students registered successfully.'}, status=201)
    
# -----------------------------------------------------------------------------------------    
# ----------SIngle student upload

# Checks for admin user type=can only perform the restricted operations
# like user creation and etc. 
class RegisterSingleStudentAPIView(APIView):
    permission_classes = [IsAuthenticated]  #  Ensure only logged-in users (Admins) can access

    def post(self, request):
        email = request.data.get('email')
        name = request.data.get('name')
        enrollment_id = request.data.get('enrollment_id')
        batch_name = request.data.get('batch_name')

        # print("requested data:", request.data)
        print("requested data name:", request.data.get('name'))
        print("requested data email:", request.data.get('email'))
        print("requested data enrollment_id:", request.data.get('enrollment_id'))
        print("requested data batch_name:", request.data.get('batch_name'))

        if not email or not name or not enrollment_id or not batch_name:
            return Response({'error': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_email(email)
        except ValidationError:
            print(" 1 requested data:", request.data)
            return Response({'error': 'Invalid email format.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            batch = Batch.objects.get(batch_name=batch_name)
        except Batch.DoesNotExist:
            return Response({'error': 'Invalid batch name.'}, status=status.HTTP_400_BAD_REQUEST)

        if StudentDetails.objects.filter(enrollment_id=enrollment_id).exists():
            return Response({'error': f'Enrollment ID {enrollment_id} already exists.'}, status=status.HTTP_400_BAD_REQUEST)

        if UserMaster.objects.filter(email=email).exists():
            return Response({'error': f'Email {email} is already registered.'}, status=status.HTTP_400_BAD_REQUEST)

        otp = ''.join(random.choices('0123456789', k=6))

        try:
            with transaction.atomic():
                created_by_user = request.user if request.user.is_authenticated else None

                # Create UserMaster with created_by
                user = UserMaster.objects.create(
                    email=email,
                    otp=otp,
                    usertype='Student',
                    status='Active',
                    enrollment_id=enrollment_id,  # Link enrollment ID to UserMaster
                    created_by=created_by_user  # Assign created_by
                )

                # Create StudentDetails and link to UserMaster
                student_details = StudentDetails.objects.create(
                    enrollment_id=enrollment_id,
                    name=name,
                    batch=batch,
                    user=user  # Ensure StudentDetails is linked to UserMaster
                )

                # Create StudentBatch entry
                StudentBatch.objects.create(
                    enrollment=student_details,
                    current_batch=batch,
                    status='Active'
                )
        except Exception as e:
            return Response({'error': f'Failed to create student: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        # Send email with OTP
        try:
            send_mail(
                'Registration Successful',
                f'Your OTP is: {otp}',
                'admin@example.com',
                [email],
                fail_silently=False,
            )
        except Exception as e:
            return Response({'warning': f'Student registered but failed to send OTP email: {str(e)}'}, status=status.HTTP_207_MULTI_STATUS)

        return Response({'message': 'Student registered successfully.'}, status=status.HTTP_201_CREATED)

# ---------------------------------------------------------------------------------------
class GetStudentsInBatchAPIView(ListAPIView):
    serializer_class = StudentInBatchSerializer
    permission_classes = [IsAuthenticated]  

    def get_queryset(self):
        batch_name = self.kwargs.get("batch_name") 
        try:
            batch = Batch.objects.get(batch_name=batch_name) 
        except Batch.DoesNotExist:
            return StudentDetails.objects.none()  

        return StudentDetails.objects.filter(batch=batch) 
# ---------------------------------------------------------------------------------------
class GetSingleStudentAPIView(RetrieveAPIView):
    serializer_class = StudentDetailsRoleBasedSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Retrieve student details by enrollment_id.
        """
        user = self.request.user
        if user.usertype != "Admin":
            raise Exception("Only admins can access this.")

        enrollment_id = self.kwargs.get("enrollment_id")

        try:
            return StudentDetails.objects.get(enrollment_id=enrollment_id)
        except StudentDetails.DoesNotExist:
            raise Exception("Student not found.")

# ----------------------------------------------------------------------------------------
class GetStudentProfileAPIView(RetrieveAPIView):
#    View to see profile of their by students
    serializer_class = StudentDetailsRoleBasedSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        """
        Fetch details of the logged-in student.
        """
        user = self.request.user

        if user.usertype != "Student":
            raise Exception("Only students can access this profile.")

        try:
            return user.student_details  # Fetch linked StudentDetails record
        except StudentDetails.DoesNotExist:
            raise Exception("Student profile not found.")
# ------------------------------------------------------------------------------------------
# # ----------------------------------------------------------------------------------------
class FreezeGroupFormationAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if request.user.usertype != "Admin":
            return Response({"error": "You do not have permission to perform this action."}, status=status.HTTP_403_FORBIDDEN)

        GroupFormation.objects.update(is_freeze=True)

        return Response({"message": "Group formation has been frozen. No further changes allowed."}, status=status.HTTP_200_OK)

# ----------------------------------------------------------------------------------------
# This code is first tested then only 
# Get enrollment id's
class BatchEnrollmentIDsAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        user = request.user

        # Ensure the user is a student
        if user.usertype != "Student":
            return Response({"error": "Only students can view enrollment IDs."}, status=status.HTTP_403_FORBIDDEN)

        # Get the batch of the logged-in student
        student_batch = StudentBatch.objects.filter(enrollment__user=user, current_batch__isnull=False).first()
        if not student_batch:
            return Response({"error": "You are not assigned to any batch."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if the logged-in user is already in a group and get the group ID
        group_student = GroupStudents.objects.filter(student_batch_link=student_batch).select_related('group').first()
        if group_student:
            return Response(
                {
                    "message": "You are already in a group.",
                    "is_already_in_group": True,
                    "group_id": group_student.group.id  # Sending the group ID
                },
                status=status.HTTP_200_OK
            )

        # Get the enrollment ID of the logged-in user
        logged_in_enrollment_id = student_batch.enrollment.enrollment_id

        # Get student batches that are already in a group
        grouped_students = GroupStudents.objects.values_list("student_batch_link_id", flat=True)

        # Fetch enrollment IDs and names of other students in the same batch (excluding logged-in user & already grouped students)
        students = StudentBatch.objects.filter(
            current_batch=student_batch.current_batch
        ).exclude(enrollment__enrollment_id=logged_in_enrollment_id).exclude(id__in=grouped_students).select_related("enrollment")

        # Prepare response data with enrollment IDs and names
        student_data = [
            {"enrollment_id": student.enrollment.enrollment_id, "name": student.enrollment.name}
            for student in students
        ]

        return Response({"students": student_data, "is_already_in_group": False}, status=status.HTTP_200_OK)

# -------------------------------------------------------------------------------------
# Register group
class RegisterGroupAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user
        # Ensure only students can register groups
        if user.usertype != "Student":
            return Response({"error": "Only students can register groups."}, status=status.HTTP_403_FORBIDDEN)

        # Get the batch of the logged-in student
        student_batch = StudentBatch.objects.filter(enrollment__user=user, current_batch__isnull=False).first()
        if not student_batch:
            return Response({"error": "You are not assigned to any batch."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if student is already in a group
        existing_group = GroupStudents.objects.filter(student_batch_link=student_batch).first()
        if existing_group:
            return Response({"error": "You are already in a group."}, status=status.HTTP_400_BAD_REQUEST)

        # Get the list of enrollment IDs from the request
        enrollment_ids = request.data.get("enrollment_ids", [])

        if not enrollment_ids or not (2 <= len(enrollment_ids) <= 3):
            return Response({"error": "You must provide enrollment IDs of 2-3 other students."}, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the student batch objects of provided enrollment IDs
        batch_students = StudentBatch.objects.filter(enrollment__enrollment_id__in=enrollment_ids, current_batch=student_batch.current_batch)

        if batch_students.count() != len(enrollment_ids):
            return Response({"error": "Some enrollment IDs are invalid or not in your batch."}, status=status.HTTP_400_BAD_REQUEST)

        # Create the new group
        with transaction.atomic():
            new_group = GroupFormation.objects.create(status="Active")
            # Add the registering student
            GroupStudents.objects.create(group=new_group, student_batch_link=student_batch)
            # Add the selected students
            for student in batch_students:
                GroupStudents.objects.create(group=new_group, student_batch_link=student)

        return Response({"message": f"Group registered successfully.","group_id":{new_group.id}}, status=status.HTTP_201_CREATED)

# ----------------------------------------------------------------------------------------
class IdeaSubmissionAPIView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IdeaSubmissionSerializer

    def create(self, request, *args, **kwargs):
        user = request.user
        print(request.data)

        # Ensure only students can submit ideas
        if user.usertype != "Student":
            return Response({"error": "Only students can submit ideas."}, status=status.HTTP_403_FORBIDDEN)

        # Fetch the group of the logged-in student
        group = GroupFormation.objects.filter(group_students__student_batch_link__enrollment__user=user).first()
        if not group:
            return Response({"error": "You are not part of any group."}, status=status.HTTP_403_FORBIDDEN)

        if group.is_freeze:
            return Response({"error": "Group formation is frozen. Idea submission is not allowed."}, status=status.HTTP_400_BAD_REQUEST)

        if group.finalized_idea:
            return Response({"error": "Your group’s final idea is already selected. No more ideas can be submitted."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure request contains `idea_id`
        idea_number = request.data.get("idea_id")
        if idea_number not in [1, 2, 3]:
            return Response({"error": "Invalid idea_id. Must be 1, 2, or 3."}, status=status.HTTP_400_BAD_REQUEST)

        # Map idea_id to the corresponding field in GroupFormation
        idea_field_map = {1: "idea_1", 2: "idea_2", 3: "idea_3"}
        idea_field = idea_field_map[idea_number]

        # Check if an idea already exists in this slot
        existing_idea = getattr(group, idea_field, None)
        if existing_idea:
            return Response({"error": f"Idea slot {idea_number} is already filled. Please update it instead."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)

            # Save idea with created_by set automatically
            idea = serializer.save(created_by=user)

            # Assign idea to the specified slot
            setattr(group, idea_field, idea)
            group.save()

        return Response({"message": f"Idea {idea_number} submitted successfully."}, status=status.HTTP_201_CREATED)

# ------------------------------------------------------------------------------------------------------
class CheckIdeaSubmissionAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, *args, **kwargs):
        user = request.user

        # Ensure only students can check idea submission
        if user.usertype != "Student":
            return Response({"error": "Only students can check idea submission."}, status=status.HTTP_403_FORBIDDEN)

        # Get the student's group
        group = GroupFormation.objects.filter(group_students__student_batch_link__enrollment__user=user).first()

        if not group:
            return Response({"error": "You are not part of any group."}, status=status.HTTP_403_FORBIDDEN)

        # Check each idea slot and add an 'is_submitted' field
        ideas_data = []

        for idx, idea in enumerate([group.idea_1, group.idea_2, group.idea_3], start=1):
            if idea:
                idea_data = IdeaSubmissionSerializer(idea).data
                idea_data["idea_id"] = idx  # Assign idea ID (1, 2, or 3)
                idea_data["is_submitted"] = True
            else:
                idea_data = {
                    "idea_id": idx,
                    "is_submitted": False
                }
            
            ideas_data.append(idea_data)

        return Response({"ideas": ideas_data}, status=status.HTTP_200_OK)
# ----------------------------------------------------------------------------------------
class UpdateIdeaAPIView(UpdateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class=IdeaSubmissionSerializer
    queryset = Idea.objects.all()

    def get_object(self):
        """Fetch the idea based on idea_id (1, 2, or 3) from GroupFormation."""
        user = self.request.user

        # Ensure the user is a student
        if user.usertype != "Student":
            return Response({"error": "Only students can update ideas."}, status=status.HTTP_403_FORBIDDEN)

        # Get the user's group
        group = GroupFormation.objects.filter(group_students__student_batch_link__enrollment__user=user).first()
        if not group:
            return Response({"error": "You are not part of any group."}, status=status.HTTP_403_FORBIDDEN)

        if group.is_freeze:
            return Response({"error": "Group formation is frozen. Idea updation is not allowed."}, status=status.HTTP_400_BAD_REQUEST)

        # Ensure request contains `idea_id`
        idea_number = self.request.data.get("idea_id")
        if idea_number not in [1, 2, 3]:
            return Response({"error": "Invalid idea ID. Must be 1, 2, or 3."}, status=status.HTTP_400_BAD_REQUEST)

        # Map idea_id (1, 2, 3) to the corresponding field in GroupFormation
        idea_field_map = {1: group.idea_1, 2: group.idea_2, 3: group.idea_3}
        idea = idea_field_map.get(idea_number)

        if not idea:
            return Response({"error": f"Idea {idea_number} is not assigned to your group."}, status=status.HTTP_404_NOT_FOUND)

        return idea

    def update(self, request, *args, **kwargs):
        """Update the idea details."""
        idea = self.get_object()
        if isinstance(idea, Response):
            return idea  # Return error response if get_object() fails

        with transaction.atomic():
            serializer = self.get_serializer(idea, data=request.data, partial=True)
            if serializer.is_valid():
                serializer.save()

        return Response({"message": "Idea updated successfully!"}, status=status.HTTP_200_OK)

# ----------------------------------------------------------------------------------------
class IdeaResetAPIView(APIView):
    
    permission_classes = [IsAuthenticated]
    def delete(self, request, *args, **kwargs):
        user = request.user
        idea_index = request.data.get("idea_id")  # User provides 1, 2, or 3
        print(request.data)
        print(idea_index)

        if idea_index not in [1, 2, 3]:
            return Response({"error": "Invalid idea_id. Must be 1, 2, or 3."}, status=status.HTTP_400_BAD_REQUEST)

        # Find the user's group
        group = GroupFormation.objects.filter(group_students__student_batch_link__enrollment__user=user).first()

        if not group:
            return Response({"error": "You are not part of any group."}, status=status.HTTP_403_FORBIDDEN)

        if group.is_freeze:
            return Response({"error": "Group formation is frozen. Idea reset is not allowed."}, status=status.HTTP_400_BAD_REQUEST)

        # Determine the actual idea ID stored in GroupFormation based on the provided idea_index
        idea_to_delete = None

        if idea_index == 1 and group.idea_1:
            idea_to_delete = group.idea_1
            group.idea_1 = None
        elif idea_index == 2 and group.idea_2:
            idea_to_delete = group.idea_2
            group.idea_2 = None
        elif idea_index == 3 and group.idea_3:
            idea_to_delete = group.idea_3
            group.idea_3 = None
        else:
            return Response({"error": "Idea not found in the specified slot."}, status=status.HTTP_404_NOT_FOUND)

        # Safely update the database
        with transaction.atomic():
            group.save()  # Remove reference to idea in GroupFormation
            idea_to_delete.delete()  # Delete idea from Idea table
            
        return Response({"message": "Idea reset successfully!"}, status=status.HTTP_200_OK)
# ----------------------------------------------------------------------------------------
class StudentGroupDetailsAPIView(RetrieveAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer

    def get_object(self):
        user = self.request.user

        if user.usertype != "Student":
            raise Exception("Only students can access this.")

        group = GroupFormation.objects.filter(group_students__student_batch_link__enrollment__user=user).first()
        if not group:
            raise Exception("You are not part of any group.")

        return group
    
# ----------------------------------------------------------------------------------------
class AdminGroupOverviewAPIView(APIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer  # Define the serializer class

    def get_queryset(self):
        user = self.request.user

        if user.usertype != "Admin":
            raise ValidationError("Only admins can access this.")

        batch_name = self.request.data.get("batch_name")
        if not batch_name:
            raise ValidationError("Batch name is required.")

        try:
            # Step 1: Get the batch
            batch = Batch.objects.get(batch_name=batch_name)

            # Step 2: Get students in this batch
            student_batches = StudentBatch.objects.filter(current_batch=batch)

            # Step 3: Find groups associated with these students
            groups = GroupFormation.objects.filter(
                group_students__student_batch_link__in=student_batches
            ).distinct()

            return groups

        except Batch.DoesNotExist:
            raise ValidationError("Batch not found.")

    def post(self, request, *args, **kwargs):
        queryset = self.get_queryset()

        # ✅ Corrected: Manually create the serializer instance
        serializer = self.serializer_class(queryset, many=True)

        # ✅ Corrected: Convert serializer data into a dictionary
        response_data = {str(group["id"]): group for group in serializer.data}

        return Response(response_data, status=status.HTTP_200_OK)
    
# ----------------------------------------------------------------------------------------
class SetupStudentAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Check if password needs to be set
        if user.last_login is None:
            password_serializer = SetPasswordSerializer(data=request.data, context={"request": request})
            if password_serializer.is_valid():
                password_serializer.save()
            else:
                return Response(password_serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        # Fetch the student's details
        try:
            student = user.student_details
        except StudentDetails.DoesNotExist:
            return Response({"error": "Student record not found."}, status=status.HTTP_404_NOT_FOUND)

        # Check if student details are already updated
        if student.section and student.mobile_no:
            return Response({"message": "Password set successfully. Details are already updated."}, status=status.HTTP_200_OK)

        # Update student details
        details_serializer = StudentDetailsSerializer(student, data=request.data, partial=True)
        if details_serializer.is_valid():
            details_serializer.save()
            return Response({"message": "Password set and details updated successfully."}, status=status.HTTP_200_OK)

        return Response(details_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# ----------------------------------------------------------------------------------------------
# Admin view for student list and thei details
class AdminStudentListView(APIView):
    permission_classes = [IsAuthenticated]  # Only authenticated users can access

    def get(self, request):
        # Ensure only Admin users can access this
        if request.user.usertype != 'Admin':  # Adjust based on your user model
            return Response({"message": "You are not authorized to access this data."}, status=status.HTTP_403_FORBIDDEN)

        # Fetch students linked to this admin (if `created_by` exists)
        students = StudentDetails.objects.filter(user__created_by=request.user)

        # Manually structure the response data
        student_data = []
        for student in students:
            # Get group information if the student is part of a group
            group_student = GroupStudents.objects.filter(student_batch_link__enrollment=student).first()
            group_id = group_student.group.id if group_student else None
            group_status = "Joined" if group_student else "Pending"

            student_data.append({
                "enrollment_id": student.enrollment_id,
                "email": student.user.email if student.user else None,  # Fetching email from UserMaster
                "name": student.name,
                "batch_name": student.batch.batch_name if student.batch else None,
                "group_id": group_id,
                "group_status": group_status,
                "section": student.section,
                "mobile_no": student.mobile_no
            })

        return Response({"students": student_data}, status=status.HTTP_200_OK)


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
    permission_classes=[IsAuthenticated]

    def post(self,request):
        user=request.user

        # Check if password needs to be set
        if user.last_login is None:
            password_serializer = SetPasswordSerializer(data=request.data, context={"request": request})
            if password_serializer.is_valid():
                password_serializer.save()
            else:
                return Response(password_serializer.errors, status=status.HTTP_400_BAD_REQUEST)
            
        guide_serializer=GuideSerializer(Guide,data=request.data,)



