from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from api.models import Contact, SpamReport
from faker import Faker
import random

User = get_user_model()
fake = Faker()

class Command(BaseCommand):
    help = 'Populates the database with sample data'

    def add_arguments(self, parser):
        parser.add_argument('--users', type=int, default=20)
        parser.add_argument('--contacts', type=int, default=100)
        parser.add_argument('--reports', type=int, default=50)

    def handle(self, *args, **options):
        self.stdout.write('Creating users...')
        users = self._create_users(options['users'])
        
        self.stdout.write('Creating contacts...')
        self._create_contacts(users, options['contacts'])
        
        self.stdout.write('Creating spam reports...')
        self._create_spam_reports(users, options['reports'])
        
        self.stdout.write(self.style.SUCCESS('Successfully populated database'))

    def _create_users(self, count):
        users = []
        for i in range(count):
            phone = f"+1{fake.msisdn()[3:]}"  # US format
            try:
                user = User.objects.create_user(
                    username=phone,
                    phone_number=phone,
                    password='testpass123',
                    first_name=fake.first_name(),
                    email=fake.email() if random.random() > 0.3 else None
                )
                users.append(user)
                self.stdout.write(f'Created user: {user.phone_number}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Failed to create user: {str(e)}'))
        return users

    def _create_contacts(self, users, count):
        for i in range(count):
            user = random.choice(users)
            try:
                contact = Contact.objects.create(
                    user=user,
                    name=fake.name(),
                    phone_number=f"+1{fake.msisdn()[3:]}",
                    email=fake.email() if random.random() > 0.5 else None,
                    notes=fake.text() if random.random() > 0.7 else None,
                    tags=','.join(fake.words(3)) if random.random() > 0.5 else None,
                    groups=','.join(fake.words(2)) if random.random() > 0.6 else None
                )
                self.stdout.write(f'Created contact: {contact.name}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Failed to create contact: {str(e)}'))

    def _create_spam_reports(self, users, count):
        report_types = ['spam', 'scam', 'telemarketing', 'robocall', 'other']
        for i in range(count):
            reporter = random.choice(users)
            try:
                report = SpamReport.objects.create(
                    reported_number=f"+1{fake.msisdn()[3:]}",
                    reporter=reporter,
                    report_type=random.choice(report_types),
                    details=fake.text() if random.random() > 0.3 else None,
                    severity=random.randint(1, 10),
                    is_verified=random.random() > 0.7
                )
                self.stdout.write(f'Created spam report: {report.reported_number}')
            except Exception as e:
                self.stdout.write(self.style.WARNING(f'Failed to create spam report: {str(e)}')) 