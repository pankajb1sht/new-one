import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated
from rest_framework.views import APIView
from django.db.models import Q, Count, F
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError
from .models import Contact, SpamReport
from .serializers import (
    UserSerializer, UserRegistrationSerializer, ContactSerializer,
    SearchResultSerializer, SpamReportSerializer
)

logger = logging.getLogger(__name__)

User = get_user_model()

class RegistrationView(APIView):
    permission_classes = []  # Allow unauthenticated access
    authentication_classes = []  # No authentication needed for registration
    
    def post(self, request, *args, **kwargs):
        logger.info(f"Registration attempt with data: {request.data}")
        
        try:
            # Validate request data presence
            if not request.data:
                logger.error("No data provided in registration request")
                return Response(
                    {'error': 'No data provided'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Basic data validation
            required_fields = ['username', 'password', 'phone_number']
            missing_fields = [field for field in required_fields if field not in request.data]
            if missing_fields:
                logger.error(f"Missing required fields: {missing_fields}")
                return Response(
                    {
                        'error': 'Missing required fields',
                        'missing_fields': missing_fields
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if username exists
            if User.objects.filter(username=request.data.get('username')).exists():
                logger.warning(f"Username already exists: {request.data.get('username')}")
                return Response(
                    {'error': 'Username already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if phone number exists
            if User.objects.filter(phone_number=request.data.get('phone_number')).exists():
                logger.warning(f"Phone number already exists: {request.data.get('phone_number')}")
                return Response(
                    {'error': 'Phone number already registered'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = UserRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                # Create user
                try:
                    user = serializer.save()
                    logger.info(f"Successfully created user: {user.username}")
                    return Response(
                        {
                            'message': 'User created successfully',
                            'user': serializer.data
                        },
                        status=status.HTTP_201_CREATED
                    )
                except IntegrityError as e:
                    logger.error(f"Database integrity error: {str(e)}")
                    return Response(
                        {'error': 'Database integrity error occurred'},
                        status=status.HTTP_400_BAD_REQUEST
                    )
                except Exception as e:
                    logger.error(f"Error creating user: {str(e)}")
                    return Response(
                        {'error': 'Error creating user'},
                        status=status.HTTP_500_INTERNAL_SERVER_ERROR
                    )
            
            logger.error(f"Validation errors: {serializer.errors}")
            return Response(
                {
                    'error': 'Invalid data',
                    'details': serializer.errors,
                    'received_data': request.data
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in registration: {str(e)}")
            return Response(
                {
                    'error': 'An unexpected error occurred',
                    'details': str(e),
                    'received_data': request.data
                },
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return Contact.objects.filter(user=self.request.user)

    def perform_create(self, serializer):
        try:
            # Check if contact already exists
            existing_contact = Contact.objects.filter(
                user=self.request.user,
                phone_number=serializer.validated_data['phone_number']
            ).first()
            
            if existing_contact:
                logger.warning(f"Contact already exists for user {self.request.user.username}")
                raise ValidationError('Contact with this phone number already exists')
                
            serializer.save(user=self.request.user)
            logger.info(f"Contact created successfully for user {self.request.user.username}")
            
        except IntegrityError as e:
            logger.error(f"Database integrity error: {str(e)}")
            raise ValidationError('Error creating contact: Database integrity error')
        except Exception as e:
            logger.error(f"Error creating contact: {str(e)}")
            raise ValidationError(f'Error creating contact: {str(e)}')

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            logger.error(f"Unexpected error creating contact: {str(e)}")
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def destroy(self, request, *args, **kwargs):
        try:
            instance = self.get_object()
            self.perform_destroy(instance)
            logger.info(f"Contact deleted successfully by user {request.user.username}")
            return Response(status=status.HTTP_204_NO_CONTENT)
        except Exception as e:
            logger.error(f"Error deleting contact: {str(e)}")
            return Response(
                {'error': f'Error deleting contact: {str(e)}'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

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