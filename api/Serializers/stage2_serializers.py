import datetime
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from ..models import (Guide,GuideExpertise,Expertise,GuideProjectInterest,GroupFormation)
from django.contrib.auth.hashers import make_password
from django.core.exceptions import ObjectDoesNotExist
from django.db import transaction
import random

class GuideSetupSerializer(serializers.ModelSerializer):

    expertise_names = serializers.ListField(
        child=serializers.CharField(), write_only=True, required=False
    )

    class Meta:
        model = Guide
        fields = ['mobile_no', 'expertise_names']

    def update(self, instance, validated_data):
        expertise_names = validated_data.pop('expertise_names', [])

        # Update mobile number
        instance.mobile_no = validated_data.get('mobile_no', instance.mobile_no)
        instance.save()

        # Update expertise (reset then add new ones)
        if expertise_names:
            GuideExpertise.objects.filter(guide=instance).delete()
            for name in expertise_names:
                expertise_obj, _ = Expertise.objects.get_or_create(
                    title=name.strip(),
                    defaults={"description": ""}  # description optional
                )
                GuideExpertise.objects.create(guide=instance, expertise=expertise_obj)

        return instance

class GuidePrioritySerializer(serializers.Serializer):
    group = serializers.IntegerField()
    priority = serializers.ChoiceField(choices=GuideProjectInterest.Priority.choices)

    def validate_group(self, value):
        if not GroupFormation.objects.filter(id=value).exists():
            raise serializers.ValidationError("Invalid group ID")
        return value
