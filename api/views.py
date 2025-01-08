import logging
from rest_framework import viewsets, status, filters
from rest_framework.decorators import action, api_view, permission_classes
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.views import APIView
from django.db.models import Q, Count, F
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from django.db import IntegrityError, connections
from django.db.utils import OperationalError
from .models import Contact, SpamReport
from .serializers import (
    UserSerializer, UserRegistrationSerializer, ContactSerializer,
    SearchResultSerializer, SpamReportSerializer
)
from rest_framework.parsers import JSONParser
from rest_framework_simplejwt.tokens import RefreshToken

logger = logging.getLogger(__name__)

User = get_user_model()

class RegistrationView(APIView):
    permission_classes = []  # Allow unauthenticated access
    authentication_classes = []  # No authentication needed for registration
    parser_classes = (JSONParser,)  # Only accept JSON data
    
    def post(self, request, *args, **kwargs):
        logger.info(f"Registration attempt with data: {request.data}")
        
        try:
            # Validate request data presence
            if not isinstance(request.data, dict):
                return Response(
                    {'error': 'Invalid data format. JSON object expected'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Basic data validation
            required_fields = ['username', 'password', 'phone_number']
            missing_fields = [field for field in required_fields if not request.data.get(field)]
            if missing_fields:
                return Response(
                    {
                        'error': 'Missing required fields',
                        'missing_fields': missing_fields
                    },
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Validate phone number format
            phone_number = request.data.get('phone_number')
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
                request.data['phone_number'] = phone_number

            # Check if username exists
            if User.objects.filter(username=request.data.get('username')).exists():
                return Response(
                    {'error': 'Username already exists'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Check if phone number exists
            if User.objects.filter(phone_number=phone_number).exists():
                return Response(
                    {'error': 'Phone number already registered'},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = UserRegistrationSerializer(data=request.data)
            if serializer.is_valid():
                user = serializer.save()
                # Get tokens for the user
                refresh = RefreshToken.for_user(user)
                return Response(
                    {
                        'message': 'User created successfully',
                        'user': serializer.data,
                        'tokens': {
                            'refresh': str(refresh),
                            'access': str(refresh.access_token),
                        }
                    },
                    status=status.HTTP_201_CREATED
                )
            
            return Response(
                {
                    'error': 'Invalid data',
                    'details': serializer.errors
                },
                status=status.HTTP_400_BAD_REQUEST
            )
            
        except Exception as e:
            logger.error(f"Unexpected error in registration: {str(e)}")
            return Response(
                {
                    'error': 'An unexpected error occurred',
                    'details': str(e)
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
        try:
            query = request.query_params.get('q', '').strip()
            search_type = request.query_params.get('type', 'name').lower()

            if not query:
                return Response(
                    {"error": "Query parameter 'q' is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if search_type not in ['name', 'phone']:
                return Response(
                    {"error": "Search type must be either 'name' or 'phone'"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            results = []
            if search_type == 'name':
                # First get exact matches
                contacts = Contact.objects.filter(
                    Q(name__iexact=query) |
                    Q(name__istartswith=query)
                ).distinct()

                # Then get partial matches
                if not contacts.exists():
                    contacts = Contact.objects.filter(
                        name__icontains=query
                    ).exclude(
                        Q(name__iexact=query) |
                        Q(name__istartswith=query)
                    ).distinct()

            else:  # phone search
                # Clean phone number
                if not query.startswith('+'):
                    query = '+' + query

                # First check registered users
                registered_user = User.objects.filter(phone_number=query).first()
                if registered_user:
                    # Return only registered user if found
                    results.append({
                        'name': registered_user.username,
                        'phone_number': registered_user.phone_number,
                        'spam_likelihood': self.get_spam_likelihood(query),
                        'email': registered_user.email if Contact.objects.filter(
                            user=request.user,
                            phone_number=query
                        ).exists() else None,
                        'is_registered': True
                    })
                    return Response(results)

                # If no registered user found, search contacts
                contacts = Contact.objects.filter(phone_number=query).distinct()

            # Process contacts
            seen_numbers = set()
            for contact in contacts:
                if contact.phone_number in seen_numbers:
                    continue
                seen_numbers.add(contact.phone_number)

                result = {
                    'name': contact.name,
                    'phone_number': contact.phone_number,
                    'spam_likelihood': self.get_spam_likelihood(contact.phone_number),
                    'is_registered': False
                }

                # Check if this contact is a registered user
                registered_user = User.objects.filter(phone_number=contact.phone_number).first()
                if registered_user:
                    result['is_registered'] = True
                    # Add email only if the searcher is in their contacts
                    if Contact.objects.filter(
                        user=registered_user,
                        phone_number=request.user.phone_number
                    ).exists():
                        result['email'] = registered_user.email

                results.append(result)

            return Response(results)

        except Exception as e:
            logger.error(f"Search error: {str(e)}")
            return Response(
                {'error': 'An error occurred during search'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

class SpamViewSet(viewsets.ModelViewSet):
    serializer_class = SpamReportSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return SpamReport.objects.filter(reported_by=self.request.user)

    def create(self, request, *args, **kwargs):
        try:
            # Clean phone number
            phone_number = request.data.get('phone_number', '').strip()
            if not phone_number:
                return Response(
                    {"error": "Phone number is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number
                request.data['phone_number'] = phone_number

            # Check if already reported
            if SpamReport.objects.filter(
                reported_by=request.user,
                phone_number=phone_number
            ).exists():
                return Response(
                    {"error": "You have already reported this number"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            serializer = self.get_serializer(data=request.data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)

            # Get updated spam stats
            total_users = User.objects.count()
            spam_count = SpamReport.objects.filter(phone_number=phone_number).count()
            spam_likelihood = (spam_count / total_users) * 100 if total_users > 0 else 0

            return Response({
                'message': 'Number reported as spam successfully',
                'phone_number': phone_number,
                'spam_likelihood': spam_likelihood,
                'total_reports': spam_count
            }, status=status.HTTP_201_CREATED)

        except Exception as e:
            logger.error(f"Error reporting spam: {str(e)}")
            return Response(
                {'error': 'An error occurred while reporting spam'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def perform_create(self, serializer):
        serializer.save(reported_by=self.request.user)

    @action(detail=False, methods=['get'])
    def check(self, request):
        try:
            phone_number = request.query_params.get('phone_number', '').strip()
            if not phone_number:
                return Response(
                    {"error": "phone_number parameter is required"},
                    status=status.HTTP_400_BAD_REQUEST
                )

            # Clean phone number
            if not phone_number.startswith('+'):
                phone_number = '+' + phone_number

            total_users = User.objects.count()
            spam_reports = SpamReport.objects.filter(phone_number=phone_number)
            spam_count = spam_reports.count()
            
            # Get recent reporters
            recent_reporters = []
            if spam_count > 0:
                recent_reporters = [
                    {
                        'username': report.reported_by.username,
                        'date': report.created_at
                    }
                    for report in spam_reports.order_by('-created_at')[:5]
                ]

            return Response({
                'phone_number': phone_number,
                'spam_likelihood': (spam_count / total_users) * 100 if total_users > 0 else 0,
                'total_reports': spam_count,
                'recent_reporters': recent_reporters,
                'is_reported_by_you': spam_reports.filter(reported_by=request.user).exists()
            })

        except Exception as e:
            logger.error(f"Error checking spam: {str(e)}")
            return Response(
                {'error': 'An error occurred while checking spam status'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

@api_view(['GET'])
@permission_classes([AllowAny])
def health_check(request):
    """
    Health check endpoint to verify service and database status
    """
    try:
        # Test database connection
        db_conn = connections['default']
        c = db_conn.cursor()
        c.execute('SELECT 1')
        row = c.fetchone()
        if row is None:
            raise Exception("Database check failed")
        
        return Response({
            'status': 'healthy',
            'database': 'connected'
        }, status=status.HTTP_200_OK)
    except OperationalError:
        return Response({
            'status': 'unhealthy',
            'database': 'disconnected'
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE)
    except Exception as e:
        return Response({
            'status': 'unhealthy',
            'error': str(e)
        }, status=status.HTTP_503_SERVICE_UNAVAILABLE) 