from decimal import Decimal
from functools import wraps

from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.db import transaction
from django.db.models import Count, Q, Sum
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils import timezone
from django.utils.dateparse import parse_date

from .models import (
    Attendance,
    ClassRoutine,
    ClassSchedule,
    CourseAssignment,
    Fee,
    Student,
    faculties as Faculty,
)

PRESENT_LIKE = ("present", "late")
LOW_ATTENDANCE_LIMIT = 75
DAY_ORDER = {day: i for i, (day, _) in enumerate(ClassSchedule.DAYS)}


# ----------------------------------------------------------------------------
# helpers
# ----------------------------------------------------------------------------
def _pct(part, total):
    return round(part * 100 / total) if total else 0


def _show(request, kind, template, context):
    context["kind"] = kind
    return render(request, template, context)


def student_required(view):
    """Logged-in user with role 'student' and a Student profile."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if getattr(request.user, "role", "") != "student":
            raise PermissionDenied
        student = (
            Student.objects.select_related("user", "department").filter(user=request.user).first()
        )
        if not student:
            return _show(request, "student", "portal/no_profile.html", {})
        return view(request, student, *args, **kwargs)

    return login_required(wrapper)


def teacher_required(view):
    """Logged-in user with role 'teacher' and a teacher (faculties) profile."""

    @wraps(view)
    def wrapper(request, *args, **kwargs):
        if getattr(request.user, "role", "") != "teacher":
            raise PermissionDenied
        teacher = (
            Faculty.objects.select_related("user", "department").filter(user=request.user).first()
        )
        if not teacher:
            return _show(request, "teacher", "portal/no_profile.html", {})
        return view(request, teacher, *args, **kwargs)

    return login_required(wrapper)


def _student_assignments(student):
    """Course assignments of the student's department (and semester when set)."""
    base = CourseAssignment.objects.filter(Courses__department=student.department)
    ids = []
    for a in base:
        sem = (a.Semester or "").strip()
        if not sem.isdigit() or int(sem) == student.semester:
            ids.append(a.pk)
    return (
        CourseAssignment.objects.filter(pk__in=ids)
        .select_related("faculties__user", "Courses__department")
        .prefetch_related("schedules")
        .order_by("Courses__code")
    )


def _students_of(assignment):
    students = (
        Student.objects.filter(department=assignment.Courses.department)
        .select_related("user")
        .order_by("student_id")
    )
    sem = (assignment.Semester or "").strip()
    if sem.isdigit():
        students = students.filter(semester=int(sem))
    return students


def _by_day(schedules):
    groups = {}
    for s in schedules:
        groups.setdefault(s.day, []).append(s)
    ordered = sorted(groups.items(), key=lambda kv: DAY_ORDER.get(kv[0], 99))
    return [(day, sorted(items, key=lambda s: s.start_time)) for day, items in ordered]


# ----------------------------------------------------------------------------
# STUDENT PORTAL
# ----------------------------------------------------------------------------
@student_required
def student_dashboard(request, student):
    today = timezone.localdate()
    assignments = _student_assignments(student)

    records = Attendance.objects.filter(student=student)
    total = records.count()
    good = records.filter(status__in=PRESENT_LIKE).count()

    fee_totals = Fee.objects.filter(student=student).aggregate(t=Sum("amount"), p=Sum("paid_amount"))
    due = (fee_totals["t"] or Decimal("0")) - (fee_totals["p"] or Decimal("0"))

    todays_classes = (
        ClassSchedule.objects.filter(course_assignment__in=assignments, day=today.strftime("%A"))
        .select_related("course_assignment__Courses", "course_assignment__faculties__user")
        .order_by("start_time")
    )
    upcoming_exams = ClassRoutine.objects.filter(
        course_assignment__in=assignments, routine_type="exam", date__gte=today
    ).count()

    context = {
        "student": student,
        "course_count": assignments.count(),
        "attendance_pct": _pct(good, total),
        "att_total": total,
        "due": due,
        "upcoming_exams": upcoming_exams,
        "todays_classes": todays_classes,
        "today": today,
    }
    return _show(request, "student", "portal/student_dashboard.html", context)


