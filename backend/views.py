from django.db.models import Sum
from rest_framework import status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework.permissions import AllowAny
from .jwt_utils import get_user_from_token, verify_token, generate_token
from .models import User, Timesheet, HolidayWeekend
from .serializers import (
    UserSerializer, 
    LoginSerializer, 
    TimesheetSerializer, 
    HolidayWeekendSerializer,
    MyTokenObtainPairSerializer
)
import jwt
import base64
import json

def debug_token(token_str):
    """Inspect and debug a JWT token without validation"""
    try:
        # Split the token
        parts = token_str.split('.')
        if len(parts) != 3:
            return {"error": "Not a valid JWT format (should have 3 parts)"}
            
        # Decode header and payload (without verification)
        # Add padding if needed
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
        return {"error": f"Failed to decode token: {str(e)}"}

def get_user_from_request(request):
    """Extract and return the user from the Authorization token with detailed debugging"""
    # Use the debug_token function already defined in this file
    
    auth_header = request.META.get('HTTP_AUTHORIZATION', '')
    print("DEBUG: AUTH HEADER ->", auth_header)
    
    if not auth_header or not auth_header.startswith('Bearer '):
        print("DEBUG: Invalid Authorization header format")
        return None

    token = auth_header.split(' ')[1]
    print("DEBUG: Extracted token ->", token)
    
    # Debug the token structure without validation
    token_debug = debug_token(token)
    print("DEBUG: Token structure:", json.dumps(token_debug, indent=2))
    
    # Try with our custom JWT implementation first
    try:
        # Directly decode and verify the token using PyJWT
        try:
            from django.conf import settings
            payload = jwt.decode(
                token,
                settings.SIMPLE_JWT['SIGNING_KEY'],
                algorithms=['HS256'],
                options={'verify_exp': True}
            )
            print("DEBUG: PyJWT decoded payload:", payload)
            
            # Extract user ID from payload
            user_id = None
            if 'sub' in payload:
                user_id = payload['sub']
            elif 'user_id' in payload:
                user_id = payload['user_id']
                
            if not user_id:
                print("DEBUG: No user ID found in token payload")
                return None
                
            # Get the user
            from django.contrib.auth import get_user_model
            User = get_user_model()
            user = User.objects.get(id=user_id)
            print("DEBUG: User retrieved:", user)
            return user
            
        except Exception as jwt_error:
            print(f"DEBUG: PyJWT decode failed: {str(jwt_error)}")
            # Continue to SimpleJWT method
            
        # Try with our custom get_user_from_token
        user = get_user_from_token(token)
        print("DEBUG: Custom token validated successfully, user ->", user)
        return user
        
    except Exception as custom_error:
        print(f"DEBUG: Custom token validation failed: {str(custom_error)}")
        
        # If custom validation failed, try with SimpleJWT
        try:
            from rest_framework_simplejwt.tokens import AccessToken
            from rest_framework_simplejwt.exceptions import TokenError
            from django.contrib.auth import get_user_model
            
            User = get_user_model()
            
            # Try with SimpleJWT
            token_obj = AccessToken(token)
            user_id = token_obj.payload.get('user_id')
            print(f"DEBUG: SimpleJWT payload: {token_obj.payload}")
            
            if user_id:
                user = User.objects.get(id=user_id)
                print("DEBUG: SimpleJWT token valid, user ->", user)
                return user
            else:
                print("DEBUG: SimpleJWT token doesn't contain user_id")
                
        except Exception as simplejwt_error:
            print(f"DEBUG: SimpleJWT validation failed: {str(simplejwt_error)}")
            
        return None

class MyTokenObtainPairView(TokenObtainPairView):
    serializer_class = MyTokenObtainPairSerializer

class LoginView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = LoginSerializer(data=request.data)
        if serializer.is_valid():
            try:
                user = serializer.validated_data['user']
                
                # Generate tokens with our enhanced generate_token function
                access_token = generate_token(user.id, 'access')
                refresh_token = generate_token(user.id, 'refresh')
                
                # Let's add some debug information to verify token structure
                # Use the debug_token function already defined in this file
                token_debug = debug_token(access_token)
                print("DEBUG: Generated access token:", json.dumps(token_debug, indent=2))

                return Response({
                    'user': UserSerializer(user).data,
                    'access_token': access_token,
                    'refresh_token': refresh_token
                })
            except Exception as e:
                print(f"DEBUG: Login exception: {str(e)}")
                return Response({'error': str(e)}, status=500)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class RefreshTokenView(APIView):
    permission_classes = [AllowAny]
    
    def post(self, request):
        refresh_token = request.data.get('refresh_token')
        
        if not refresh_token:
            return Response({'error': 'Refresh token is required'}, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # First try to validate with our custom jwt_utils
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
                # If our custom verification fails, try with SimpleJWT
                from rest_framework_simplejwt.tokens import RefreshToken
                try:
                    refresh = RefreshToken(refresh_token)
                    return Response({
                        'access_token': str(refresh.access_token),
                    })
                except Exception as simplejwt_error:
                    # Both methods failed, raise the original error
                    raise custom_error
                
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_401_UNAUTHORIZED)

