from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q, Count, F
from django.contrib.auth import get_user_model
from .models import Contact, SpamReport
from .serializers import (
    UserSerializer, UserRegistrationSerializer, ContactSerializer,
    SearchResultSerializer, SpamReportSerializer
)

User = get_user_model()

class RegistrationView(APIView):
    def post(self, request):
        serializer = UserRegistrationSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class SearchView(APIView):
    permission_classes = [IsAuthenticated]

    def get_spam_likelihood(self, phone_number):
        total_users = User.objects.count()
        spam_count = SpamReport.objects.filter(phone_number=phone_number).count()
        return (spam_count / total_users) * 100 if total_users > 0 else 0

    def get(self, request):
        query = request.query_params.get('q', '')
        search_type = request.query_params.get('type', 'name')
        
        if not query:
            return Response({"error": "Query parameter 'q' is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)

        results = []
        if search_type == 'name':
            # First get exact matches
            contacts = Contact.objects.filter(name__istartswith=query)
            # Then get partial matches
            contacts = contacts.union(
                Contact.objects.filter(name__icontains=query)
                .exclude(name__istartswith=query)
            )
        else:  # phone search
            registered_user = User.objects.filter(phone_number=query).first()
            if registered_user:
                # If registered user found, only return that
                results.append({
                    'name': registered_user.username,
                    'phone_number': registered_user.phone_number,
                    'spam_likelihood': self.get_spam_likelihood(query),
                    'email': registered_user.email if Contact.objects.filter(
                        user=request.user, phone_number=query).exists() else None
                })
                return Response(results)
            else:
                # Otherwise return all matching contacts
                contacts = Contact.objects.filter(phone_number=query)

        for contact in contacts:
            result = {
                'name': contact.name,
                'phone_number': contact.phone_number,
                'spam_likelihood': self.get_spam_likelihood(contact.phone_number),
            }
            
            # Add email only if the contact is a registered user and the searcher is in their contacts
            user = User.objects.filter(phone_number=contact.phone_number).first()
            if user and Contact.objects.filter(user=user, phone_number=request.user.phone_number).exists():
                result['email'] = user.email
            
            results.append(result)

        return Response(results)

class SpamViewSet(viewsets.ModelViewSet):
    serializer_class = SpamReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SpamReport.objects.filter(reported_by=self.request.user)

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)

    @action(detail=False, methods=['get'])
    def check(self, request):
        phone_number = request.query_params.get('phone_number')
        if not phone_number:
            return Response({"error": "phone_number parameter is required"}, 
                          status=status.HTTP_400_BAD_REQUEST)
        
        total_users = User.objects.count()
        spam_count = SpamReport.objects.filter(phone_number=phone_number).count()
        
        return Response({
            'phone_number': phone_number,
            'spam_likelihood': (spam_count / total_users) * 100 if total_users > 0 else 0,
            'total_reports': spam_count
        }) 