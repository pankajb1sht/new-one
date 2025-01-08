# Spam Detector API

A Django REST API for detecting and reporting spam phone numbers.

## Features

- User registration and authentication using JWT
- Contact management system
- Spam reporting and detection
- Rate limiting and throttling
- API documentation using Swagger/OpenAPI
- Caching for improved performance
- Comprehensive test suite

## Prerequisites

- Python 3.8+
- PostgreSQL
- Virtual environment (recommended)

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd spam_detector
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
```

5. Update the `.env` file with your configuration:
```
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DB_NAME=spam_detector
DB_USER=your-db-user
DB_PASSWORD=your-db-password
DB_HOST=localhost
DB_PORT=5432
CORS_ALLOWED_ORIGINS=http://localhost:3000
```

6. Create the database:
```bash
createdb spam_detector
```

7. Run migrations:
```bash
python manage.py migrate
```

8. Create a superuser:
```bash
python manage.py createsuperuser
```

## Running the Development Server

```bash
python manage.py runserver
```

The API will be available at http://localhost:8000/api/
The admin interface will be available at http://localhost:8000/admin/
API documentation will be available at http://localhost:8000/swagger/

## API Endpoints

### Authentication
- POST /api/token/ - Obtain JWT token
- POST /api/token/refresh/ - Refresh JWT token

### Users
- POST /api/users/ - Register new user
- GET /api/users/me/ - Get current user details
- PUT /api/users/me/ - Update current user

### Contacts
- GET /api/contacts/ - List user's contacts
- POST /api/contacts/ - Create new contact
- GET /api/contacts/{id}/ - Get contact details
- PUT /api/contacts/{id}/ - Update contact
- DELETE /api/contacts/{id}/ - Delete contact

### Spam Reports
- GET /api/reports/ - List spam reports
- POST /api/reports/ - Create spam report
- GET /api/reports/{id}/ - Get report details
- GET /api/search/ - Search phone numbers

## Testing

Run the test suite:
```bash
python manage.py test
```

For coverage report:
```bash
coverage run manage.py test
coverage report
```

## Security Features

- JWT authentication
- Rate limiting
- CORS protection
- SSL/TLS support
- XSS protection
- CSRF protection
- Secure cookie settings
- Password validation

## Deployment

For production deployment:

1. Set DEBUG=False in .env
2. Configure proper database settings
3. Set up proper ALLOWED_HOSTS
4. Configure CORS_ALLOWED_ORIGINS
5. Set up SSL/TLS
6. Configure proper logging
7. Set up proper caching (Redis recommended)
8. Configure proper static file serving

## Contributing

1. Fork the repository
2. Create your feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details. 