from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserLoginSerializer,BatchSerializer
from rest_framework.permissions import IsAuthenticated,AllowAny
# New imports
import pandas as pd, random
from .models import UserMaster,Batch,StudentBatch,StudentDetails
from django.core.mail import send_mail
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.db import transaction
from django.contrib.auth.hashers import make_password

class LoginAPIView(APIView):
    def post(self, request):
        serializer = UserLoginSerializer(data=request.data)
        if serializer.is_valid():
            user = serializer.validated_data
            tokens = serializer.get_tokens(user)
            return Response({
                "message": "Login successful",
                "tokens": tokens
            }, status=status.HTTP_200_OK)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
class BatchcreateView(APIView):
    permission_classes=[IsAuthenticated]

    def post(self,request):
        if request.user.usertype != 'Admin':
            return Response(
                {"error": "You do not have permission to perform this action."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = BatchSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save(created_by=request.user)  
            return Response({"message":"batch created successfully!!"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    

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
    
# ----------SIngle student upload

class RegisterStudent(APIView):
    permission_classes=[AllowAny]

    def post(self,request):
        name=request.data.get('fullName')
        email=request.data.get('email')
        enrolment_id=request.data.get('enrollmentid')

        return Response({"Msg":"Registered"},status=201)