@student_required
def student_courses(request, student):
    return _show(
        request,
        "student",
        "portal/student_courses.html",
        {"student": student, "assignments": _student_assignments(student)},
    )


@student_required
def student_attendance(request, student):
    assignments = _student_assignments(student)
    stats = {
        r["course_assignment_id"]: r
        for r in Attendance.objects.filter(student=student)
        .values("course_assignment_id")
        .annotate(
            total=Count("id"),
            present=Count("id", filter=Q(status="present")),
            late=Count("id", filter=Q(status="late")),
            absent=Count("id", filter=Q(status="absent")),
        )
    }
    rows = []
    for a in assignments:
        r = stats.get(a.pk, {"total": 0, "present": 0, "late": 0, "absent": 0})
        pct = _pct(r["present"] + r["late"], r["total"])
        rows.append(
            {
                "assignment": a,
                "total": r["total"],
                "present": r["present"],
                "late": r["late"],
                "absent": r["absent"],
                "pct": pct,
                "low": r["total"] > 0 and pct < LOW_ATTENDANCE_LIMIT,
            }
        )

    recent = (
        Attendance.objects.filter(student=student)
        .select_related("course_assignment__Courses")
        .order_by("-date", "-updated_at")[:20]
    )
    return _show(
        request,
        "student",
        "portal/student_attendance.html",
        {"student": student, "rows": rows, "recent": recent, "low_limit": LOW_ATTENDANCE_LIMIT},
    )


@student_required
def student_routine(request, student):
    today = timezone.localdate()
    assignments = _student_assignments(student)
    schedules = ClassSchedule.objects.filter(course_assignment__in=assignments).select_related(
        "course_assignment__Courses"
    )
    routines = (
        ClassRoutine.objects.filter(course_assignment__in=assignments)
        .filter(Q(date__isnull=True) | Q(date__gte=today))
        .select_related("course_assignment__Courses", "course_assignment__faculties__user")
        .order_by("date", "start_time")
    )
    return _show(
        request,
        "student",
        "portal/routine.html",
        {"groups": _by_day(schedules), "routines": routines, "today": today},
    )


@student_required
def student_fees(request, student):
    today = timezone.localdate()
    fees = list(Fee.objects.filter(student=student).order_by("-semester", "-id"))
    for f in fees:
        f.percent = _pct(f.paid_amount, f.amount)
        f.overdue = bool(f.due_date and f.due_date < today and f.due_amount > 0)
    total = sum((f.amount for f in fees), Decimal("0"))
    paid = sum((f.paid_amount for f in fees), Decimal("0"))
    return _show(
        request,
        "student",
        "portal/student_fees.html",
        {"fees": fees, "total": total, "paid": paid, "due": total - paid, "student": student},
    )


# ----------------------------------------------------------------------------
# TEACHER PORTAL
# ----------------------------------------------------------------------------
def _my_assignments(teacher):
    return (
        CourseAssignment.objects.filter(faculties=teacher)
        .select_related("Courses__department", "faculties__user")
        .prefetch_related("schedules")
        .order_by("Courses__code")
    )


@teacher_required
def teacher_dashboard(request, teacher):
    today = timezone.localdate()
    assignments = _my_assignments(teacher)

    student_ids = set()
    for a in assignments:
        student_ids.update(_students_of(a).values_list("pk", flat=True))

    todays_classes = (
        ClassSchedule.objects.filter(course_assignment__in=assignments, day=today.strftime("%A"))
        .select_related("course_assignment__Courses")
        .order_by("start_time")
    )
    marked_today = (
        Attendance.objects.filter(course_assignment__in=assignments, date=today)
        .values("course_assignment")
        .distinct()
        .count()
    )
    upcoming_exams = ClassRoutine.objects.filter(
        course_assignment__in=assignments, routine_type="exam", date__gte=today
    ).count()

    context = {
        "teacher": teacher,
        "course_count": assignments.count(),
        "student_count": len(student_ids),
        "marked_today": marked_today,
        "upcoming_exams": upcoming_exams,
        "todays_classes": todays_classes,
        "today": today,
    }
    return _show(request, "teacher", "portal/teacher_dashboard.html", context)


