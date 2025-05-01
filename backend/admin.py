from django.contrib import admin
from .models import User, Timesheet, HolidayWeekend

@admin.register(User)
class UserAdmin(admin.ModelAdmin):
    list_display = ('id', 'name', 'email')
    search_fields = ('name', 'email')

@admin.register(Timesheet)
class TimesheetAdmin(admin.ModelAdmin):
    list_display = ['id', 'user', 'date', 'duration', 'work_type']
    list_filter = ['date', 'work_type', 'user']


@admin.register(HolidayWeekend)
class HolidayWeekendAdmin(admin.ModelAdmin):
    list_display = ('id', 'date', 'description')
    list_filter = ('date',)
    search_fields = ('description',)