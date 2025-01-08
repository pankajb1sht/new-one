from rest_framework import serializers
from django.contrib.auth import get_user_model
from .models import Contact, SpamReport

User = get_user_model()

class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('id', 'first_name', 'phone_number', 'email', 'registration_timestamp', 'last_login')
        read_only_fields = ('registration_timestamp', 'last_login')

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True)
    
    class Meta:
        model = User
        fields = ('first_name', 'phone_number', 'email', 'password')

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['phone_number'],
            first_name=validated_data['first_name'],
            phone_number=validated_data['phone_number'],
            email=validated_data.get('email', ''),
            password=validated_data['password']
        )
        return user

class ContactSerializer(serializers.ModelSerializer):
    class Meta:
        model = Contact
        fields = '__all__'
        read_only_fields = ('user', 'created_at', 'updated_at')

    def create(self, validated_data):
        validated_data['user'] = self.context['request'].user
        return super().create(validated_data)

class SpamReportSerializer(serializers.ModelSerializer):
    reporter_name = serializers.CharField(source='reporter.first_name', read_only=True)
    
    class Meta:
        model = SpamReport
        fields = ('id', 'reported_number', 'reporter', 'reporter_name', 'report_type', 
                 'details', 'evidence', 'severity', 'timestamp')
        read_only_fields = ('reporter', 'timestamp')

    def create(self, validated_data):
        validated_data['reporter'] = self.context['request'].user
        return super().create(validated_data)

class PhoneNumberSearchSerializer(serializers.Serializer):
    phone_number = serializers.CharField(max_length=15)
    name = serializers.CharField(read_only=True)
    spam_likelihood = serializers.FloatField(read_only=True)
    report_count = serializers.IntegerField(read_only=True)

class NameSearchSerializer(serializers.Serializer):
    name = serializers.CharField()
    results = PhoneNumberSearchSerializer(many=True, read_only=True) 