class TimesheetListCreateView(APIView):
    """List all timesheets or create a new timesheet"""

    def get(self, request):
        user = get_user_from_request(request)

        if not user:
            return Response({"error": "Authentication required or invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        timesheets = Timesheet.objects.filter(user=user)

        # Optional filtering by date (month and year)
        month = request.query_params.get('month')
        year = request.query_params.get('year')
        work_type = request.query_params.get('work_type')  # optional filter by work type
        
        if month and year:
            try:
                month = int(month)
                year = int(year)
                timesheets = timesheets.filter(date__month=month, date__year=year)
            except ValueError:
                pass

        if work_type:
            timesheets = timesheets.filter(work_type=work_type)

        serializer = TimesheetSerializer(timesheets, many=True)

        # Calculate statistics
        total_duration = timesheets.aggregate(total=Sum('duration'))['total'] or 0
        leave_days = timesheets.filter(work_type__in=['half_day_leave', 'full_day_leave']).count()

        response_data = {
            'timesheets': serializer.data,
            'statistics': {
                'total_duration': total_duration,
                'leave_days': leave_days
            }
        }

        return Response(response_data)

    def post(self, request):
        user = get_user_from_request(request)

        if not user:
            return Response({"error": "Authentication required or invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        request.data['user'] = user.id  # Automatically set the user based on the token

        serializer = TimesheetSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class TimesheetDetailView(APIView):
    """Retrieve, update, or delete a timesheet instance"""

    def get_object(self, pk, user):
        try:
            return Timesheet.objects.get(id=pk, user=user)
        except Timesheet.DoesNotExist:
            return None
    
    def get(self, request, pk):
        user = get_user_from_request(request)

        if not user:
            return Response({"error": "Authentication required or invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        timesheet = self.get_object(pk, user)
        if not timesheet:
            return Response({"error": "Timesheet not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = TimesheetSerializer(timesheet)
        return Response(serializer.data)
    
    def patch(self, request, pk):
        user = get_user_from_request(request)

        if not user:
            return Response({"error": "Authentication required or invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        timesheet = self.get_object(pk, user)
        if not timesheet:
            return Response({"error": "Timesheet not found"}, status=status.HTTP_404_NOT_FOUND)
        
        serializer = TimesheetSerializer(timesheet, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        user = get_user_from_request(request)

        if not user:
            return Response({"error": "Authentication required or invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        timesheet = self.get_object(pk, user)
        if not timesheet:
            return Response({"error": "Timesheet not found"}, status=status.HTTP_404_NOT_FOUND)
        
        timesheet.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)

class HolidayWeekendListView(APIView):
    """List all holidays and weekends"""

    def get(self, request):
        user = get_user_from_request(request)

        if not user:
            return Response({"error": "Authentication required or invalid token"}, status=status.HTTP_401_UNAUTHORIZED)

        holidays = HolidayWeekend.objects.all()

        # Optional filtering by date
        month = request.query_params.get('month')
        year = request.query_params.get('year')

        if month and year:
            try:
                month = int(month)
                year = int(year)
                holidays = holidays.filter(date__month=month, date__year=year)
            except ValueError:
                pass

        serializer = HolidayWeekendSerializer(holidays, many=True)
        return Response(serializer.data)

class TokenTestView(APIView):
    """Test view to debug token authentication"""
    
    def get(self, request):
        # Let's print all headers for debugging
        headers = {k: v for k, v in request.META.items() if k.startswith('HTTP_')}
        print("DEBUG: All headers:", json.dumps(headers, indent=2))
        
        # Check for authentication header
        auth_header = request.META.get('HTTP_AUTHORIZATION', '')
        
        if not auth_header:
            return Response({"error": "No Authorization header present"}, 
                           status=status.HTTP_401_UNAUTHORIZED)
                           
        if not auth_header.startswith('Bearer '):
            return Response({"error": "Authorization header must start with 'Bearer '"}, 
                           status=status.HTTP_401_UNAUTHORIZED)
                           
        token = auth_header.split(' ')[1]
        
        # Debug token without validation
        # Use the debug_token function already defined in this file
        token_debug = debug_token(token)
        
        user = get_user_from_request(request)
        
        if not user:
            return Response({
                "error": "Authentication failed",
                "token_debug": token_debug,
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        # Authentication successful
        return Response({
            "authenticated": True,
            "user_id": user.id,
            "username": user.name,
            "email": user.email,
            "token_debug": token_debug,
        })