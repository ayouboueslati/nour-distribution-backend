# Nour Distribution Backend

> A comprehensive distribution management system built with FastAPI, PostgreSQL, and Docker

[![FastAPI](https://img.shields.io/badge/FastAPI-0.109+-00C7B7?style=flat&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Python](https://img.shields.io/badge/Python-3.11+-3776AB?style=flat&logo=python&logoColor=white)](https://www.python.org/)
[![PostgreSQL](https://img.shields.io/badge/PostgreSQL-15+-336791?style=flat&logo=postgresql&logoColor=white)](https://www.postgresql.org/)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ED?style=flat&logo=docker&logoColor=white)](https://www.docker.com/)
[![License](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

## 📋 Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Tech Stack](#tech-stack)
- [Architecture](#architecture)
- [Getting Started](#getting-started)
  - [Prerequisites](#prerequisites)
  - [Installation](#installation)
  - [Docker Deployment](#docker-deployment)
- [API Documentation](#api-documentation)
- [Configuration](#configuration)
- [Security](#security)
- [Development](#development)
- [Testing](#testing)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## 🎯 Overview

**Nour Distribution** is a production-ready ERP system designed for Tunisian distribution businesses, specializing in hairdressing accessories. The backend provides a robust REST API for managing inventory, orders, invoicing, client relationships, and comprehensive business analytics.

### Key Highlights

- 🚀 **High Performance**: Built with FastAPI for async/await support
- 🔒 **Enterprise Security**: JWT authentication, role-based access control, and Docker security hardening
- 📊 **Business Intelligence**: Real-time analytics and reporting
- 🧾 **Compliant Invoicing**: Tunisian tax regulations (TVA, Timbre Fiscal)
- 📄 **PDF Generation**: Professional invoices, quotes, and credit notes
- 📧 **Email Notifications**: Automated transactional emails
- 🐳 **Docker Ready**: Containerized for easy deployment

## ✨ Features

### Core Functionality

#### 📦 Inventory Management
- Product catalog with categories and variants
- Real-time stock tracking and alerts
- Low stock notifications
- Stock movement history
- Supplier management
- Barcode support

#### 🛒 Order Management
- Complete order lifecycle (Pending → Processing → Confirmed → Completed)
- Shopping cart functionality
- Order status tracking
- Multi-item orders with discounts
- Shipping fee calculation
- Order history and analytics

#### 📑 Document Management
- **Devis (Quotes)**: Generate professional quotes with approval workflow
- **Factures (Invoices)**: Compliant invoicing with payment tracking
- **Avoirs (Credit Notes)**: Stock returns and credit management
- PDF generation with QR codes
- Email delivery
- Document timeline tracking

#### 💰 Financial Management
- Multiple payment methods (Cash, Check, Wire Transfer, Card, etc.)
- Payment tracking and reconciliation
- Partial payment support
- Payment terms management
- Financial reporting

#### 👥 Client Management
- Client profiles and contact information
- Client portal for order tracking
- Purchase history
- Client-specific pricing
- Account balance tracking

#### 📊 Analytics & Reporting
- Sales analytics and trends
- Stock health reports
- Revenue dashboards
- Category performance analysis
- Inventory turnover metrics
- Export to Excel/CSV

#### 👨‍💼 User Management
- Role-based access control (RBAC)
- Multiple user roles: Super Admin, Manager, Sales, Inventory, Delivery
- User activity logging
- Profile management

#### 🔔 Notifications
- Email notifications for orders, payments, and status changes
- Real-time admin notifications
- Customizable notification templates
- HTML email templates

### Tunisian Business Compliance

- ✅ TVA (VAT) calculation at 19%
- ✅ Timbre Fiscal (Stamp Duty) at 1.000 DT
- ✅ Matricule Fiscal and Registre de Commerce
- ✅ Compliant invoice formatting
- ✅ Tunisian payment methods support
- ✅ French language invoices with amounts in words

## 🛠 Tech Stack

### Backend Framework
- **FastAPI** - Modern, high-performance web framework
- **Python 3.11+** - Latest Python with performance improvements
- **Uvicorn** - Lightning-fast ASGI server
- **Pydantic** - Data validation using Python type annotations

### Database
- **PostgreSQL 15** - Robust relational database
- **SQLAlchemy** - SQL toolkit and ORM
- **Alembic** - Database migration tool
- **AsyncPG** - Async PostgreSQL driver

### Security
- **Python-JOSE** - JWT token generation and validation
- **Passlib + Bcrypt** - Password hashing
- **CORS Middleware** - Cross-origin resource sharing

### PDF & Documents
- **ReportLab** - PDF generation
- **Num2Words** - Convert numbers to words (French)
- **QRCode** - QR code generation for invoices
- **Pillow** - Image processing

### Email
- **AioSMTPLib** - Async SMTP client
- **Jinja2** - Email template engine

### Analytics & Reporting
- **Pandas** - Data analysis and manipulation
- **NumPy** - Numerical computing
- **Plotly** - Interactive charts
- **OpenPyXL** - Excel file generation

### DevOps
- **Docker** - Containerization
- **Docker Compose** - Multi-container orchestration
- **Pytest** - Testing framework

## 🏗 Architecture

```
nour-distribution-backend/
├── app/
│   ├── api/
│   │   └── v1/
│   │       ├── endpoints/      # API route handlers
│   │       │   ├── auth.py
│   │       │   ├── products.py
│   │       │   ├── orders.py
│   │       │   ├── documents.py
│   │       │   ├── clients.py
│   │       │   ├── analytics.py
│   │       │   └── ...
│   │       └── api.py          # API router aggregation
│   ├── core/
│   │   ├── config.py           # Application settings
│   │   ├── security.py         # Authentication & authorization
│   │   └── database.py         # Database connection
│   ├── models/                 # SQLAlchemy models
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── order.py
│   │   ├── document.py
│   │   └── ...
│   ├── schemas/                # Pydantic schemas
│   │   ├── user.py
│   │   ├── product.py
│   │   ├── order.py
│   │   └── ...
│   ├── services/               # Business logic
│   │   ├── auth_service.py
│   │   ├── product_service.py
│   │   ├── order_service.py
│   │   ├── document_service.py
│   │   ├── pdf_service.py
│   │   └── notification_service.py
│   ├── templates/              # Email templates
│   │   └── emails/
│   └── utils/                  # Utility functions
├── migrations/                 # Alembic migrations
├── static/                     # Static files (PDFs, images)
├── tests/                      # Test suite
├── requirements/               # Python dependencies
│   ├── base.txt
│   ├── dev.txt
│   └── prod.txt
├── docker-compose.yml          # Development Docker config
├── docker-compose.prod.yml     # Production Docker config (hardened)
├── Dockerfile
├── alembic.ini
├── main.py                     # Application entry point
└── .env.example                # Environment variables template

```

### Design Patterns

- **Repository Pattern**: Data access abstraction through services
- **Dependency Injection**: FastAPI's native DI for database sessions
- **Schema Validation**: Pydantic models for request/response validation
- **Factory Pattern**: Dynamic service instantiation
- **Observer Pattern**: Event-driven notifications

## 🚀 Getting Started

### Prerequisites

- **Python 3.11+** installed
- **PostgreSQL 15+** running
- **Docker & Docker Compose** (optional, recommended)
- **Git** for version control

### Installation

#### 1. Clone the Repository

```bash
git clone https://github.com/yourusername/nour-distribution-backend.git
cd nour-distribution-backend
```

#### 2. Create Virtual Environment

```bash
python -m venv venv

# Windows
venv\Scripts\activate

# macOS/Linux
source venv/bin/activate
```

#### 3. Install Dependencies

```bash
# Development
pip install -r requirements/dev.txt

# Production
pip install -r requirements/prod.txt
```

#### 4. Configure Environment Variables

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your configuration
# Required: DATABASE_URL, SECRET_KEY, SMTP credentials, etc.
```

#### 5. Initialize Database

```bash
# Run migrations
alembic upgrade head

# Seed initial data (optional)
python -m app.scripts.seed_data
```

#### 6. Run the Application

```bash
# Development mode with auto-reload
uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Production mode
uvicorn main:app --host 0.0.0.0 --port 8000 --workers 4
```

The API will be available at:
- **API Root**: http://localhost:8000
- **Interactive Docs (Swagger)**: http://localhost:8000/docs
- **Alternative Docs (ReDoc)**: http://localhost:8000/redoc

### Docker Deployment

#### Development

```bash
# Start all services
docker compose up -d

# View logs
docker compose logs -f

# Stop services
docker compose down
```

#### Production (Security Hardened)

```bash
# Initialize Docker Swarm
docker swarm init

# Create secrets
echo "production_user" | docker secret create db_user -
echo "$(openssl rand -base64 32)" | docker secret create db_password -

# Deploy stack
docker stack deploy -f docker-compose.prod.yml nour-distribution

# Check status
docker service ls
```

**Features**:
- ✅ Non-root user execution
- ✅ Read-only root filesystem
- ✅ Dropped Linux capabilities
- ✅ No new privileges
- ✅ Secrets management via Docker Secrets
- ✅ Network isolation

See [Security Documentation](#security) for details.


## 📚 API Documentation

For complete API documentation, please refer to the interactive Swagger documentation available when running the application locally at `/docs`.



## ⚙️ Configuration

### Environment Variables

Create a `.env` file in the project root:

```bash
# Application
PROJECT_NAME=Nour Distribution
VERSION=1.0.0
API_V1_STR=/api/v1

# Database
DATABASE_URL=postgresql://user:password@localhost:5432/nour_distribution

# Security
SECRET_KEY=your-secret-key-here
ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=30
BCRYPT_ROUNDS=12

# SMTP Email
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-email@gmail.com
SMTP_PASSWORD=your-app-password
FROM_EMAIL=noreply@nour-distribution.com
EMAIL_ENABLED=true

# First Admin (for initial setup)
FIRST_SUPER_ADMIN_EMAIL=admin@example.com
FIRST_SUPER_ADMIN_PASSWORD=changeme
FIRST_SUPER_ADMIN_NAME=Super Admin

# CORS
CORS_ORIGINS=["http://localhost:3000","http://127.0.0.1:3000"]

# Tunisian Tax Configuration
TVA_RATE=0.19
TIMBRE_FISCAL_RATE=1.000

# Company Information
COMPANY_NAME=NOUR DISTRIBUTION
COMPANY_ADDRESS=87 Avenue de la République, 2033 Megrine – BEN AROUS
COMPANY_PHONE=71 432 831
COMPANY_EMAIL=contact@nour-distribution.com
COMPANY_MATRICULE_FISCAL=155546 / F
```

See `.env.example` for all available options.

## 🔒 Security

> [!IMPORTANT]
> **Production Security Checklist**
> - [ ] Change all default passwords and secrets
> - [ ] Disable `/docs` and `/redoc` endpoints in production
> - [ ] Enable HTTPS/TLS (use reverse proxy like nginx)
> - [ ] Use Docker Secrets or external secrets manager
> - [ ] Configure rate limiting
> - [ ] Set up Web Application Firewall (WAF)
> - [ ] Enable security monitoring and alerting
> - [ ] Regularly update dependencies

### Security Features

- ✅ **JWT Authentication** with token expiration
- ✅ **Password Hashing** using Bcrypt (12 rounds)
- ✅ **Role-Based Access Control** (RBAC)
- ✅ **CORS Configuration** for frontend integration
- ✅ **SQL Injection Prevention** via ORM
- ✅ **Input Validation** with Pydantic
- ✅ **Secrets Management** via Docker Secrets (production)
- ✅ **Rate Limiting** (recommended: configure in reverse proxy)
- ✅ **Security Headers** (HSTS, CSP, etc.)

### Docker Security (Production)

Our production Docker setup implements enterprise-grade security:

#### Container Security
- **Non-root User**: Application runs as `appuser` (UID 1000)
- **Read-only Filesystem**: Root filesystem is read-only
- **Dropped Capabilities**: All Linux capabilities dropped
- **No New Privileges**: Prevents privilege escalation

#### Secrets Management
- **Docker Secrets**: Credentials stored securely, not in environment variables
- **No Plain Text**: Database passwords never in compose files
- **Secret Rotation**: Support for zero-downtime credential rotation

#### Network Security
- **Internal Networks**: Database not exposed to host
- **Inter-container Communication**: Services communicate on isolated network
- **TLS Support**: Ready for reverse proxy with SSL termination

### Security Documentation

Comprehensive security guides available:
- `SECRETS_MANAGEMENT_GUIDE.md` - Secrets management best practices
- `SECURITY_TESTING_GUIDE.md` - Security validation procedures
- `QUICK_REFERENCE.md` - Security quick reference

### Security Testing

```bash
# Run security tests
./test-security.sh

# Scan for vulnerabilities
docker scout cves nour-distribution-backend:latest

# Or use Trivy
trivy image nour-distribution-backend:latest
```

## 💻 Development

### Code Style

We follow **PEP 8** style guidelines with some modifications:

- Line length: 120 characters
- Use type hints for function signatures
- Docstrings for all public functions/classes

### Project Structure Guidelines

- **Models**: Database models (SQLAlchemy)
- **Schemas**: Request/response validation (Pydantic)
- **Services**: Business logic layer
- **Endpoints**: API route handlers (thin layer)
- **Utils**: Reusable utility functions

### Database Migrations

```bash
# Create a new migration
alembic revision --autogenerate -m "Description of changes"

# Apply migrations
alembic upgrade head

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

### Adding New Features

1. Create database model in `app/models/`
2. Define Pydantic schemas in `app/schemas/`
3. Implement business logic in `app/services/`
4. Create API endpoints in `app/api/v1/endpoints/`
5. Register routes in `app/api/v1/api.py`
6. Write tests in `tests/`
7. Generate migration: `alembic revision --autogenerate`

## 🧪 Testing

### Run Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=app --cov-report=html

# Run specific test file
pytest tests/test_products.py

# Run with verbose output
pytest -v
```

### Test Structure

```
tests/
├── conftest.py              # Pytest fixtures
├── test_auth.py             # Authentication tests
├── test_products.py         # Product endpoints
├── test_orders.py           # Order management
├── test_documents.py        # Document generation
└── test_analytics.py        # Analytics endpoints
```

## 🚀 Deployment

### Production Checklist

- [ ] Environment variables configured
- [ ] Database migrations applied
- [ ] SSL/TLS certificates configured
- [ ] CORS origins set to production domains
- [ ] Email SMTP credentials configured
- [ ] Secrets management implemented
- [ ] Docker security hardening applied
- [ ] Health check endpoint tested
- [ ] Backup strategy implemented
- [ ] Monitoring and logging configured
- [ ] Rate limiting configured (if needed)

### Deployment Options

#### Option 1: Docker Swarm

```bash
docker swarm init
docker stack deploy -f docker-compose.prod.yml nour-distribution
```

#### Option 2: Docker Compose (Simplified)

```bash
docker-compose -f docker-compose.prod.yml up -d
```

#### Option 3: Kubernetes

Convert Docker Compose to Kubernetes manifests using Kompose:

```bash
kompose convert -f docker-compose.prod.yml
kubectl apply -f .
```

#### Option 4: Cloud Platforms

- **AWS ECS/Fargate**: Use AWS Secrets Manager
- **Azure Container Instances**: Use Azure Key Vault
- **Google Cloud Run**: Use Secret Manager

See `SECRETS_MANAGEMENT_GUIDE.md` for platform-specific guides.

### Environment-Specific Configs

- **Development**: `docker-compose.yml`
- **Production**: `docker-compose.prod.yml` (security hardened)
- **Staging**: Create `docker-compose.staging.yml` as needed

## 📊 Monitoring & Logging

### Health Check

```bash
curl http://localhost:8000/health
```

Response:
```json
{
  "status": "healthy",
  "timestamp": "2026-01-08T16:00:00",
  "docs_available": true
}
```

### Logs

```bash
# Docker logs
docker compose logs -f backend

# Application logs (if using file logging)
tail -f logs/app.log
```

### Recommended Tools

- **Prometheus** - Metrics collection
- **Grafana** - Metrics visualization
- **ELK Stack** - Log aggregation (Elasticsearch, Logstash, Kibana)
- **Sentry** - Error tracking
- **New Relic** - APM (Application Performance Monitoring)

## 🤝 Contributing

Contributions are welcome! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Contribution Guidelines

- Write tests for new features
- Update documentation as needed
- Follow existing code style and patterns
- Add migration files for database changes
- Ensure all tests pass before submitting PR

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 👥 Authors

- **Ayoub Oueslati** - *Initial work* - [GitHub Profile](https://github.com/ayouboueslati)

## 🙏 Acknowledgments

- FastAPI framework and community
- PostgreSQL and SQLAlchemy teams
- Tunisian business community for requirements feedback
- All contributors and testers

## 📞 Support

For support and questions:

- **Email**: support@nour-distribution.com
- **Issues**: [GitHub Issues](https://github.com/ayouboueslati/nour-distribution-backend/issues)
- **Documentation**: http://localhost:8000/docs

## 🗺 Roadmap

### Version 1.1 (Q1 2026)
- [ ] GraphQL API support
- [ ] Real-time notifications via WebSockets
- [ ] Advanced reporting and dashboards
- [ ] Multi-warehouse support

### Version 1.2 (Q2 2026)
- [ ] Mobile API optimization
- [ ] Barcode scanning integration
- [ ] Automated backup system
- [ ] Multi-currency support

### Version 2.0 (Q3 2026)
- [ ] Multi-tenant architecture
- [ ] Advanced analytics with ML predictions
- [ ] Integration with accounting software
- [ ] Mobile apps (iOS/Android)

---

**Built with ❤️ for the Tunisian distribution industry**

*For detailed security documentation, see the security guides in the project root.*
