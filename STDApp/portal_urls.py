from django.urls import path

from . import portal_views as p

urlpatterns = [
    path("student/", p.student_dashboard, name="student_dashboard"),
    path("student/courses/", p.student_courses, name="student_courses"),
    path("student/attendance/", p.student_attendance, name="student_attendance"),
    path("student/routine/", p.student_routine, name="student_routine"),
    path("student/fees/", p.student_fees, name="student_fees"),

    path("teacher/", p.teacher_dashboard, name="teacher_dashboard"),
    path("teacher/courses/", p.teacher_courses, name="teacher_courses"),
    path("teacher/attendance/", p.teacher_attendance, name="teacher_attendance"),
    path("teacher/routine/", p.teacher_routine, name="teacher_routine"),
    path("teacher/report/", p.teacher_report, name="teacher_report"),
]
