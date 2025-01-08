from django.test import TestCase
from django.contrib.auth import get_user_model
from rest_framework.test import APITestCase
from rest_framework import status
from .models import Contact, SpamReport

User = get_user_model()

class UserModelTests(TestCase):
    def setUp(self):
        self.user_data = {
            'username': '+1234567890',
            'phone_number': '+1234567890',
            'first_name': 'Test',
            'password': 'testpass123'
        }
        self.user = User.objects.create_user(**self.user_data)

    def test_user_creation(self):
        self.assertTrue(isinstance(self.user, User))
        self.assertEqual(self.user.phone_number, self.user_data['phone_number'])

class ContactModelTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='+1234567890',
            phone_number='+1234567890',
            first_name='Test',
            password='testpass123'
        )
        self.contact_data = {
            'user': self.user,
            'name': 'Test Contact',
            'phone_number': '+9876543210'
        }
        self.contact = Contact.objects.create(**self.contact_data)

    def test_contact_creation(self):
        self.assertTrue(isinstance(self.contact, Contact))
        self.assertEqual(self.contact.name, self.contact_data['name'])

class APITests(APITestCase):
    def setUp(self):
        self.user_data = {
            'username': '+1234567890',
            'phone_number': '+1234567890',
            'first_name': 'Test',
            'password': 'testpass123'
        }
        self.user = User.objects.create_user(**self.user_data)
        self.client.force_authenticate(user=self.user)

    def test_user_registration(self):
        url = '/api/users/'
        data = {
            'phone_number': '+9876543210',
            'first_name': 'New',
            'password': 'newpass123'
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED)

    def test_spam_report_creation(self):
        url = '/api/reports/'
        data = {
            'reported_number': '+9876543210',
            'report_type': 'SPAM',
            'details': 'Test spam report',
            'severity': 1
        }
        response = self.client.post(url, data, format='json')
        self.assertEqual(response.status_code, status.HTTP_201_CREATED) 