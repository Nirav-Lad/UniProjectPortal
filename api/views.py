from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView,UpdateAPIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserLoginSerializer,BatchSerializer,SetPasswordSerializer,StudentDetailsSerializer
from rest_framework.permissions import IsAuthenticated,AllowAny
# New imports
import pandas as pd, random
from .models import UserMaster,Batch,StudentBatch,StudentDetails
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
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
    queryset = Batch.objects.all()
    serializer_class = BatchSerializer

    def perform_create(self, serializer):
        if self.request.user.usertype != 'Admin':
            raise Exception("You do not have permission to perform this action.")
        serializer.save(created_by=self.request.user)

    def create(self, request, *args, **kwargs):
        response = super().create(request, *args, **kwargs)
        return Response(
            {"message": "Batch created successfully!", "batch": response.data},
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
