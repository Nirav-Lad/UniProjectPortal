from rest_framework.serializers import ValidationError,ModelSerializer
from ..models import SubmissionWindow,ProjectDocument
import os
from django.core.exceptions import ValidationError

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
            data.pop('is_active',None)
            data.pop('batch',None)
            data.pop('updated_on',None)

        return data

# PUT / PATCH request serializer - for updating the submissions
class SubmissionWindowUpdateSerializer(ModelSerializer):

    class Meta:
        model = SubmissionWindow
        fields = [
            'name',
            'description',
            'submission_start',
            'submission_end',
        ]

    def validate(self, data):
        start = data.get('submission_start')
        end = data.get('submission_end')

        if start is None:
            start = self.instance.submission_start
        if end is None:
            end = self.instance.submission_end

        if start >= end:
            raise ValidationError("Submission end time must be greater than start time")

        return data
    
class DocumentUploadSerializer(ModelSerializer):

    class Meta:
        model=ProjectDocument
        fields=[
            'submission',
            'group',
            'file',
        ]

    def validate_file(self,value):
        ext=os.path.splitext(value.name[1]).lower()
        allowed_extensions=['.pdf','.doc','.docx']
        if ext not in allowed_extensions:
            raise ValidationError(f"File extension {ext} is not allowed.")
        return value
    