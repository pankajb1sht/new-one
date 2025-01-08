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
        parser.add_argument('--users', type=int, default=10)
        parser.add_argument('--contacts-per-user', type=int, default=20)
        parser.add_argument('--spam-reports', type=int, default=30)

    def handle(self, *args, **options):
        num_users = options['users']
        contacts_per_user = options['contacts_per_user']
        num_spam_reports = options['spam_reports']

        self.stdout.write('Creating users...')
        users = []
        for i in range(num_users):
            user = User.objects.create_user(
                username=fake.user_name(),
                password='testpass123',
                phone_number=f'+1{fake.msisdn()[3:]}',
                email=fake.email() if random.choice([True, False]) else None
            )
            users.append(user)
            self.stdout.write(f'Created user: {user.username}')

        self.stdout.write('Creating contacts...')
        for user in users:
            for _ in range(contacts_per_user):
                Contact.objects.create(
                    user=user,
                    name=fake.name(),
                    phone_number=f'+1{fake.msisdn()[3:]}'
                )

        self.stdout.write('Creating spam reports...')
        all_contacts = Contact.objects.all()
        for _ in range(num_spam_reports):
            contact = random.choice(all_contacts)
            user = random.choice(users)
            SpamReport.objects.get_or_create(
                reported_by=user,
                phone_number=contact.phone_number
            )

        self.stdout.write(self.style.SUCCESS('Successfully populated the database')) 