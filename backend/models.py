from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin
from django.db import models

class UserManager(BaseUserManager):
    def create_user(self, email, name, password=None):
        if not email:
            raise ValueError("The Email field must be set")
        email = self.normalize_email(email)
        user = self.model(email=email, name=name)
        user.set_password(password)
        user.save(using=self._db)
        return user
    
    def create_superuser(self, email, name, password=None):
        user = self.create_user(email, name, password)
        user.is_superuser = True
        user.is_staff = True
        user.save(using=self._db)
        return user


class User(AbstractBaseUser, PermissionsMixin):
    name = models.CharField(max_length=100)
    email = models.EmailField(unique=True)
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['name']

    def __str__(self):
        return self.name

    class Meta:
        db_table = "user"

class Timesheet(models.Model):
    WORKTYPE_CHOICES = [
        ('working', 'Working'),
        ('weekend', 'Weekend'),
        ('holiday', 'Holiday'),
        ('half_day_leave', 'Half Day Leave'),
        ('full_day_leave', 'Full Day Leave'),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    date = models.DateField()
    task_name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    duration = models.DecimalField(max_digits=5, decimal_places=2)
    work_type = models.CharField(max_length=20, choices=WORKTYPE_CHOICES, default='working')

    def __str__(self):
        return f"Timesheet - {self.user.name} ({self.date})"

    class Meta:
        db_table = "timesheet"

class HolidayWeekend(models.Model):
    date = models.DateField()
    description = models.CharField(max_length=255)

    def __str__(self):
        return self.description

    class Meta:
        db_table = "holiday_weekend"
