# Taskly Project

This is a Django-based **project management tool** called **Taskly**.

---
## Prerequisites

- Python 3.9+
- MySQL 5.7+ or MariaDB
- pip (Python package manager)
- Git (optional)
---

## Setup Instructions

1. **Clone the repository** (if using Git):

    ```bash
    git clone <your-repo-url>
    cd taskly
    ```

2. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

3. **Setup environment variables:**
    - Look for the .env.example file in the project directory.
    - Create a new `.env` file:
    ```bash
    cp .env.example .env   # Linux/macOS
    copy .env.example .env # Windows
    ```
    - Open the `.env` and insert your values for database, secret key, etc.

4. **Run Migration:**
    ```bash
    python manage.py makemigrations
    python manage.py migrate
    ```

5. **Run the server:**
    ```bash
    python manage.py runserver
    ```
    visit `http://127.0.0.1:8000` in your browser.