@teacher_required
def teacher_courses(request, teacher):
    assignments = list(_my_assignments(teacher))
    for a in assignments:
        a.student_count = _students_of(a).count()
    return _show(
        request,
        "teacher",
        "portal/teacher_courses.html",
        {"teacher": teacher, "assignments": assignments},
    )


@teacher_required
def teacher_attendance(request, teacher):
    today = timezone.localdate()
    source = request.POST if request.method == "POST" else request.GET
    assignment_id = source.get("assignment", "")
    the_date = parse_date(source.get("date") or "") or today

    assignment = None
    if assignment_id.isdigit():
        assignment = _my_assignments(teacher).filter(pk=int(assignment_id)).first()

    rows = []
    summary = {"present": 0, "late": 0, "absent": 0}
    if assignment:
        students = _students_of(assignment)
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
                            "marked_by": teacher,
                            "remarks": request.POST.get(f"remarks_{s.pk}", "").strip()[:200],
                        },
                    )
            messages.success(request, "Attendance saved.")
            return redirect(
                f"{reverse('teacher_attendance')}?assignment={assignment.pk}&date={the_date.isoformat()}"
            )

        existing = {
            r.student_id: r
            for r in Attendance.objects.filter(course_assignment=assignment, date=the_date)
        }
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

    context = {
        "assignments": _my_assignments(teacher),
        "assignment": assignment,
        "assignment_id": assignment_id,
        "the_date": the_date,
        "rows": rows,
        "summary": summary,
    }
    return _show(request, "teacher", "portal/teacher_attendance.html", context)


@teacher_required
def teacher_routine(request, teacher):
    today = timezone.localdate()
    assignments = _my_assignments(teacher)
    schedules = ClassSchedule.objects.filter(course_assignment__in=assignments).select_related(
        "course_assignment__Courses"
    )
    routines = (
        ClassRoutine.objects.filter(course_assignment__in=assignments)
        .filter(Q(date__isnull=True) | Q(date__gte=today))
        .select_related("course_assignment__Courses", "course_assignment__faculties__user")
        .order_by("date", "start_time")
    )
    return _show(
        request,
        "teacher",
        "portal/routine.html",
        {"groups": _by_day(schedules), "routines": routines, "today": today},
    )


@teacher_required
def teacher_report(request, teacher):
    assignment_id = request.GET.get("assignment", "")
    assignment = None
    if assignment_id.isdigit():
        assignment = _my_assignments(teacher).filter(pk=int(assignment_id)).first()

    rows = []
    if assignment:
        stats = {
            r["student_id"]: r
            for r in Attendance.objects.filter(course_assignment=assignment)
            .values("student_id")
            .annotate(total=Count("id"), good=Count("id", filter=Q(status__in=PRESENT_LIKE)))
        }
        for s in _students_of(assignment):
            r = stats.get(s.pk, {"total": 0, "good": 0})
            pct = _pct(r["good"], r["total"])
            rows.append(
                {
                    "student": s,
                    "total": r["total"],
                    "pct": pct,
                    "low": r["total"] > 0 and pct < LOW_ATTENDANCE_LIMIT,
                }
            )
        rows.sort(key=lambda x: (x["total"] == 0, x["pct"]))

    return _show(
        request,
        "teacher",
        "portal/teacher_report.html",
        {
            "assignments": _my_assignments(teacher),
            "assignment": assignment,
            "assignment_id": assignment_id,
            "rows": rows,
            "low_limit": LOW_ATTENDANCE_LIMIT,
        },
    )
