import datetime
from rest_framework import serializers
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from .models import Batch, UserMaster
from django.contrib.auth.hashers import make_password


class UserLoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password_or_otp = serializers.CharField(write_only=True) 

    def validate(self, data):
        email = data.get("email")
        password_or_otp = data.get("password_or_otp")

        try:
            user = UserMaster.objects.get(email=email)
        except UserMaster.DoesNotExist:
            raise serializers.ValidationError("Invalid email or password")

        if not user.is_active:
            raise serializers.ValidationError("Account is disabled")

        # Detect First Login using `last_login`
        if user.usertype == "Student" and user.last_login is None:
            if password_or_otp == user.otp:  
                return {
                    "user": user,
                    "require_password_change": True,
                    "message": "OTP verified. Please set your password."
                }
            else:
                raise serializers.ValidationError("Invalid OTP")

        # If password is set, authenticate using password
        user = authenticate(email=email, password=password_or_otp)
        if user:
            return {
                "user": user,
                "require_password_change": False
            }

        raise serializers.ValidationError("Invalid email or password")

    def get_tokens(self, user):
        refresh = RefreshToken.for_user(user)
        return {
            "refresh": str(refresh),
            "access": str(refresh.access_token),
        } 
# ------------------------------------------------------------
class SetPasswordSerializer(serializers.Serializer):
    password = serializers.CharField(write_only=True, min_length=6)

    def validate(self, data):
        user = self.context["request"].user

        if user.last_login is not None:
            raise serializers.ValidationError("Password has already been set.")

        return data

    def save(self, **kwargs):
        user = self.context["request"].user
        user.password = make_password(self.validated_data["password"], hasher="argon2")  
        user.last_login = datetime.datetime.now()
        user.save()
        return user
# ------------------------------------------------------------
class BatchSerializer(serializers.ModelSerializer):
    class Meta:
        model = Batch
        fields = ['batch_id', 'batch_name', 'created_by', 'created_on']
        read_only_fields = ['batch_id', 'created_by', 'created_on']  # Auto-generated fields

    def create(self, validated_data):
        request = self.context.get('request')
        if request and hasattr(request, 'user'):
            validated_data['created_by'] = request.user
        return super().create(validated_data)