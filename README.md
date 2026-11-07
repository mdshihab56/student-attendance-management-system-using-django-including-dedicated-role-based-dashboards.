# Student Attendance Management System

A role-based academic management web application built with **Python and Django**. The system brings student records, teacher administration, course allocation, attendance, class schedules, academic reports, and fee monitoring into a unified platform with separate experiences for administrators, teachers, and students.

## Overview

The Student Attendance Management System is designed to make routine academic administration more organized and accessible. Instead of managing student information, course assignments, attendance records, class routines, and fee information in separate places, authorized users can work with the information through a centralized web application.

The application follows a role-based workflow:

- **Administrators** manage the academic structure and operational records.
- **Teachers** access assigned courses, record class attendance, view schedules, and review attendance reports.
- **Students** view their courses, attendance history, class routines, and fee information.

Each role receives a dedicated dashboard and navigation relevant to its responsibilities.

## Key Features

### Administrator panel
- Dashboard for an overview of academic activity.
- Create, view, update, activate/deactivate, and manage student records.
- Manage teacher/faculty records.
- Maintain departments and courses.
- Assign courses to faculty members with semester and session information.
- Manage attendance records.
- Create and manage class and examination routines.
- Maintain student fee records and payment status.
- Review attendance and academic reports.

### Teacher portal
- Dedicated teacher dashboard.
- View assigned courses and relevant student lists.
- Record attendance using **Present**, **Absent**, and **Late** statuses.
- Review teaching schedules and routines.
- Access attendance reports for assigned courses.

### Student portal
- Dedicated student dashboard.
- View enrolled/assigned courses.
- Review attendance records.
- View class and examination routines.
- Check semester fee records, paid amounts, outstanding balances, and payment status.

### Account and access
- User authentication with login and registration pages.
- Role-aware dashboards and navigation.
- Login-protected portal pages.
- Administrator views protected by an administrator access check.

## Use Case Diagram
<img width="2550" height="2079" alt="Student Attendance Management System - UML Use Case Diagram (A4 Printable)" src="https://github.com/user-attachments/assets/624196cf-8e91-46d1-aedc-9b2b661bbcf1" />

## Create Account Panel
<img width="1920" height="1080" alt="Screenshot (5160)" src="https://github.com/user-attachments/assets/0e17a464-7fe3-4cb4-a26c-f4b8ba9e0c12" />

## Login
<img width="1920" height="1080" alt="Screenshot (5161)" src="https://github.com/user-attachments/assets/64f61743-328e-4089-9da5-3fa1feeca06a" />
 Panel

## How the System Works

1. **Account access** - A user registers or signs in through the authentication interface.
2. **Role resolution** - The application checks the authenticated account's role and directs the user to the corresponding dashboard.
3. **Academic setup** - An administrator creates departments, courses, student and faculty profiles, and course assignments.
4. **Class organization** - Course assignments are connected to class schedules and class/examination routines.
5. **Attendance recording** - A teacher selects an assigned course and records each student's attendance for a date. The system stores the status, marker, date, and optional remarks.
6. **Record integrity** - The attendance model enforces one attendance entry per student, course assignment, and date, preventing duplicate records for the same class/date combination.
7. **Review and reporting** - Teachers review attendance reports, while students see their own attendance history. Administrators can review and manage attendance centrally.
8. **Fee visibility** - Administrators maintain fee and paid-amount values; students can view their fee balance and payment status.

## Technology Stack

| Layer | Technology |
|---|---|
| Backend framework | Python, Django |
| Application language | Python |
| Frontend rendering | Django Templates, HTML, CSS |
| Client-side behavior | JavaScript (where used in templates) |
| Database in the supplied configuration | SQLite |
| Authentication | Django authentication system with a custom user model |
| Email integration dependency | Resend Python SDK |
| Deployment target | Vercel (requires production configuration; see below) |

## Project Structure

```text
Class Attendance management System/
├── manage.py
├── requirements.txt
├── SETUP.md
├── .env.example
├── StudentAttProject/
│   ├── settings.py
│   ├── urls.py
│   ├── asgi.py
│   └── wsgi.py
└── STDApp/
    ├── models.py
    ├── views.py
    ├── admin_views.py
    ├── portal_views.py
    ├── urls.py
    ├── admin_urls.py
    ├── portal_urls.py
    ├── migrations/
    └── templates/
        ├── admin_panel/
        ├── portal/
        ├── login.html
        └── register.html
```

### Main data models

- `user` - Custom Django user with a role field.
- `Department` - Academic department information.
- `Course` - Course name, code, department, and credit value.
- `faculties` - Faculty profile linked to a user and department.
- `Student` - Student profile, student ID, department, and semester.
- `CourseAssignment` - Connects a faculty member with a course, semester, and session.
- `ClassSchedule` - Weekly schedule details for a course assignment.
- `Attendance` - Student attendance status, date, teacher marker, and remarks.
- `ClassRoutine` - Class and examination routine entries.
- `Fee` - Semester fee, paid amount, due date, and calculated payment status.


## Future Improvements

Possible next steps for the project include:

- PostgreSQL-backed production deployment.
- More granular permission policies and audit logs.
- Exportable attendance reports (CSV/PDF).
- Attendance percentage alerts and configurable thresholds.
- Improved analytics for course-wise and semester-wise attendance.
- Automated testing for role access and attendance workflows.

---

**Built with Python and Django.**
---
 Design & developed by Md.Shihab Sikder [CSE-22nd-C-220088] & Faria Akter Eva [CSE-22nd-C-220015]
