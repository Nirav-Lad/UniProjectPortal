from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from .serializers import UserLoginSerializer,BatchSerializer
from rest_framework.permissions import IsAuthenticated

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
