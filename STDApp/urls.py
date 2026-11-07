from django.urls import path

from. import views

urlpatterns = [

    path('register/',views.register_view,name='register'),
    path('verify_otp/',views.verify_otp_view,name='verify_otp'),
    path('login/',views.login_view,name='login'),
    path('logout/',views.logout_view,name='logout'),

    # # Department
    # path('department/add/', views.add_department, name='add_department'),
    # path('departments/', views.department_list, name='department_list'),

    # # Course
    # path('course/add/', views.add_course, name='add_course'),
    # path('courses/', views.course_list, name='course_list'),

    # # Teacher
    # path('teacher/add/', views.add_teacher, name='add_teacher'),
    # path('teachers/', views.teacher_list, name='teacher_list'),

    # # Student
    # path('student/add/', views.add_student, name='add_student'),
    # path('students/', views.student_list, name='student_list'),
]