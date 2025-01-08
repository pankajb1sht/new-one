from django.db.models import Count, Avg, Q, F
from django.contrib.auth import get_user_model
from rest_framework import viewsets, status, generics
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.exceptions import ValidationError
from rest_framework.pagination import PageNumberPagination
from django.contrib.postgres.search import SearchVector, SearchQuery, SearchRank
from django.core.cache import cache
from django.core.cache.utils import make_template_fragment_key
from django.utils.decorators import method_decorator
from django.views.decorators.cache import cache_page
from django.core.exceptions import ObjectDoesNotExist
from .models import Contact, SpamReport
from .serializers import (
    UserSerializer, UserRegistrationSerializer, ContactSerializer,
    SpamReportSerializer, PhoneNumberSearchSerializer, NameSearchSerializer
)

User = get_user_model()

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 10
    page_size_query_param = 'page_size'
    max_page_size = 100

class UserViewSet(viewsets.ModelViewSet):
    queryset = User.objects.all()
    serializer_class = UserSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_permissions(self):
        if self.action == 'create':
            return [AllowAny()]
        return super().get_permissions()

    def get_serializer_class(self):
        if self.action == 'create':
            return UserRegistrationSerializer
        return UserSerializer

    def create(self, request, *args, **kwargs):
        try:
            return super().create(request, *args, **kwargs)
        except Exception as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )

class ContactViewSet(viewsets.ModelViewSet):
    serializer_class = ContactSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = Contact.objects.filter(user=self.request.user)
        name = self.request.query_params.get('name', None)
        phone = self.request.query_params.get('phone', None)
        tags = self.request.query_params.get('tags', None)

        if name:
            queryset = queryset.filter(name__icontains=name)
        if phone:
            queryset = queryset.filter(phone_number__icontains=phone)
        if tags:
            tag_list = [tag.strip() for tag in tags.split(',')]
            for tag in tag_list:
                queryset = queryset.filter(tags__icontains=tag)

        return queryset.order_by('-updated_at')

    def perform_create(self, serializer):
        try:
            serializer.save(user=self.request.user)
            cache.delete_pattern('search_results_*')
        except ValidationError as e:
            raise ValidationError(detail=str(e))

    def perform_update(self, serializer):
        try:
            serializer.save()
            cache.delete_pattern('search_results_*')
        except ValidationError as e:
            raise ValidationError(detail=str(e))

    def perform_destroy(self, instance):
        try:
            instance.delete()
            cache.delete_pattern('search_results_*')
        except Exception as e:
            raise ValidationError(detail=str(e))

class SpamReportViewSet(viewsets.ModelViewSet):
    serializer_class = SpamReportSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    def get_queryset(self):
        queryset = SpamReport.objects.all()
        phone = self.request.query_params.get('phone', None)
        report_type = self.request.query_params.get('type', None)
        severity = self.request.query_params.get('severity', None)

        if phone:
            queryset = queryset.filter(reported_number=phone)
        if report_type:
            queryset = queryset.filter(report_type=report_type)
        if severity:
            queryset = queryset.filter(severity=severity)

        return queryset.order_by('-timestamp')

    def perform_create(self, serializer):
        try:
            serializer.save(reporter=self.request.user)
            cache.delete_pattern('spam_likelihood_*')
        except ValidationError as e:
            raise ValidationError(detail=str(e))

