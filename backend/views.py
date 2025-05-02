from django.db.models import Sum
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from backend.auth import EmailAuthBackend
from .jwt_utils import get_user_from_token, verify_token, generate_token
from .models import User, Timesheet, Project, UserProject
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import TokenError
from django.contrib.auth import get_user_model, authenticate
from .serializers import (
    UserSerializer, 
    LoginSerializer, 
    TimesheetSerializer,
    ProjectSerializer,
    UserProjectSerializer,
    MyTokenObtainPairSerializer
)
import jwt
import base64
import json
import logging

logger = logging.getLogger(__name__)

def debug_token(token_str):
    """Inspect and debug a JWT token without validation"""
    try:
        parts = token_str.split('.')
        if len(parts) != 3:
            return {"error": "Not a valid JWT format (should have 3 parts)"}
        def decode_part(part):
            padding = '=' * (4 - len(part) % 4)
            return json.loads(base64.b64decode(part + padding).decode('utf-8'))
            
        header = decode_part(parts[0])
        payload = decode_part(parts[1])
        
        return {
            "header": header,
            "payload": payload,
            "is_valid_format": True
        }
    except Exception as e:
        logger.error(f"Token debug failed: {str(e)}")
        return {"error": f"Failed to decode token: {str(e)}"}

def get_user_from_request(request):
    """Extract and return the user from the Authorization token"""
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    
    if not auth_header or not auth_header.startswith('Bearer '):
        return None

    token = auth_header.split(' ')[1]

    try:
        try:
            from django.conf import settings
            payload = jwt.decode(
                token,
                settings.SIMPLE_JWT['SIGNING_KEY'],
                algorithms=['HS256'],
                options={'verify_exp': True}
            )
            user_id = payload.get('sub') or payload.get('user_id')
            if not user_id:
                return None
            User = get_user_model()
            return User.objects.get(id=user_id)
            
        except Exception:
            user = get_user_from_token(token)
            return user
            
    except Exception:
        try:
            User = get_user_model()
            token_obj = AccessToken(token)
            user_id = token_obj.payload.get('user_id')
            if user_id:
                return User.objects.get(id=user_id)
        except Exception:
            return None

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        
        if not serializer.is_valid():
            return Response({
                "status": "error",
                "code": "invalid_input",
                "errors": serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)

        try:
            email = serializer.validated_data['email']
            password = serializer.validated_data['password']
            
            user = authenticate(
                request,
                email=email,
                password=password,
                backend='backend.auth.EmailAuthBackend'
            )
            
            if user is None:
                User = get_user_model()
                try:
                    db_user = User.objects.get(email=email)
                    if not db_user.is_active:
                        return Response({
                            "status": "error",
                            "code": "account_inactive",
                            "message": "Account is inactive"
                        }, status=status.HTTP_403_FORBIDDEN)
                        
                    return Response({
                        "status": "error",
                        "code": "invalid_credentials",
                        "message": "Invalid password"
                    }, status=status.HTTP_401_UNAUTHORIZED)
                    
                except User.DoesNotExist:
                    return Response({
                        "status": "error",
                        "code": "user_not_found",
                        "message": "No user with this email exists"
                    }, status=status.HTTP_404_NOT_FOUND)

            access_token = generate_token(user.id, 'access')
            refresh_token = generate_token(user.id, 'refresh')
            
            return Response({
                "status": "success",
                "user": UserSerializer(user).data,
                "access_token": access_token,
                "refresh_token": refresh_token
            })
                
        except Exception as e:
            logger.error(f"Login error: {str(e)}")
            return Response({
                "status": "error",
                "code": "server_error",
                "message": "Internal server error"
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            try:
                payload = verify_token(refresh_token)
                
                if payload.get('type') != 'refresh':
                    return Response({'error': 'Invalid token type - not a refresh token'}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                
                user_id = payload.get('sub', payload.get('user_id'))
                if not user_id:
                    return Response({'error': 'Invalid token - no user ID'}, 
                                    status=status.HTTP_400_BAD_REQUEST)
                    
                access_token = generate_token(user_id, 'access')
                return Response({'access_token': access_token})
                
            except Exception as custom_error:
                from rest_framework_simplejwt.tokens import RefreshToken
                try:
                    refresh = RefreshToken(refresh_token)
                    return Response({
                        'access_token': str(refresh.access_token),
                    })
                except Exception:
                    raise custom_error
                
        except Exception as e:
            logger.error(f"Refresh token error: {str(e)}")
            return Response({'error': 'Invalid refresh token'}, status=status.HTTP_401_UNAUTHORIZED)

# Project API Views
class ProjectListCreateView(APIView):
    """List all projects or create a new project"""

    def get(self, request):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        # Get projects owned by the user
        owned_projects = Project.objects.filter(owner=user)
        
        # Get projects the user is assigned to via UserProject
        assigned_projects = Project.objects.filter(userproject__user=user)
        
        # Combine both querysets (removing duplicates)
        all_projects = (owned_projects | assigned_projects).distinct()
        
        serializer = ProjectSerializer(all_projects, many=True)
        return Response(serializer.data)

    def post(self, request):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
            
        # Set the current user as owner
        request.data['owner'] = user.id
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            project = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ProjectDetailView(APIView):
    """Retrieve, update, or delete a project instance"""

    def get_object(self, pk, user):
        try:
            # Check if user owns or is assigned to this project
            project = Project.objects.get(pk=pk)
            if project.owner == user or UserProject.objects.filter(user=user, project=project).exists():
                return project
            return None
        except Project.DoesNotExist:
            return None
    
    def get(self, request, pk):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        project = self.get_object(pk, user)
        if not project:
            return Response({"error": "Project not found or access denied"}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        return Response(ProjectSerializer(project).data)
    
    def patch(self, request, pk):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        project = self.get_object(pk, user)
        if not project:
            return Response({"error": "Project not found or access denied"}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        # Only allow update if user is the owner
        if project.owner != user:
            return Response({"error": "Only the project owner can update project details"}, 
                           status=status.HTTP_403_FORBIDDEN)
            
        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        project = self.get_object(pk, user)
        if not project:
            return Response({"error": "Project not found or access denied"}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        # Only allow delete if user is the owner
        if project.owner != user:
            return Response({"error": "Only the project owner can delete the project"}, 
                           status=status.HTTP_403_FORBIDDEN)
            
        project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# UserProject API Views
class UserProjectListCreateView(APIView):
    """List all user-project assignments or create a new assignment"""

    def get(self, request):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        # Filter by user or project if specified
        project_id = request.query_params.get('project_id')
        user_id = request.query_params.get('user_id')
        
        # Base queryset - only show assignments for projects the user owns or is assigned to
        owned_projects = Project.objects.filter(owner=user)
        queryset = UserProject.objects.filter(user=user) | UserProject.objects.filter(project__in=owned_projects)
        
        if project_id:
            queryset = queryset.filter(project_id=project_id)
        
        if user_id:
            queryset = queryset.filter(user_id=user_id)
            
        queryset = queryset.distinct()
        
        serializer = UserProjectSerializer(queryset, many=True)
        return Response(serializer.data)

    def post(self, request):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Check if the user has permission to add users to this project
        project_id = request.data.get('project')
        try:
            project = Project.objects.get(id=project_id)
            if project.owner != user:
                return Response(
                    {"error": "Only the project owner can add users to this project"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except Project.DoesNotExist:
            return Response({"error": "Project not found"}, status=status.HTTP_404_NOT_FOUND)
            
        serializer = UserProjectSerializer(data=request.data)
        if serializer.is_valid():
            user_project = serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class UserProjectDetailView(APIView):
    """Retrieve, update, or delete a user-project assignment"""

    def get_object(self, pk, user):
        try:
            user_project = UserProject.objects.get(pk=pk)
            # User can view/modify if they are the user in the assignment or the project owner
            if user_project.user == user or user_project.project.owner == user:
                return user_project
            return None
        except UserProject.DoesNotExist:
            return None
    
    def get(self, request, pk):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        user_project = self.get_object(pk, user)
        if not user_project:
            return Response({"error": "User-Project assignment not found or access denied"}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        return Response(UserProjectSerializer(user_project).data)
    
    def delete(self, request, pk):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        user_project = self.get_object(pk, user)
        if not user_project:
            return Response({"error": "User-Project assignment not found or access denied"}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        # Only project owner can remove users
        if user_project.project.owner != user:
            return Response({"error": "Only the project owner can remove users from the project"}, 
                           status=status.HTTP_403_FORBIDDEN)
            
        user_project.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

# Timesheet API Views
class TimesheetListCreateView(APIView):
    """List all timesheets or create a new timesheet"""

    def get(self, request):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        # Get all user_projects for the current user
        user_projects = UserProject.objects.filter(user=user)
        
        # Get all timesheets for these user_projects
        timesheets = Timesheet.objects.filter(user_project__in=user_projects)
        
        # Apply filters if specified
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        work_type = request.query_params.get('work_type')
        project_id = request.query_params.get('project_id')
        
        if month and year:
            try:
                month = int(month)
                year = int(year)
                timesheets = timesheets.filter(date__month=month, date__year=year)
            except ValueError:
                pass

        if work_type:
            timesheets = timesheets.filter(work_type=work_type)
            
        if project_id:
            timesheets = timesheets.filter(user_project__project_id=project_id)

        serializer = TimesheetSerializer(timesheets, many=True)
        total_duration = timesheets.aggregate(total=Sum('duration'))['total'] or 0
        leave_days = timesheets.filter(work_type__in=['half_day_leave', 'full_day_leave']).count()

        return Response({
            'timesheets': serializer.data,
            'statistics': {
                'total_duration': total_duration,
                'leave_days': leave_days
            }
        })

    def post(self, request):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)
        
        # Verify the user_project belongs to the current user
        user_project_id = request.data.get('user_project')
        try:
            user_project = UserProject.objects.get(id=user_project_id)
            if user_project.user.id != user.id:
                return Response(
                    {"error": "You can only create timesheets for your own project assignments"}, 
                    status=status.HTTP_403_FORBIDDEN
                )
        except UserProject.DoesNotExist:
            return Response({"error": "User-Project assignment not found"}, 
                          status=status.HTTP_404_NOT_FOUND)
            
        serializer = TimesheetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TimesheetDetailView(APIView):
    """Retrieve, update, or delete a timesheet instance"""

    def get_object(self, pk, user):
        try:
            timesheet = Timesheet.objects.get(pk=pk)
            # User can only access their own timesheets
            if timesheet.user_project.user == user:
                return timesheet
            return None
        except Timesheet.DoesNotExist:
            return None
    
    def get(self, request, pk):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        timesheet = self.get_object(pk, user)
        if not timesheet:
            return Response({"error": "Timesheet not found or access denied"}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        return Response(TimesheetSerializer(timesheet).data)
    
    def patch(self, request, pk):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        timesheet = self.get_object(pk, user)
        if not timesheet:
            return Response({"error": "Timesheet not found or access denied"}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        # If user_project is being changed, verify it belongs to the current user
        user_project_id = request.data.get('user_project')
        if user_project_id:
            try:
                user_project = UserProject.objects.get(id=user_project_id)
                if user_project.user.id != user.id:
                    return Response(
                        {"error": "You can only assign timesheets to your own project assignments"}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            except UserProject.DoesNotExist:
                return Response({"error": "User-Project assignment not found"}, 
                              status=status.HTTP_404_NOT_FOUND)
        
        serializer = TimesheetSerializer(timesheet, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        user = get_user_from_request(request)
        if not user:
            return Response({"error": "Authentication required"}, status=status.HTTP_401_UNAUTHORIZED)

        timesheet = self.get_object(pk, user)
        if not timesheet:
            return Response({"error": "Timesheet not found or access denied"}, 
                           status=status.HTTP_404_NOT_FOUND)
        
        timesheet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class TokenTestView(APIView):
    """Test view for token authentication"""
    
    def get(self, request):
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        if not auth_header or not auth_header.startswith('Bearer '):
            return Response({"error": "Authorization header required"}, status=status.HTTP_401_UNAUTHORIZED)
                           
        token = auth_header.split(' ')[1]
        token_debug = debug_token(token)
        user = get_user_from_request(request)
        
        if not user:
            return Response({
                "error": "Authentication failed",
                "token_debug": token_debug,
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        return Response({
            "authenticated": True,
            "user_id": user.id,
            "username": user.name,
            "email": user.email
        })