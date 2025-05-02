from django.contrib import admin
from .models import User, Timesheet, HolidayWeekend
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
@admin.register(User)
class UserAdmin(BaseUserAdmin):  
    list_display = ('id', 'name', 'email', 'is_staff')
    search_fields = ('name', 'email')
    list_filter = ('is_staff', 'is_active')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('name',)}),
        ('Permissions', {'fields': ('is_active', 'is_staff', 'is_superuser')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'name', 'password1', 'password2'),
        }),
    )

@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ('id', 'get_user', 'get_project', 'date', 'duration', 'work_type')
    list_filter = ('date', 'work_type', 'user_project__user')
    search_fields = (
        'user_project__user__name',
        'user_project__user__email',
        'user_project__project__name',
        'task_name'
    )
    
    def get_user(self, obj):
        return f"{obj.user_project.user.name} ({obj.user_project.user.email})"
    get_user.short_description = 'User'
    get_user.admin_order_field = 'user_project__user__name'
    
    def get_project(self, obj):
        return obj.user_project.project.name
    get_project.short_description = 'Project'
    get_project.admin_order_field = 'user_project__project__name'

@admin.register(HolidayWeekend)
class HolidayWeekendAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'description')
    list_filter = ('date',)
    search_fields = ('description',)
    date_hierarchy = 'date'