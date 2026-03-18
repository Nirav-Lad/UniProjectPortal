from rest_framework.viewsets import ModelViewSet
from ..models import SubmissionWindow
from rest_framework.permissions import IsAuthenticated
from ..utils.permissions import IsAdminUser,IsGuideUser,IsStudentUser
from ..serializers import SubmissionWindowSerializer

class SubmissionWindowViewSet(ModelViewSet):
    queryset=SubmissionWindow.objects.all().order_by('-created_on')
    serializer_class=SubmissionWindowSerializer
    permission_classes=[IsAuthenticated]

    def perform_create(self, serializer):
        serializer.save(created_by=self.request.user.id)
    
    def get_queryset(self):
        queryset=super().get_queryset()
        batch_id=self.request.query_params.get('batch_id')
        created_by=self.request.user.id

        if batch_id and created_by:
            queryset=queryset.filter(batch_id=batch_id,created_by=created_by)

        return queryset