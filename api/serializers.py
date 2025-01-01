from rest_framework import serializers
from .models import Batch

class CreateBatchSerializer(serializers.ModelSerializer):
    class Meta:
        model=Batch
        fields=['batch_id','batch_name','created_by']
