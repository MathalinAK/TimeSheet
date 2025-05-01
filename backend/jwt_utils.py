import os
import uuid
from datetime import datetime, timedelta, timezone
from django.conf import settings
import jwt
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import get_user_model
from uuid import uuid4
from datetime import datetime, timedelta
from django.conf import settings
import jwt

def generate_token(user_id, token_type):
    """Generate JWT token with all required claims"""
    payload = {
        'sub': str(user_id),
        'type': token_type,
        'user_id': user_id,
        'iat': datetime.utcnow(),
        'exp': datetime.utcnow() + (
            timedelta(minutes=15) if token_type == 'access' 
            else timedelta(days=7)
        ),
        'jti': str(uuid4())  # Add unique JWT ID
    }
    return jwt.encode(
        payload,
        settings.SIMPLE_JWT['SIGNING_KEY'],
        algorithm='HS256'
    )

def verify_token(token):
    """Verify JWT token with all required claims"""
    try:
        payload = jwt.decode(
            token,
            settings.SIMPLE_JWT['SIGNING_KEY'],
            algorithms=['HS256'],
            options={
                'verify_exp': True,
                'require': ['sub', 'user_id', 'type', 'jti', 'exp', 'iat']
            }
        )
        return payload
    except Exception as e:
        raise Exception(f'Invalid token: {str(e)}')


def get_user_from_token(token):
    """Get user from token"""
    try:
        payload = verify_token(token)
        User = get_user_model()
        
        # Try with 'sub' first (our custom format)
        if 'sub' in payload:
            return User.objects.get(id=payload['sub'])
        
        # Fall back to 'user_id' (SimpleJWT format)
        elif 'user_id' in payload:
            return User.objects.get(id=payload['user_id'])
        
        raise Exception("No user identifier in token")
        
    except Exception as e:
        raise Exception(f"Failed to get user from token: {str(e)}")

def refresh_token(refresh_token_str):
    """Generate new access token from refresh token"""
    try:
        payload = verify_token(refresh_token_str)
        
        # Check if this is indeed a refresh token
        if payload.get('type') != 'refresh':
            raise Exception("Invalid token type - refresh token required")
            
        return generate_token(payload['sub'] if 'sub' in payload else payload['user_id'], 'access')
    except Exception as e:
        raise Exception(f"Refresh failed: {str(e)}")