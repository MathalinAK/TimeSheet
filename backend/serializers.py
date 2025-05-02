from rest_framework import serializers
from uuid import uuid4
from .models import User, Timesheet, Project, UserProject
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
        # This is the correct way to create a user with hashed password
        user = User.objects.create_user(
            email=validated_data['email'],
            name=validated_data['name'],
            password=validated_data['password']
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

class ProjectSerializer(serializers.ModelSerializer):
    owner_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Project
        fields = ('id', 'name', 'description', 'owner', 'owner_name')
        
    def get_owner_name(self, obj):
        return obj.owner.name if obj.owner else None

class UserProjectSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    
    class Meta:
        model = UserProject
        fields = ('id', 'user', 'project', 'user_name', 'project_name')
        
    def get_user_name(self, obj):
        return obj.user.name if obj.user else None
        
    def get_project_name(self, obj):
        return obj.project.name if obj.project else None

class TimesheetSerializer(serializers.ModelSerializer):
    user_name = serializers.SerializerMethodField()
    project_name = serializers.SerializerMethodField()
    
    class Meta:
        model = Timesheet
        fields = ('id', 'user_project', 'date', 'task_name', 'description', 'duration', 
                  'work_type', 'user_name', 'project_name')
    
    def get_user_name(self, obj):
        return obj.user_project.user.name if obj.user_project and obj.user_project.user else None
        
    def get_project_name(self, obj):
        return obj.user_project.project.name if obj.user_project and obj.user_project.project else None