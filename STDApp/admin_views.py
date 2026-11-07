from datetime import timedelta
from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied, ValidationError
from django.db import IntegrityError, transaction
from django.db.models import Count, ProtectedError, Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import (
    Attendance,
    ClassRoutine,
    ClassSchedule,
    Course,
    CourseAssignment,
    Department,
    Fee,
    Student,
    faculties as Faculty,
)

User = get_user_model()

ROLE_ADMIN = "admin"
ROLE_STUDENT = "student"
ROLE_TEACHER = "teacher"

PRESENT_LIKE = ("present", "late")
LOW_ATTENDANCE_LIMIT = 75


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def admin_required(view):
    """Only logged-in admins (role == 'admin') or superusers can open the panel."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        user = request.user
        if user.is_superuser or getattr(user, "role", "") == ROLE_ADMIN:
            return view(request, *args, **kwargs)
        raise PermissionDenied

    return login_required(wrapper)


def _pct(part, total):
    return round(part * 100 / total) if total else 0


def _run(request, action, ok_message):
    """Run a DB action safely and flash a success / error message."""
    try:
        with transaction.atomic():
            action()
        messages.success(request, ok_message)
        return True
    except ProtectedError:
        messages.error(request, "This record is linked with other data, so it cannot be deleted.")
    except IntegrityError:
        messages.error(request, "This record already exists or conflicts with existing data.")
    except (KeyError, ValueError, TypeError, ArithmeticError, ValidationError, ObjectDoesNotExist) as exc:
        text = str(exc) if isinstance(exc, ValueError) and exc.args else "Invalid or missing data. Please check the form."
        messages.error(request, text)
    return False


# ----------------------------------------------------------------------------
# 1. dashboard
# ----------------------------------------------------------------------------
@admin_required
def dashboard(request):
    today = timezone.localdate()
    todays = Attendance.objects.filter(date=today)
    total = todays.count()
    present = todays.filter(status="present").count()
    late = todays.filter(status="late").count()
    absent = todays.filter(status="absent").count()

    context = {
        "total_students": Student.objects.count(),
        "total_teachers": Faculty.objects.count(),
        "total_courses": Course.objects.count(),
        "total_departments": Department.objects.count(),
        "attendance_pct": _pct(present + late, total),
        "att_total": total,
        "att_present": present,
        "att_late": late,
        "att_absent": absent,
        "today": today,
    }
    return render(request, "admin_panel/dashboard.html", context)


# ----------------------------------------------------------------------------
# 2. students
# ----------------------------------------------------------------------------
@admin_required
def manage_students(request):
    q = request.GET.get("q", "").strip()
    dept = request.GET.get("department", "").strip()

    students = Student.objects.select_related("user", "department").order_by("student_id")
    if q:
        students = students.filter(
            Q(student_id__icontains=q)
            | Q(user__username__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
        )
    if dept.isdigit():
        students = students.filter(department_id=int(dept))

    month_ago = timezone.now() - timedelta(days=30)
    context = {
        "students": students,
        "departments": Department.objects.order_by("code"),
        "q": q,
        "dept": dept,
        "total": Student.objects.count(),
        "active": Student.objects.filter(user__is_active=True).count(),
        "new_count": Student.objects.filter(user__date_joined__gte=month_ago).count(),
    }
    return render(request, "admin_panel/students.html", context)


@admin_required
def person_form(request, kind, pk=None):
    """One view for adding / editing a student or a teacher."""
    is_student = kind == "student"
    model = Student if is_student else Faculty
    obj = get_object_or_404(model.objects.select_related("user"), pk=pk) if pk else None
    back = "panel_students" if is_student else "panel_teachers"

    if obj:
        values = {
            "username": obj.user.username,
            "first_name": obj.user.first_name,
            "last_name": obj.user.last_name,
            "email": obj.user.email,
            "department": str(obj.department_id),
            "phone": obj.phone,
        }
        if is_student:
            values["student_id"] = obj.student_id
            values["semester"] = obj.semester
    else:
        values = {"semester": 1}

    if request.method == "POST":
        values = request.POST.dict()
        try:
            with transaction.atomic():
                username = values.get("username", "").strip()
                if not username:
                    raise ValueError("Username is required.")
                user = obj.user if obj else None
                clash = User.objects.filter(username__iexact=username)
                if user:
                    clash = clash.exclude(pk=user.pk)
                if clash.exists():
                    raise ValueError("This username is already taken.")

                password = values.get("password", "")
                if not obj and not password:
                    raise ValueError("Password is required for a new account.")

                if not obj:
                    user = User(role=ROLE_STUDENT if is_student else ROLE_TEACHER, email_verified=True)
                user.username = username
                user.first_name = values.get("first_name", "").strip()
                user.last_name = values.get("last_name", "").strip()
                user.email = values.get("email", "").strip()
                if password:
                    user.set_password(password)
                user.save()

                profile = obj or model(user=user)
                profile.department_id = int(values.get("department") or 0)
                profile.phone = values.get("phone", "").strip()
                if is_student:
                    student_id = values.get("student_id", "").strip()
                    if not student_id:
                        raise ValueError("Student ID is required.")
                    profile.student_id = student_id
                    profile.semester = int(values.get("semester") or 1)
                profile.save()

            messages.success(request, "Saved successfully.")
            return redirect(back)
        except ValueError as exc:
            messages.error(request, str(exc))
        except IntegrityError:
            messages.error(request, "Username or Student ID already exists, or the department is invalid.")

    context = {
        "kind": kind,
        "is_student": is_student,
        "obj": obj,
        "v": values,
        "departments": Department.objects.order_by("code"),
        "back": back,
    }
    return render(request, "admin_panel/person_form.html", context)


@admin_required
def student_toggle(request, pk):
    if request.method == "POST":
        student = get_object_or_404(Student.objects.select_related("user"), pk=pk)
        student.user.is_active = not student.user.is_active
        student.user.save(update_fields=["is_active"])
        messages.success(request, "Student status updated.")
    return redirect("panel_students")


@admin_required
def student_delete(request, pk):
    if request.method == "POST":
        student = get_object_or_404(Student.objects.select_related("user"), pk=pk)
        _run(request, student.user.delete, "Student deleted.")
    return redirect("panel_students")


# ----------------------------------------------------------------------------
# 3. teachers
# ----------------------------------------------------------------------------
@admin_required
def manage_teachers(request):
    q = request.GET.get("q", "").strip()
    teachers = (
        Faculty.objects.select_related("user", "department")
        .annotate(course_count=Count("courseassignment", distinct=True))
        .order_by("user__first_name", "user__username")
    )
    if q:
        teachers = teachers.filter(
            Q(user__username__icontains=q)
            | Q(user__first_name__icontains=q)
            | Q(user__last_name__icontains=q)
            | Q(phone__icontains=q)
        )
    context = {
        "teachers": teachers,
        "q": q,
        "total": Faculty.objects.count(),
        "active": Faculty.objects.filter(user__is_active=True).count(),
        "assigned": CourseAssignment.objects.count(),
    }
    return render(request, "admin_panel/teachers.html", context)


@admin_required
def teacher_toggle(request, pk):
    if request.method == "POST":
        teacher = get_object_or_404(Faculty.objects.select_related("user"), pk=pk)
        teacher.user.is_active = not teacher.user.is_active
        teacher.user.save(update_fields=["is_active"])
        messages.success(request, "Teacher status updated.")
    return redirect("panel_teachers")


@admin_required
def teacher_delete(request, pk):
    if request.method == "POST":
        teacher = get_object_or_404(Faculty.objects.select_related("user"), pk=pk)
        _run(request, teacher.user.delete, "Teacher deleted.")
    return redirect("panel_teachers")


# ----------------------------------------------------------------------------
# 4. courses & departments
# ----------------------------------------------------------------------------
@admin_required
def manage_courses(request):
    if request.method == "POST":
        d = request.POST
        action = d.get("action")

        if action == "add_department":
            def run():
                name, code = d["name"].strip(), d["code"].strip().upper()
                if not name or not code:
                    raise ValueError("Department name and code are required.")
                Department.objects.create(name=name, code=code)

            _run(request, run, "Department added.")

        elif action == "add_course":
            def run():
                cname, code = d["Cname"].strip(), d["code"].strip().upper()
                if not cname or not code:
                    raise ValueError("Course title and code are required.")
                Course.objects.create(
                    department_id=int(d["department"]),
                    Cname=cname,
                    code=code,
                    credit=float(d.get("credit") or 3),
                )

            _run(request, run, "Course added.")

        elif action == "delete_course":
            _run(request, lambda: Course.objects.filter(pk=d["id"]).delete(), "Course deleted.")

        elif action == "delete_department":
            def run():
                dept = Department.objects.get(pk=d["id"])
                if dept.student_set.exists() or dept.course_set.exists() or dept.faculties_set.exists():
                    raise ValueError("This department still has students, teachers or courses.")
                dept.delete()

            _run(request, run, "Department deleted.")

        return redirect("panel_courses")

    q = request.GET.get("q", "").strip()
    courses = Course.objects.select_related("department").order_by("department__code", "code")
    if q:
        courses = courses.filter(Q(code__icontains=q) | Q(Cname__icontains=q))

    context = {
        "courses": courses,
        "departments": Department.objects.annotate(
            n_students=Count("student", distinct=True),
            n_courses=Count("course", distinct=True),
        ).order_by("code"),
        "q": q,
        "total_credits": Course.objects.aggregate(t=Sum("credit"))["t"] or 0,
    }
    return render(request, "admin_panel/courses.html", context)


# ----------------------------------------------------------------------------
# 5. assign courses & schedule
# ----------------------------------------------------------------------------
@admin_required
def manage_assignments(request):
    if request.method == "POST":
        d = request.POST
        action = d.get("action")

        if action == "add_assignment":
            _run(
                request,
                lambda: CourseAssignment.objects.create(
                    faculties_id=int(d["faculty"]),
                    Courses_id=int(d["course"]),
                    Semester=d.get("semester", "").strip(),
                    session=d.get("session", "").strip(),
                ),
                "Course assigned to teacher.",
            )

        elif action == "add_schedule":
            def run():
                if d["start_time"] >= d["end_time"]:
                    raise ValueError("End time must be after start time.")
                ClassSchedule.objects.create(
                    course_assignment_id=int(d["assignment"]),
                    day=d["day"],
                    start_time=d["start_time"],
                    end_time=d["end_time"],
                    room=d.get("room", "").strip(),
                )

            _run(request, run, "Class schedule added.")

        elif action == "delete_assignment":
            _run(request, lambda: CourseAssignment.objects.filter(pk=d["id"]).delete(), "Assignment deleted.")

        elif action == "delete_schedule":
            _run(request, lambda: ClassSchedule.objects.filter(pk=d["id"]).delete(), "Schedule deleted.")

        return redirect("panel_assignments")

    assignments = (
        CourseAssignment.objects.select_related("faculties__user", "Courses__department")
        .prefetch_related("schedules")
        .order_by("Courses__code")
    )
    context = {
        "assignments": assignments,
        "teachers": Faculty.objects.select_related("user").order_by("user__first_name", "user__username"),
        "courses": Course.objects.order_by("code"),
        "days": ClassSchedule.DAYS,
    }
    return render(request, "admin_panel/assignments.html", context)


# ----------------------------------------------------------------------------
# 6. attendance management
# ----------------------------------------------------------------------------
@admin_required
def manage_attendance(request):
    today = timezone.localdate()
    source = request.POST if request.method == "POST" else request.GET
    assignment_id = source.get("assignment", "")
    the_date = parse_date(source.get("date") or "") or today

    assignment = None
    if assignment_id.isdigit():
        assignment = (
            CourseAssignment.objects.select_related("faculties__user", "Courses__department")
            .filter(pk=int(assignment_id))
            .first()
        )

    rows = []
    summary = {"present": 0, "late": 0, "absent": 0}
    if assignment:
        students = (
            Student.objects.filter(department=assignment.Courses.department)
            .select_related("user")
            .order_by("student_id")
        )
        semester = (assignment.Semester or "").strip()
        if semester.isdigit():
            students = students.filter(semester=int(semester))

        valid = {"present", "absent", "late"}

        if request.method == "POST":
            with transaction.atomic():
                for s in students:
                    status = request.POST.get(f"status_{s.pk}")
                    if status not in valid:
                        continue
                    Attendance.objects.update_or_create(
                        student=s,
                        course_assignment=assignment,
                        date=the_date,
                        defaults={
                            "status": status,
                            "marked_by": assignment.faculties,
                            "remarks": request.POST.get(f"remarks_{s.pk}", "").strip()[:200],
                        },
                    )
            messages.success(request, "Attendance saved.")
            return redirect(f"{reverse('panel_attendance')}?assignment={assignment.pk}&date={the_date.isoformat()}")

        existing = {r.student_id: r for r in Attendance.objects.filter(course_assignment=assignment, date=the_date)}
        for s in students:
            record = existing.get(s.pk)
            status = record.status if record else "present"
            if record:
                summary[status] = summary.get(status, 0) + 1
            rows.append(
                {
                    "student": s,
                    "status": status,
                    "remarks": record.remarks if record else "",
                    "saved": record is not None,
                }
            )

    recent = Attendance.objects.select_related(
        "student__user", "course_assignment__Courses", "marked_by__user"
    ).order_by("-date", "-updated_at")
    if assignment:
        recent = recent.filter(course_assignment=assignment)
    recent = recent[:25]

    context = {
        "assignments": CourseAssignment.objects.select_related("faculties__user", "Courses").order_by("Courses__code"),
        "assignment": assignment,
        "assignment_id": assignment_id,
        "the_date": the_date,
        "rows": rows,
        "summary": summary,
        "recent": recent,
    }
    return render(request, "admin_panel/attendance.html", context)


# ----------------------------------------------------------------------------
# 7. fees
# ----------------------------------------------------------------------------
@admin_required
def manage_fees(request):
    if request.method == "POST":
        d = request.POST
        action = d.get("action")

        if action == "add_fee":
            def run():
                amount = Decimal(d["amount"])
                paid = Decimal(d.get("paid_amount") or "0")
                if amount <= 0 or paid < 0 or paid > amount:
                    raise ValueError("Amount must be positive and paid amount cannot exceed it.")
                Fee.objects.create(
                    student_id=int(d["student"]),
                    semester=int(d["semester"]),
                    amount=amount,
                    paid_amount=paid,
                    due_date=parse_date(d.get("due_date") or "") or None,
                )

            _run(request, run, "Fee record added.")

        elif action == "pay":
            def run():
                fee = Fee.objects.get(pk=d["id"])
                payment = Decimal(d["amount"])
                if payment <= 0:
                    raise ValueError("Payment must be greater than zero.")
                fee.paid_amount = min(fee.amount, fee.paid_amount + payment)
                fee.save(update_fields=["paid_amount"])

            _run(request, run, "Payment recorded.")

        elif action == "delete":
            _run(request, lambda: Fee.objects.filter(pk=d["id"]).delete(), "Fee record deleted.")

        return redirect("panel_fees")

    status = request.GET.get("status", "").strip()
    q = request.GET.get("q", "").strip()
    fees_qs = Fee.objects.select_related("student__user", "student__department").order_by("-due_date", "-id")
    if q:
        fees_qs = fees_qs.filter(Q(student__student_id__icontains=q) | Q(student__user__username__icontains=q))

    today = timezone.localdate()
    fees = []
    for fee in fees_qs:
        if status and fee.payment_status != status:
            continue
        fee.percent = _pct(fee.paid_amount, fee.amount)
        fee.overdue = bool(fee.due_date and fee.due_date < today and fee.due_amount > 0)
        fees.append(fee)

    totals = Fee.objects.aggregate(total=Sum("amount"), paid=Sum("paid_amount"))
    total = totals["total"] or Decimal("0")
    paid = totals["paid"] or Decimal("0")

    context = {
        "fees": fees,
        "status": status,
        "q": q,
        "total": total,
        "paid": paid,
        "due": total - paid,
        "students": Student.objects.select_related("user").order_by("student_id"),
    }
    return render(request, "admin_panel/fees.html", context)


# ----------------------------------------------------------------------------
# 8. class & exam routine
# ----------------------------------------------------------------------------
@admin_required
def manage_routines(request):
    if request.method == "POST":
        d = request.POST
        action = d.get("action")

        if action == "add":
            def run():
                if d["start_time"] >= d["end_time"]:
                    raise ValueError("End time must be after start time.")
                date_obj = parse_date(d.get("date") or "")
                day = d.get("day") or (date_obj.strftime("%A") if date_obj else "")
                assignment = CourseAssignment.objects.select_related("Courses").get(pk=d["assignment"])
                ClassRoutine.objects.create(
                    course_assignment=assignment,
                    routine_type=d.get("routine_type", "class"),
                    title=d.get("title", "").strip() or assignment.Courses.code,
                    date=date_obj,
                    day=day[:10],
                    start_time=d["start_time"],
                    end_time=d["end_time"],
                    room=d.get("room", "").strip(),
                )

            _run(request, run, "Routine published.")

        elif action == "delete":
            _run(request, lambda: ClassRoutine.objects.filter(pk=d["id"]).delete(), "Routine deleted.")

        return redirect("panel_routines")

    kind = request.GET.get("type", "").strip()
    routines = ClassRoutine.objects.select_related(
        "course_assignment__Courses", "course_assignment__faculties__user"
    ).order_by("date", "start_time")
    if kind in ("class", "exam"):
        routines = routines.filter(routine_type=kind)

    context = {
        "routines": routines,
        "kind": kind,
        "assignments": CourseAssignment.objects.select_related("faculties__user", "Courses").order_by("Courses__code"),
        "days": ClassSchedule.DAYS,
        "class_count": ClassRoutine.objects.filter(routine_type="class").count(),
        "exam_count": ClassRoutine.objects.filter(routine_type="exam").count(),
    }
    return render(request, "admin_panel/routines.html", context)


# ----------------------------------------------------------------------------
# 9. course plans & syllabus (course outline overview)
# ----------------------------------------------------------------------------
@admin_required
def course_plans(request):
    q = request.GET.get("q", "").strip()
    dept = request.GET.get("department", "").strip()

    courses = (
        Course.objects.select_related("department")
        .prefetch_related("courseassignment_set__faculties__user")
        .order_by("department__name", "code")
    )
    if q:
        courses = courses.filter(Q(code__icontains=q) | Q(Cname__icontains=q))
    if dept.isdigit():
        courses = courses.filter(department_id=int(dept))

    context = {
        "courses": courses,
        "departments": Department.objects.order_by("code"),
        "q": q,
        "dept": dept,
    }
    return render(request, "admin_panel/course_plans.html", context)


# ----------------------------------------------------------------------------
# 10. institutional reports
# ----------------------------------------------------------------------------
@admin_required
def reports(request):
    total = Attendance.objects.count()
    present = Attendance.objects.filter(status="present").count()
    late = Attendance.objects.filter(status="late").count()
    absent = Attendance.objects.filter(status="absent").count()

    per_course = []
    course_rows = (
        Attendance.objects.values("course_assignment__Courses__code", "course_assignment__Courses__Cname")
        .annotate(total=Count("id"), good=Count("id", filter=Q(status__in=PRESENT_LIKE)))
        .order_by("course_assignment__Courses__code")
    )
    for r in course_rows:
        per_course.append(
            {
                "code": r["course_assignment__Courses__code"],
                "name": r["course_assignment__Courses__Cname"],
                "total": r["total"],
                "pct": _pct(r["good"], r["total"]),
            }
        )

    low = []
    student_rows = Attendance.objects.values(
        "student_id", "student__student_id", "student__user__username", "student__user__first_name",
        "student__user__last_name",
    ).annotate(total=Count("id"), good=Count("id", filter=Q(status__in=PRESENT_LIKE)))
    for r in student_rows:
        pct = _pct(r["good"], r["total"])
        if pct < LOW_ATTENDANCE_LIMIT:
            full = f'{r["student__user__first_name"]} {r["student__user__last_name"]}'.strip()
            low.append(
                {
                    "sid": r["student__student_id"],
                    "name": full or r["student__user__username"],
                    "total": r["total"],
                    "pct": pct,
                }
            )
    low.sort(key=lambda x: x["pct"])

    fee_totals = Fee.objects.aggregate(total=Sum("amount"), paid=Sum("paid_amount"))
    fee_total = fee_totals["total"] or Decimal("0")
    fee_paid = fee_totals["paid"] or Decimal("0")

    context = {
        "att_total": total,
        "att_present": present,
        "att_late": late,
        "att_absent": absent,
        "att_pct": _pct(present + late, total),
        "per_course": per_course,
        "low": low,
        "low_limit": LOW_ATTENDANCE_LIMIT,
        "fee_total": fee_total,
        "fee_paid": fee_paid,
        "fee_due": fee_total - fee_paid,
        "fee_pct": _pct(fee_paid, fee_total),
        "departments": Department.objects.annotate(
            n_students=Count("student", distinct=True),
            n_teachers=Count("faculties", distinct=True),
            n_courses=Count("course", distinct=True),
        ).order_by("code"),
    }
    return render(request, "admin_panel/reports.html", context)
