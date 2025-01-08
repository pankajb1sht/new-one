# Spam Detection API

A Django REST API for spam detection and contact management, similar to Truecaller.

## Features

- User registration and authentication
- Contact management
- Spam number reporting
- Name and phone number search functionality
- Privacy-aware contact details sharing

## Setup Instructions

1. Create a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Linux/Mac
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a .env file:
```bash
cp .env.example .env
# Edit .env with your database credentials
```

4. Run migrations:
```bash
python manage.py migrate
```

5. Create a superuser:
```bash
python manage.py createsuperuser
```

6. Populate test data (optional):
```bash
python manage.py populate_data
```

7. Run the development server:
```bash
python manage.py runserver
```

## API Endpoints

### Authentication
- POST /api/auth/register/ - Register new user
- POST /api/auth/login/ - Login user
- POST /api/auth/refresh/ - Refresh JWT token

### Contacts
- GET /api/contacts/ - List user's contacts
- POST /api/contacts/ - Add new contact
- DELETE /api/contacts/{id}/ - Remove contact

### Search
- GET /api/search/name/?q={query} - Search by name
- GET /api/search/phone/?q={number} - Search by phone number

### Spam
- POST /api/spam/report/ - Report a number as spam
- GET /api/spam/check/{number}/ - Check spam status

## Security Features

- JWT based authentication
- Phone number verification
- Rate limiting
- Input validation
- Privacy controls for email visibility 