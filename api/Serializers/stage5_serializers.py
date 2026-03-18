from rest_framework.serializers import ValidationError,ModelSerializer
from ..models import SubmissionWindow

class SubmissionWindowSerializer(ModelSerializer):
    
    class Meta:
        model=SubmissionWindow
        fields=[
            'id',
            'name',
            'description',
            'batch',
            'submission_start',
            'submission_end',
            'is_active',
            'created_by',
            'created_on'
        ]
        read_only_fields=['id','created_by','created_on']

    def validate(self, data):
        start=data.get('submission_start')
        end=data.get('submission_end')

        if start>=end:
            raise ValidationError("Submission end time must be greater than start time")
        
        return data
