from django.urls import path

from . import admin_views as v

urlpatterns = [
    path("", v.dashboard, name="panel_dashboard"),

    path("students/", v.manage_students, name="panel_students"),
    path("students/add/", v.person_form, {"kind": "student"}, name="panel_student_add"),
    path("students/<int:pk>/edit/", v.person_form, {"kind": "student"}, name="panel_student_edit"),
    path("students/<int:pk>/toggle/", v.student_toggle, name="panel_student_toggle"),
    path("students/<int:pk>/delete/", v.student_delete, name="panel_student_delete"),

    path("teachers/", v.manage_teachers, name="panel_teachers"),
    path("teachers/add/", v.person_form, {"kind": "teacher"}, name="panel_teacher_add"),
    path("teachers/<int:pk>/edit/", v.person_form, {"kind": "teacher"}, name="panel_teacher_edit"),
    path("teachers/<int:pk>/toggle/", v.teacher_toggle, name="panel_teacher_toggle"),
    path("teachers/<int:pk>/delete/", v.teacher_delete, name="panel_teacher_delete"),

    path("courses/", v.manage_courses, name="panel_courses"),
    path("assignments/", v.manage_assignments, name="panel_assignments"),
    path("attendance/", v.manage_attendance, name="panel_attendance"),
    path("fees/", v.manage_fees, name="panel_fees"),
    path("routines/", v.manage_routines, name="panel_routines"),
    path("course-plans/", v.course_plans, name="panel_course_plans"),
    path("reports/", v.reports, name="panel_reports"),
]