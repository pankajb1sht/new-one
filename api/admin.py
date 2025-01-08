from django.contrib import admin
from django.contrib.auth import get_user_model
from django.contrib.auth.admin import UserAdmin
from .models import Contact, SpamReport

User = get_user_model()

@admin.register(User)
class CustomUserAdmin(UserAdmin):
    list_display = ('phone_number', 'first_name', 'email', 'is_active', 'last_login')
    search_fields = ('phone_number', 'first_name', 'email')
    ordering = ('-last_login',)
    list_filter = ('is_active', 'is_staff', 'registration_timestamp')

@admin.register(Contact)
class ContactAdmin(admin.ModelAdmin):
    list_display = ('name', 'phone_number', 'user', 'created_at')
    search_fields = ('name', 'phone_number')
    list_filter = ('created_at',)
    raw_id_fields = ('user',)

@admin.register(SpamReport)
class SpamReportAdmin(admin.ModelAdmin):
    list_display = ('reported_number', 'reporter', 'report_type', 'severity', 'timestamp')
    list_filter = ('report_type', 'severity', 'timestamp')
    search_fields = ('reported_number', 'details')
    raw_id_fields = ('reporter',) 