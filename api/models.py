from django.db import models


class Batch(models.Model):
    batch_id = models.CharField(primary_key=True, max_length=12)
    batch_name = models.CharField(max_length=255, unique=True)
    created_by = models.ForeignKey(
        'UserMaster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='batches_created',
    )
    created_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'batch'
        verbose_name_plural = 'Batches'
        ordering = ['created_on']

    def __str__(self):
        return self.batch_name


class GroupFormation(models.Model):
    id = models.AutoField(primary_key=True)  # Explicit primary key
    STATUS_CHOICES = [
        ('Pending', 'Pending'),
        ('Approved', 'Approved'),
        ('Rejected', 'Rejected'),
    ]
    status = models.CharField(
        max_length=9,
        choices=STATUS_CHOICES,
        default='Pending',
    )
    finalized_idea = models.ForeignKey(
        'Idea',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='finalized_group_formations',
    )
    idea_1 = models.ForeignKey(
        'Idea',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='idea_1_group_formations',
    )
    idea_2 = models.ForeignKey(
        'Idea',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='idea_2_group_formations',
    )
    idea_3 = models.ForeignKey(
        'Idea',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='idea_3_group_formations',
    )

    class Meta:
        db_table = 'group_formation'
        verbose_name_plural = 'Group Formations'


class GroupStudents(models.Model):
    id = models.AutoField(primary_key=True)  # Added explicit primary key
    group = models.ForeignKey(
        GroupFormation,
        on_delete=models.CASCADE,
        related_name='group_students',
    )
    student_batch_link = models.ForeignKey(
        'StudentBatch',
        on_delete=models.CASCADE,
        related_name='group_students',
    )

    class Meta:
        db_table = 'group_students'
        unique_together = ('group', 'student_batch_link')


class Idea(models.Model):
    id = models.AutoField(primary_key=True)  # Added explicit primary key
    title = models.CharField(max_length=255)
    broad_area = models.CharField(max_length=255, blank=True, null=True)
    objective = models.TextField(blank=True, null=True)
    originality_innovativeness = models.TextField(blank=True, null=True)
    key_activities = models.TextField(blank=True, null=True)
    data_sources = models.TextField(blank=True, null=True)
    technology_usage = models.TextField(blank=True, null=True)
    scalability = models.TextField(blank=True, null=True)
    social_impact = models.TextField(blank=True, null=True)
    potent_users = models.TextField(blank=True, null=True)
    created_on = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'UserMaster',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='ideas_created',
    )

    class Meta:
        db_table = 'idea'
        ordering = ['-created_on']


class StudentBatch(models.Model):
    id = models.AutoField(primary_key=True)  # Added explicit primary key
    enrollment = models.ForeignKey(
        'StudentDetails',
        on_delete=models.CASCADE,
        related_name='student_batches',
    )
    previous_batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='previous_batches',
    )
    current_batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='current_batches',
    )
    transition_date = models.DateTimeField(blank=True, null=True)
    status = models.CharField(max_length=8, blank=True, null=True)

    class Meta:
        db_table = 'student_batch'


class StudentDetails(models.Model):
    enrollment_id = models.IntegerField(primary_key=True)  # Manual input, not auto-increment
    name = models.CharField(max_length=255)
    section = models.CharField(max_length=80, blank=True, null=True)
    mobile_no = models.CharField(max_length=10, unique=True)
    batch = models.ForeignKey(
        Batch,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='students',
    )

    class Meta:
        db_table = 'student_details'
        verbose_name_plural = 'Student Details'

    def __str__(self):
        return f"{self.name} ({self.enrollment_id})"


class UserMaster(models.Model):
    id = models.AutoField(primary_key=True)  # Added explicit primary key
    USER_TYPE_CHOICES = [
        ('Admin', 'Admin'),
        ('Student', 'Student'),
        ('Mentor', 'Mentor'),
    ]
    usertype = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='Student',
    )
    email = models.EmailField(unique=True)
    otp = models.CharField(max_length=6, blank=True, null=True)
    password = models.CharField(max_length=255)
    status = models.CharField(max_length=8, blank=True, null=True)
    created_on = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(
        'self',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='users_created',
    )

    class Meta:
        db_table = 'user_master'

    def __str__(self):
        return self.email
