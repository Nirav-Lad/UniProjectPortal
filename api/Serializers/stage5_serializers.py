from rest_framework.serializers import ValidationError,ModelSerializer
from ..models import SubmissionWindow

# POST request serailizer - for creating a submission
class SubmissionWindowCreateSerializer(ModelSerializer):
    
    class Meta:
        model=SubmissionWindow
        fields=[
            'name',
            'description',
            'batch',
            'submission_start',
            'submission_end',
        ]

    def validate(self, data):
        start=data.get('submission_start')
        end=data.get('submission_end')

        if start and end and start>=end:
            raise ValidationError("Submission end time must be greater than start time")
        
        return data

# GET request serializer - for reading the submissions
class SubmissionWindowReadSerializer(ModelSerializer):

    class Meta:
        model=SubmissionWindow
        fields="__all__"

    def to_representation(self, instance):
        data=super().to_representation(instance)
        user=self.context.get('request').user

        if user.usertype == 'Student':
            data.pop('created_by',None)
            data.pop('created_on',None)

        return data
