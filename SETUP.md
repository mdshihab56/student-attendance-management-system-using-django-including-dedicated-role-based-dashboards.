# Student Attendance System — Setup

## Windows
1. Install Python 3.11–3.13.
2. Open a terminal in this folder.
3. Create and activate a virtual environment:
   ```powershell
   py -m venv .venv
   .\.venv\Scripts\Activate.ps1
   python -m pip install --upgrade pip
   pip install -r requirements.txt
   ```
4. Run database migrations and start the site:
   ```powershell
   python manage.py migrate
   python manage.py check
   python manage.py runserver
   ```
5. Open http://127.0.0.1:8000/

## Admin panel
Create an admin user with `python manage.py createsuperuser`, then set the user's `role` to `admin` through Django admin or the database. The management panel is at `/panel/`.

## Email OTP
Set `RESEND_API_KEY` as an environment variable before running the server. Configure a verified sender address with `DEFAULT_FROM_EMAIL`. Never commit API keys or production secrets.

## Production
Set `DJANGO_DEBUG=0`, use a newly generated `DJANGO_SECRET_KEY`, configure `DJANGO_ALLOWED_HOSTS`, and follow Django's deployment checklist. The fallback development key is not suitable for deployment.
