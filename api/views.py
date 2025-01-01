from .serializers import CreateBatchSerializer
from .models import Batch
from rest_framework.generics import ListCreateAPIView


class BatchCreateList(ListCreateAPIView):
    queryset=Batch.objects.all()
    serializer_class=CreateBatchSerializer
    
