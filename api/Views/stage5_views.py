from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status
from ..models import SubmissionWindow,StudentBatch,Batch
from api.serializers import stage5_serializers

class SubmissionWindowAPIView(APIView):
    permission_classes=[IsAuthenticated]

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
