from rest_framework.views import APIView
from rest_framework.generics import (ListCreateAPIView,UpdateAPIView,ListAPIView,RetrieveAPIView,
                                     CreateAPIView)
from rest_framework.response import Response
from rest_framework import status
from .serializers import (
    UserLoginSerializer,BatchSerializer,SetPasswordSerializer,StudentDetailsSerializer,
    StudentInBatchSerializer,StudentDetailsRoleBasedSerializer,GroupSerializer,
    IdeaSubmissionSerializer)
from rest_framework.permissions import IsAuthenticated
# New imports
import pandas as pd, random
from .models import UserMaster,Batch,StudentBatch,StudentDetails,GroupFormation,GroupStudents
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.db.models import Count
from rest_framework_simplejwt.tokens import RefreshToken

# -----------------------------------------------------------------------------------------
class LoginAPIView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data["user"]
            require_password_change = serializer.validated_data["require_password_change"]

            tokens = RefreshToken.for_user(user)

            return Response({
                "message": "Login successful" if not require_password_change else "OTP verified. Please set your password.",
                "require_password_change": require_password_change,
                "tokens": {
                    "refresh": str(tokens),
                    "access": str(tokens.access_token),
                }
            }, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# -----------------------------------------------------------------------------------------
class SetPasswordAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        serializer = SetPasswordSerializer(data=request.data, context={"request": request})
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "Password set successfully. You can now log in with your password."}, status=status.HTTP_200_OK)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
# -----------------------------------------------------------------------------------------
class BatchCreateView(ListCreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = BatchSerializer

    def get_queryset(self):
        return Batch.objects.filter(created_by=self.request.user)

    def perform_create(self, serializer):
        if self.request.user.usertype != 'Admin':
            raise Exception("You do not have permission to perform this action.")
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
    permission_classes = [IsAuthenticated]  # ✅ Ensure only logged-in users (Admins) can access

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded.'}, status=400)

        try:
            data = pd.read_excel(file, engine='openpyxl')  # ✅ Load Excel file
        except Exception as e:
            return Response({'error': 'Invalid file format.'}, status=400)

        batch_name = request.data.get('batch_name')  # ✅ Get batch name instead of batch_id
        if not batch_name:
            return Response({'error': 'Batch name is required.'}, status=400)

        try:
            batch = Batch.objects.get(batch_name=batch_name)  # ✅ Fetch batch using batch_name
        except Batch.DoesNotExist:
            return Response({'error': f'Batch with name "{batch_name}" not found.'}, status=400)

        created_by_user = request.user if request.user.is_authenticated else None  # ✅ Get admin who is uploading

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

            otp = ''.join(random.choices('0123456789', k=6))  # ✅ Generate OTP

            try:
                with transaction.atomic():
                    # ✅ Create UserMaster with `created_by`
                    user = UserMaster.objects.create(
                        email=email,
                        otp=otp,
                        usertype='Student',
                        status='Active',
                        enrollment_id=enrollment_id,  # ✅ Link enrollment ID to UserMaster
                        created_by=created_by_user  # ✅ Assign created_by
                    )

                    # ✅ Create StudentDetails and link to UserMaster
                    student_details = StudentDetails.objects.create(
                        enrollment_id=enrollment_id,
                        name=name,
                        batch=batch,
                        user=user  # ✅ Ensure StudentDetails is linked to UserMaster
                    )

                    # ✅ Create StudentBatch entry
                    StudentBatch.objects.create(
                        enrollment=student_details,
                        current_batch=batch,
                        status='Active'
                    )
            except Exception as e:
                errors.append(f"Failed to create user {email}: {str(e)}")
                continue

            # ✅ Send email with OTP
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

class RegisterSingleStudentAPIView(APIView):
    permission_classes = [IsAuthenticated]  # ✅ Ensure only logged-in users (Admins) can access

    def post(self, request):
        email = request.data.get('email')
        name = request.data.get('name')
        enrollment_id = request.data.get('enrollment_id')
        batch_name = request.data.get('batch_name')

        if not email or not name or not enrollment_id or not batch_name:
            return Response({'error': 'All fields are required.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            validate_email(email)
        except ValidationError:
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

                # ✅ Create UserMaster with `created_by`
                user = UserMaster.objects.create(
                    email=email,
                    otp=otp,
                    usertype='Student',
                    status='Active',
                    enrollment_id=enrollment_id,  # ✅ Link enrollment ID to UserMaster
                    created_by=created_by_user  # ✅ Assign created_by
                )

                # ✅ Create StudentDetails and link to UserMaster
                student_details = StudentDetails.objects.create(
                    enrollment_id=enrollment_id,
                    name=name,
                    batch=batch,
                    user=user  # ✅ Ensure StudentDetails is linked to UserMaster
                )

                # ✅ Create StudentBatch entry
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

        return Response({'message': 'Student registered successfully.', 'otp': otp}, status=status.HTTP_201_CREATED)

    
# ------------------------------------------------------------------------------------
class UpdateStudentDetailsView(UpdateAPIView):
    serializer_class = StudentDetailsSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user.student_details  #  Correctly fetch StudentDetails object

    def update(self, request, *args, **kwargs):
        student = self.get_object()

        if not student:
            return Response({"error": "Student record not found."}, status=404)

        if student.section and student.mobile_no:
            return Response({"message": "Details already updated."}, status=400)

        return super().update(request, *args, **kwargs)
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
# ----------------------------------------------------------------------------------------
class AvailableGroupsAPIView(ListAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = GroupSerializer

    def get_queryset(self):
        user = self.request.user

        # ✅ Check if user is a student
        if user.usertype != "Student":
            self.permission_denied(self.request, message="Only students can view available groups.")

        # ✅ Ensure the student is assigned to a batch
        student_batch = StudentBatch.objects.filter(enrollment__user=user, current_batch__isnull=False).first()
        if not student_batch:
            self.permission_denied(self.request, message="You are not assigned to any batch.")

        # ✅ Fetch groups with less than 4 members
        groups = GroupFormation.objects.annotate(
            member_count=Count("group_students")
        ).filter(member_count__lt=4)

        if not groups.exists():
            return Response({"message": "No available groups found."}, status=status.HTTP_204_NO_CONTENT)

        return groups
# ----------------------------------------------------------------------------------------
class JoinGroupAPIView(APIView):
    permission_classes = [IsAuthenticated]

    def post(self, request):
        user = request.user

        # Ensure user is a student
        if user.usertype != "Student":
            return Response({"error": "Only students can join groups."}, status=status.HTTP_403_FORBIDDEN)

        # Fetch student's batch
        student_batch = StudentBatch.objects.filter(enrollment__user=user, current_batch__isnull=False).first()
        if not student_batch:
            return Response({"error": "You are not assigned to any batch."}, status=status.HTTP_400_BAD_REQUEST)

        # Check if student is already in a group
        existing_group = GroupStudents.objects.filter(student_batch_link=student_batch).first()
        if existing_group:
            return Response({"error": "You are already in a group."}, status=status.HTTP_400_BAD_REQUEST)

        # Get group_id from request
        group_id = request.data.get("group_id")

        if not group_id:
            # ✅ If no group is provided, create a new one automatically
            with transaction.atomic():
                new_group = GroupFormation.objects.create(status="Pending")
                GroupStudents.objects.create(group=new_group, student_batch_link=student_batch)
            return Response({"message": f"New group created. You are the first member (Group ID: {new_group.id})."}, status=status.HTTP_201_CREATED)

        # ✅ If group_id is provided, check if the group exists
        group = GroupFormation.objects.filter(id=group_id).first()
        if not group:
            return Response({"error": "Group not found."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Check if group has space (max 4 members)
        member_count = GroupStudents.objects.filter(group=group).count()
        if member_count >= 4:
            return Response({"error": "This group is already full."}, status=status.HTTP_400_BAD_REQUEST)

        # ✅ Add student to the group
        GroupStudents.objects.create(group=group, student_batch_link=student_batch)

        return Response({"message": f"Successfully joined group {group_id}."}, status=status.HTTP_200_OK)

# ----------------------------------------------------------------------------------------
class IdeaSubmissionAPIView(CreateAPIView):
    permission_classes = [IsAuthenticated]
    serializer_class = IdeaSubmissionSerializer

    def create(self, request, *args, **kwargs):
        user = request.user
        group = GroupFormation.objects.filter(group_students__student_batch_link__enrollment__user=user).first()

        if not group:
            return Response({"error": "You are not part of any group."}, status=status.HTTP_403_FORBIDDEN)

        if group.finalized_idea:  
            return Response({"error": "Your group’s final idea is already selected. No more ideas can be submitted."}, status=status.HTTP_400_BAD_REQUEST)

        existing_ideas_count = sum(1 for idea in [group.idea_1_id, group.idea_2_id, group.idea_3_id] if idea is not None)

        if existing_ideas_count >= 3:
            return Response({"error": "Your group has already submitted 3 ideas."}, status=status.HTTP_400_BAD_REQUEST)

        response = super().create(request, *args, **kwargs)
        return Response({"message": "Idea submitted successfully!"}, status=status.HTTP_201_CREATED)