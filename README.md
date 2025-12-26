# Flask App Template

A production-ready Flask template with built-in security, authentication, and user management.

## Features

- **Authentication**: Email/Password login, Google OAuth, Password Recovery (todo).
- **User Management**: Admin interface to create, edit, and delete users.
- **Security**:
    - CSRF Protection (Flask-WTF)
    - Rate Limiting (Flask-Limiter)
    - Anti-Brute Force Protection
    - New IP Detection & MFA Email
- **Database**: SQLAlchemy ORM (SQLite for dev, easily switchable to PostgreSQL/MySQL).
- **UI**: Bootstrap 5 with valid HTML5 templates.
- **Logging**: ECS-style JSON logging and rotating file handler.

## Setup

1. **Clone the repository**:
   ```bash
   git clone <repository_url>
   cd Flask-Template
   ```

2. **Create virtual environment**:
   ```bash
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Variables**:
   Copy `.env.example` to `.env` and configure your keys.
   ```bash
   cp .env.example .env
   ```

5. **Initialize Database**:
   The app will automatically create tables on the first run.

6. **Create Admin User**:
   ```bash
   flask init-admin
   ```

7. **Run the application**:
   ```bash
   flask run
   ```

## Structure

- `src/`: Application source code.
    - `models.py`: Database models (currently `Usuario` and `UserKnownIP`).
    - `routes/`: Blueprints for logical grouping of routes.
    - `templates/`: Jinja2 templates.
- `tests/`: Pytest suite.

## Customization

- **Add Routes**: Create a new blueprint in `src/routes/` and register it in `src/__init__.py`.
- **Add Models**: Define new models in `src/models.py`.
- **Change UI**: Modify `templates/base.html` or `static/css/styles.css`.
