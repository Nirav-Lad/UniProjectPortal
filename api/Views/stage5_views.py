from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import SubmissionWindow,StudentBatch,Batch,ProjectDocument,GroupStudents
from api.serializers import stage5_serializers
from ..utils.permissions import IsAdminOrGuideUser,IsStudentUser

class SubmissionWindowAPIView(APIView):
    # permission_classes=[IsAuthenticated]

    def get_permissions(self):
        if self.request.method in ["POST","PATCH","DELETE"]:
            return [IsAdminOrGuideUser()]
        return [IsAuthenticated()]

    def post(self,request):

        if request.user.usertype not in ["Admin","Guide"]:
            return Response({"message":"Only Admin or Guide can create the Submission."},status=status.HTTP_403_FORBIDDEN)
        
        serializer=stage5_serializers.SubmissionWindowCreateSerializer(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        submission=serializer.save(
            created_by=request.user,
            is_active=True
        )

        return Response({
            "message":"Submission Created successfully"
        },status=status.HTTP_201_CREATED)
    
    def get(self, request):
        user = request.user
        if user.usertype in ["Admin", "Guide"]:
            batch_id = request.query_params.get('batch_id')

            if not batch_id:
                return Response(
                    {"message": "batch_id is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            queryset = SubmissionWindow.objects.filter(batch_id=batch_id)

        elif user.usertype == "Student":
            student_batch = StudentBatch.objects.filter(enrollment_id=user.enrollment_id).first()
            batch=Batch.objects.filter(batch_id=student_batch.current_batch_id).first()

            if not batch:
                return Response(
                    {"message": "Student is not assigned to any batch"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            queryset = SubmissionWindow.objects.filter(
                batch=batch,
                is_active=True
            )

        else:
            return Response(
                {"message": "Invalid role"},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = stage5_serializers.SubmissionWindowReadSerializer(
            queryset,
            many=True,
            context={'request': request}
        )

        return Response({
            "count": queryset.count(),
            "data": serializer.data
        }, status=status.HTTP_200_OK)

    def patch(self, request):
        try:
            submission=SubmissionWindow.objects.get(id=request.query_params.get("id"),created_by=request.user)
        except SubmissionWindow.DoesNotExist:
            return Response(
                {"message":"No submission found with provided submission id or may be not owned by you."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        serializer=stage5_serializers.SubmissionWindowUpdateSerializer(
            submission,
            data=request.data,
            partial=True    
        )

        if not serializer.is_valid():
            return Response(serializer.errors,status=status.HTTP_400_BAD_REQUEST)
        
        serializer.save()

        return Response(
            {"message":"Submission updated successfully..",
             "data":serializer.data},
            status=status.HTTP_200_OK
        )

    def delete(self, request):

        try:
            submission=SubmissionWindow.objects.get(id=request.query_params.get("id"),created_by=request.user)
        except SubmissionWindow.DoesNotExist:
            return Response(
                {"message":"No submission found with provided submission id or no any owned by you."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        if submission.is_active:
            return Response(
                {"message": "Deactivate submission before deleting"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        if submission.documents.exists() or submission.statuses.exists():
            return Response(
                {"message": "Cannot delete submission with existing records"},
                status=status.HTTP_400_BAD_REQUEST
            )
        
        submission.delete()

        return Response(
            {"message": "Submission deleted successfully"},
            status=status.HTTP_200_OK
        )
        
class SubmissionWindowToggleAPIView(APIView):
    permission_classes=[IsAdminOrGuideUser]

    def patch(self,request):
        try:
            submission=SubmissionWindow.objects.get(id=request.query_params.get("id"),created_by=request.user)
        except SubmissionWindow.DoesNotExist:
            return Response(
                {"message":"No submission found with provided submission id or may be not owned by you."},
                status=status.HTTP_404_NOT_FOUND
            )
        
        submission.is_active=not submission.is_active
        submission.save()

        return Response(
            {
                "message":"Submission Status updated successfully.",
                "is_active":submission.is_active
            },
            status=status.HTTP_200_OK
        )

# Document upload API - Student User
class DocumentUploadAPIView(APIView):
    permission_classes = [IsStudentUser]
    serializer_class = stage5_serializers.DocumentUploadSerializer

    def post(self, request):

        serializer = self.serializer_class(data=request.data)

        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

        submission = serializer.validated_data.get('submission')
        file = serializer.validated_data.get('file')

        student = request.user

        student_batch = StudentBatch.objects.filter(
            enrollment_id=student.enrollment_id
        ).first()

        if not student_batch:
            return Response(
                {"message": "Student batch not found"},
                status=status.HTTP_400_BAD_REQUEST
            )

        group_student = GroupStudents.objects.filter(
            student_batch_link=student_batch
        ).select_related('group').first()

        if not group_student:
            return Response(
                {"message": "Student is not assigned to any group"},
                status=status.HTTP_400_BAD_REQUEST
            )

        group = group_student.group

        if not submission.is_active:
            return Response(
                {"message": "Submission is not active"},
                status=status.HTTP_400_BAD_REQUEST
            )

        latest_doc = ProjectDocument.objects.filter(
            submission=submission,
            group=group,
            is_latest=True
        ).first()

        if latest_doc:
            latest_doc.is_latest = False
            latest_doc.save()
            version = latest_doc.version + 1
        else:
            version = 1

        document = ProjectDocument.objects.create(
            submission=submission,
            group=group,
            version=version,
            file=file,
            status="submitted",
            is_latest=True,
            uploaded_by=request.user
        )

        return Response(
            {
                "message": "Document uploaded successfully",
                "version": document.version,
                "document_id": document.id
            },
            status=status.HTTP_201_CREATED
        )

        