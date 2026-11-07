from django.db import models
from django.conf import settings
from django.contrib.auth.models import AbstractUser


class user(AbstractUser):
    role = models.CharField(max_length=20, default="student")
    email_verified = models.BooleanField(default=True)
    
class Department(models.Model):
    name = models.CharField(max_length=100) 
    code = models.CharField(max_length=20)

    def __str__(self):
        return self.name

    
class Course(models.Model):
    department = models.ForeignKey( Department, on_delete=models.CASCADE ) 
    Cname = models.CharField(max_length=150)
    code = models.CharField(max_length=30) 
    credit = models.FloatField(default=3)

    def __str__(self):
        return f"{self.code} - {self.Cname}"



    
class faculties(models.Model): 
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE)
    department = models.ForeignKey( Department, on_delete=models.CASCADE ) 
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return self.user.get_full_name() or self.user.username

    
class Student(models.Model): 
    user = models.OneToOneField(settings.AUTH_USER_MODEL,on_delete=models.CASCADE) 
    student_id = models.CharField(max_length=30, unique=True) 
    department = models.ForeignKey( Department, on_delete=models.CASCADE ) 
    semester = models.IntegerField(default=1) 
    phone = models.CharField(max_length=20, blank=True)

    def __str__(self):
        return f"{self.student_id} - {self.user.username}"


class CourseAssignment(models.Model):
    faculties = models.ForeignKey(
        faculties,
        on_delete=models.CASCADE
    )

    Courses = models.ForeignKey(
        Course,
        on_delete=models.CASCADE
    )

    Semester = models.CharField(max_length=20, blank=True)
    session = models.CharField(max_length=20, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['faculties', 'Courses', 'Semester', 'session'],
                name='unique_course_assignment'
            )
        ]

    def __str__(self):
        return f"{self.faculties} - {self.Courses.code}"

class ClassSchedule(models.Model):
    DAYS = [
        ('Saturday', 'Saturday'),
        ('Sunday', 'Sunday'),
        ('Monday', 'Monday'),
        ('Tuesday', 'Tuesday'),
        ('Wednesday', 'Wednesday'),
        ('Thursday', 'Thursday'),
        ('Friday', 'Friday'),
    ]

    course_assignment = models.ForeignKey(
        CourseAssignment,
        on_delete=models.CASCADE,
        related_name='schedules'
    )
    day = models.CharField(max_length=10, choices=DAYS)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return f"{self.course_assignment.Courses.code} - {self.day}"



class Attendance(models.Model):
    STATUS_CHOICES = [
        ('present', 'Present'),
        ('absent', 'Absent'),
        ('late', 'Late'),
    ]

    student = models.ForeignKey(Student,on_delete=models.CASCADE,related_name='attendance_records')
    course_assignment = models.ForeignKey(CourseAssignment,on_delete=models.CASCADE,related_name='attendance_records')
    date = models.DateField()
    status = models.CharField(max_length=10,choices=STATUS_CHOICES,default='absent')
    marked_by = models.ForeignKey(faculties,on_delete=models.PROTECT,related_name='marked_records')
    remarks = models.CharField(max_length=200, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=['student', 'course_assignment', 'date'],
                name='unique_student_course_date'
            )
        ]
        ordering = ['-date']

    def __str__(self):
        return (
            f"{self.student.student_id} - "
            f"{self.date} - {self.status}"
        )



class ClassRoutine(models.Model):
    ROUTINE_TYPES = [
        ('class', 'Class'),
        ('exam', 'Exam'),
    ]

    course_assignment = models.ForeignKey(CourseAssignment,on_delete=models.CASCADE,related_name='routines')
    routine_type = models.CharField(max_length=10,choices=ROUTINE_TYPES,default='class')
    title = models.CharField(max_length=150)
    date = models.DateField(null=True, blank=True)
    day = models.CharField(max_length=10, blank=True)
    start_time = models.TimeField()
    end_time = models.TimeField()
    room = models.CharField(max_length=30, blank=True)

    def __str__(self):
        return self.title



class Fee(models.Model):
    student = models.ForeignKey(Student,on_delete=models.CASCADE,related_name='fees')
    semester = models.PositiveIntegerField()
    amount = models.DecimalField(max_digits=10,decimal_places=2)
    paid_amount = models.DecimalField(max_digits=10,decimal_places=2,default=0)
    due_date = models.DateField(null=True, blank=True)

    def __str__(self):
        return f"{self.student.student_id} - Semester {self.semester}"

    @property
    def due_amount(self):
        return self.amount - self.paid_amount

    @property
    def payment_status(self):
        if self.paid_amount >= self.amount:
            return 'Paid'
        elif self.paid_amount > 0:
            return 'Partial'
        return 'Unpaid'
    

    

