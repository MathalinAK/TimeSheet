from django.urls import path
from .views import (
    MyTokenObtainPairView,
    LoginView, 
    RefreshTokenView, 
    TimesheetListCreateView,
    TimesheetDetailView,
    ProjectListCreateView,
    ProjectDetailView,
    UserProjectListCreateView,
    UserProjectDetailView,
    TokenTestView
)

urlpatterns = [
    # Auth endpoints
    path('login/', LoginView.as_view(), name='login'),
    path('refresh-token/', RefreshTokenView.as_view(), name='refresh-token'),
    path('api/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('test-token/', TokenTestView.as_view(), name='test-token'),
    
    # Project endpoints
    path('projects/', ProjectListCreateView.as_view(), name='project-list'),
    path('projects/<int:pk>/', ProjectDetailView.as_view(), name='project-detail'),
    
    # UserProject endpoints
    path('user-projects/', UserProjectListCreateView.as_view(), name='user-project-list'),
    path('user-projects/<int:pk>/', UserProjectDetailView.as_view(), name='user-project-detail'),
    
    # Timesheet endpoints
    path('timesheets/', TimesheetListCreateView.as_view(), name='timesheet-list'),
    path('timesheets/<int:pk>/', TimesheetDetailView.as_view(), name='timesheet-detail'),
]