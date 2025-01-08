from rest_framework import serializers
from django.db.models import Count
from .models import User, Contact, SpamReport

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'username', 'phone_number', 'email')
        extra_kwargs = {
            'email': {'required': False},
            'username': {'required': True},
            'phone_number': {'required': True}
        }

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)

    class Meta:
        model = User
        fields = ('username', 'phone_number', 'email', 'password')
        extra_kwargs = {
            'email': {'required': False},
            'username': {'required': True},
            'phone_number': {'required': True}
        }

    def create(self, validated_data):
        user = User.objects.create_user(**validated_data)
        return user

class ContactSerializer(serializers.ModelSerializer):
    spam_likelihood = serializers.SerializerMethodField()

    class Meta:
        model = Contact
        fields = ('id', 'name', 'phone_number', 'spam_likelihood')

    def get_spam_likelihood(self, obj):
        total_users = User.objects.count()
        spam_count = SpamReport.objects.filter(phone_number=obj.phone_number).count()
        if total_users == 0:
            return 0
        return (spam_count / total_users) * 100

class SearchResultSerializer(serializers.ModelSerializer):
    name = serializers.CharField()
    phone_number = serializers.CharField()
    spam_likelihood = serializers.FloatField()
    email = serializers.EmailField(required=False)

    class Meta:
        model = Contact
        fields = ('name', 'phone_number', 'spam_likelihood', 'email')

class SpamReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = SpamReport
        fields = ('id', 'phone_number', 'created_at')
        read_only_fields = ('created_at',) 