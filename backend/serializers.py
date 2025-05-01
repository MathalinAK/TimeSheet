from rest_framework import serializers
from uuid import uuid4
from .models import User, Timesheet, HolidayWeekend
from django.contrib.auth import authenticate
from django.contrib.auth.hashers import make_password
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer

class MyTokenObtainPairSerializer(TokenObtainPairSerializer):
    @classmethod
    def get_token(cls, user):
        token = super().get_token(user)
        token['user_id'] = user.id
        token['type'] = 'access'
        token['jti'] = str(uuid4())
        return token

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'name', 'email', 'password')
        extra_kwargs = {
            'password': {'write_only': True}
        }

    def create(self, validated_data):
        user = User.objects.create(
            name=validated_data['name'],
            email=validated_data['email'],
            password=make_password(validated_data['password'])
        )
        return user

class LoginSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    user = serializers.SerializerMethodField()

    def get_user(self, obj):
        return UserSerializer(obj).data

    def validate(self, data):
        email = data.get('email')
        password = data.get('password')
        
        user = authenticate(email=email, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials")
        
        data['user'] = user
        return data

class TimesheetSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()

    class Meta:
        model = Timesheet
        fields = ('id', 'user', 'date', 'task_name', 'description', 'duration', 'work_type', 'user_name')

    def get_user_name(self, obj):
        return obj.user.name if obj.user else None

class HolidayWeekendSerializer(serializers.ModelSerializer):
    class Meta:
        model = HolidayWeekend
        fields = ('id', 'date', 'description')
