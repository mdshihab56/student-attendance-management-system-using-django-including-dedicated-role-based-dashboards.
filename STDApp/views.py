from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout, get_user_model
from django.contrib import messages
from django.db.models import Q
from .models import Student, faculties  # আপনার প্রজেক্টের অ্যাপ অনুযায়ী মডেলগুলো ইমপোর্ট করে নেবেন

User = get_user_model()


# ---------------------------------------------------------------- login
def login_view(req):
    if req.method == 'POST':
        username = req.POST.get('username', '').strip()
        password = req.POST.get('password', '')
        role = (req.POST.get('Role') or '').strip().lower()

        user_obj = User.objects.filter(
            Q(username=username) | Q(email__iexact=username)
        ).first()

        user = authenticate(req, username=user_obj.username, password=password) if user_obj else None

        if user is None:
            messages.error(req, 'Invalid username or password!')
            return render(req, 'login.html')

        # Admin: superuser or role == admin
        if role == 'admin' and (user.is_superuser or user.role == 'admin'):
            login(req, user)
            return redirect('panel_dashboard')

        # Student / Teacher
        if not user.is_superuser and user.role == role and role in ('student', 'teacher'):
            login(req, user)
            return redirect('teacher_dashboard' if role == 'teacher' else 'student_dashboard')

        messages.error(req, 'Invalid username, password or role!')

    return render(req, 'login.html')


# ------------------------------------------------------------- register
def register_view(req):
    if req.method == 'POST':
        full_name = req.POST.get('full_name', '').strip()
        username = req.POST.get('username', '').strip()
        email = req.POST.get('email', '').strip()
        password = req.POST.get('password', '')
        confirm_password = req.POST.get('confirm_password', '')
        role = req.POST.get('role', 'student')

        if role not in ('student', 'teacher'):
            role = 'student'

        if not username or not email or not password:
            return render(req, 'register.html', {'error': 'Please fill in all required fields.'})

        if password != confirm_password:
            return render(req, 'register.html', {'error': 'Passwords do not match.'})

        if User.objects.filter(username__iexact=username).exists():
            return render(req, 'register.html', {'error': 'Username already exists.'})

        if User.objects.filter(email__iexact=email).exists():
            return render(req, 'register.html', {'error': 'Email already registered.'})

        first, _, last = full_name.partition(' ')


        new_user = User.objects.create_user(
            username=username,
            email=email,
            password=password,
            first_name=first,
            last_name=last,
            role=role,  # আপনার models.py এর user মডেলে role ফিল্ড আছে
        )

        # ২. যদি আপনি চান ইউজার রেজিস্টার হওয়ার সাথে সাথেই Student বা faculties টেবিলের এন্ট্রি তৈরি হয়ে যাক (অপশনাল)
        # if role == 'student':
        #     Student.objects.create(user=new_user, student_id=f"STU-{new_user.id}", department_id=1) 
        # elif role == 'teacher':
        #     faculties.objects.create(user=new_user, department_id=1)

        messages.success(req, 'Account created. Please sign in.')
        return redirect('login')

    return render(req, 'register.html')


# ------------------------------------------------ otp (no longer used)
def verify_otp_view(req):
    return redirect('login')


# --------------------------------------------------------------- logout
def logout_view(request):
    logout(request)
    return redirect('login')