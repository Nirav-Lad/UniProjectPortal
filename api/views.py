from rest_framework.views import APIView
from rest_framework.generics import ListCreateAPIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserLoginSerializer,BatchSerializer,SetPasswordSerializer
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
    permission_classes = [AllowAny]

    def post(self, request):
        file = request.FILES.get('file')
        if not file:
            return Response({'error': 'No file uploaded.'}, status=400)
        
        try:
            data = pd.read_excel(file, engine='openpyxl')  # Specify engine for compatibility
        except Exception as e:
            return Response({'error': 'Invalid file format.'}, status=400)

        batch_id = request.data.get('batch_id')
        try:
            batch = Batch.objects.get(batch_id=batch_id)
        except Batch.DoesNotExist:
            return Response({'error': 'Invalid batch ID.'}, status=400)

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

            otp = ''.join(random.choices('0123456789', k=6))

            try:
                with transaction.atomic():
                    # Create the student details first
                    student_details = StudentDetails.objects.create(
                        enrollment_id=enrollment_id,
                        name=name,
                        batch=batch
                    )

                    # Create the user
                    user = UserMaster.objects.create(
                        email=email,
                        otp=otp,
                        usertype='Student',
                        status='Active'
                    )

                    # Create the student batch
                    StudentBatch.objects.create(
                        enrollment=student_details,  # Link to the StudentDetails record
                        current_batch=batch,
                        status='Active'
                    )
            except Exception as e:
                errors.append(f"Failed to create user {email}: {str(e)}")
                continue

            # Send email
            try:
                send_mail(
                    'Registration Successful',
                    f'Your OTP is: {otp}',
                    'niravlad1090@gmail.com',
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
    permission_classes = [AllowAny]

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
                # Create StudentDetails entry
                student_details = StudentDetails.objects.create(
                    enrollment_id=enrollment_id,
                    name=name,
                    batch=batch
                )

                # Create UserMaster entry
                user = UserMaster.objects.create(
                    email=email,
                    otp=otp,
                    usertype='Student',
                    status='Active'
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
                'niravlad1090@gmail.com',
                [email],
                fail_silently=False,
            )
        except Exception as e:
            return Response({'warning': f'Student registered but failed to send OTP email: {str(e)}'}, status=status.HTTP_207_MULTI_STATUS)

        return Response({'message': 'Student registered successfully.', 'otp': otp}, status=status.HTTP_201_CREATED)
