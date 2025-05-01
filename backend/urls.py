from django.urls import path
from .views import (
    MyTokenObtainPairView,
    LoginView, 
    RefreshTokenView, 
    TimesheetListCreateView,
    TimesheetDetailView,
    HolidayWeekendListView,
    TokenTestView
)

urlpatterns = [
    path('login/', LoginView.as_view(), name='login'),
    path('refresh-token/', RefreshTokenView.as_view(), name='refresh-token'),
    path('api/token/', MyTokenObtainPairView.as_view(), name='token_obtain_pair'),
    
    path('test-token/', TokenTestView.as_view(), name='test-token'),
    
    path('timesheets/', TimesheetListCreateView.as_view(), name='timesheet-list'),
    path('timesheets/<int:pk>/', TimesheetDetailView.as_view(), name='timesheet-detail'),
    
    path('holidays/', HolidayWeekendListView.as_view(), name='holiday-list'),
]