class SearchView(generics.GenericAPIView):
    permission_classes = [IsAuthenticated]
    pagination_class = StandardResultsSetPagination

    @method_decorator(cache_page(60 * 5))  # Cache for 5 minutes
    def get(self, request):
        try:
            search_type = request.query_params.get('type', 'phone')
            query = request.query_params.get('q', '')

            if not query:
                raise ValidationError({'error': 'Query parameter is required'})

            if search_type not in ['phone', 'name']:
                raise ValidationError({'error': 'Invalid search type'})

            cache_key = f'search_results_{search_type}_{query}'
            results = cache.get(cache_key)

            if results is None:
                if search_type == 'phone':
                    results = self._search_by_phone(query, request.user)
                else:
                    results = self._search_by_name(query, request.user)
                
                cache.set(cache_key, results, timeout=300)  # Cache for 5 minutes

            # Apply pagination
            page = self.paginate_queryset(results.get('results', []))
            if page is not None:
                return self.get_paginated_response(page)

            return Response(results)

        except ValidationError as e:
            return Response(
                {'error': str(e)},
                status=status.HTTP_400_BAD_REQUEST
            )
        except Exception as e:
            return Response(
                {'error': 'An unexpected error occurred'},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )

    def _search_by_phone(self, query, user):
        try:
            # First check for registered user
            user_result = User.objects.filter(phone_number=query).first()
            
            if user_result:
                spam_likelihood, report_count = self._get_spam_likelihood(query)
                result = {
                    'phone_number': query,
                    'name': user_result.first_name,
                    'spam_likelihood': spam_likelihood,
                    'report_count': report_count
                }
                
                # Only include email if searching user is in contact list
                if Contact.objects.filter(user=user_result, phone_number=user.phone_number).exists():
                    result['email'] = user_result.email
                
                return {'results': [result]}
            
            # If no registered user, search contacts
            contacts = Contact.objects.filter(phone_number=query)
            if not contacts.exists():
                spam_likelihood, report_count = self._get_spam_likelihood(query)
                return {
                    'results': [{
                        'phone_number': query,
                        'name': None,
                        'spam_likelihood': spam_likelihood,
                        'report_count': report_count
                    }]
                }
            
            # Return all contact entries for this number
            contact_names = contacts.values_list('name', flat=True).distinct()
            spam_likelihood, report_count = self._get_spam_likelihood(query)
            
            return {
                'results': [{
                    'phone_number': query,
                    'names': list(contact_names),
                    'spam_likelihood': spam_likelihood,
                    'report_count': report_count
                }]
            }
        except Exception as e:
            raise ValidationError(str(e))

    def _search_by_name(self, query, user):
        try:
            # Create search vectors with weights
            vector = (
                SearchVector('first_name', weight='A') +
                SearchVector('username', weight='B')
            )
            search_query = SearchQuery(query)

            # Search in users
            users = (
                User.objects.annotate(rank=SearchRank(vector, search_query))
                .filter(rank__gt=0.1)
                .order_by('-rank')
            )

            # Search in contacts
            contact_vector = (
                SearchVector('name', weight='A') +
                SearchVector('notes', weight='C')
            )
            contacts = (
                Contact.objects.annotate(rank=SearchRank(contact_vector, search_query))
                .filter(rank__gt=0.1)
                .order_by('-rank')
            )

            results = []
            seen_numbers = set()

            # Process user results
            for user_obj in users:
                if user_obj.phone_number not in seen_numbers:
                    spam_likelihood, report_count = self._get_spam_likelihood(user_obj.phone_number)
                    result = {
                        'phone_number': user_obj.phone_number,
                        'name': user_obj.first_name,
                        'spam_likelihood': spam_likelihood,
                        'report_count': report_count,
                        'is_registered': True
                    }
                    if Contact.objects.filter(user=user_obj, phone_number=user.phone_number).exists():
                        result['email'] = user_obj.email
                    results.append(result)
                    seen_numbers.add(user_obj.phone_number)

            # Process contact results
            for contact in contacts:
                if contact.phone_number not in seen_numbers:
                    spam_likelihood, report_count = self._get_spam_likelihood(contact.phone_number)
                    results.append({
                        'phone_number': contact.phone_number,
                        'name': contact.name,
                        'spam_likelihood': spam_likelihood,
                        'report_count': report_count,
                        'is_registered': False
                    })
                    seen_numbers.add(contact.phone_number)

            return {
                'query': query,
                'results': sorted(results, key=lambda x: (
                    not x['name'].lower().startswith(query.lower()),
                    -x['spam_likelihood'] if x['spam_likelihood'] > 0.5 else 0,
                    x['name']
                ))
            }
        except Exception as e:
            raise ValidationError(str(e))

    def _get_spam_likelihood(self, phone_number):
        try:
            cache_key = f'spam_likelihood_{phone_number}'
            cached_result = cache.get(cache_key)
            
            if cached_result is not None:
                return cached_result
            
            reports = SpamReport.objects.filter(reported_number=phone_number)
            if not reports.exists():
                cache.set(cache_key, (0.0, 0), timeout=3600)  # Cache for 1 hour
                return 0.0, 0
            
            report_count = reports.count()
            avg_severity = reports.aggregate(Avg('severity'))['severity__avg']
            
            # Enhanced spam likelihood calculation
            time_weighted_reports = reports.annotate(
                time_weight=F('severity') * (1 + 1 / (1 + F('timestamp')))
            ).aggregate(
                weighted_sum=Avg('time_weight')
            )['weighted_sum'] or 0
            
            # Normalize to 0-1 range with time decay
            likelihood = min(time_weighted_reports / 10, 1.0)
            
            result = (likelihood, report_count)
            cache.set(cache_key, result, timeout=3600)  # Cache for 1 hour
            return result
        except Exception as e:
            raise ValidationError(str(e)) 