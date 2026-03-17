from django.db import models
from django.contrib.auth.models import AbstractBaseUser, BaseUserManager, PermissionsMixin

# Stage -1
class Batch(models.Model):
    batch_id = models.AutoField(primary_key=True)
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
    id = models.AutoField(primary_key=True) 
    is_freeze = models.BooleanField(default=False) 
    STATUS_CHOICES = [
        ('Active', 'Active'),
        ('Inactive', 'Inactive'),
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
    id = models.AutoField(primary_key=True) 
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
    enrollment_id = models.IntegerField(primary_key=True)  
    user = models.OneToOneField(  # New ForeignKey to UserMaster
        'UserMaster', 
        on_delete=models.CASCADE, 
        null=True, 
        blank=True,
        related_name='student_details'
    )
    name = models.CharField(max_length=255)
    section = models.CharField(max_length=80, blank=True, null=True)
    mobile_no = models.CharField(max_length=10, unique=True, null=True)
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


# This is for test purpose only
class UserManager(BaseUserManager):
    def create_user(self, email, password=None, **extra_fields):
        if not email:
            raise ValueError("Email is required")
        email = self.normalize_email(email)
        user = self.model(email=email, **extra_fields)
        user.set_password(password)
        user.save(using=self._db)
        return user

    def create_superuser(self, email, password=None, **extra_fields):
        extra_fields.setdefault('is_staff', True)
        extra_fields.setdefault('is_superuser', True)
        return self.create_user(email, password, **extra_fields)


class UserMaster(AbstractBaseUser, PermissionsMixin):
    id = models.AutoField(primary_key=True)
    enrollment_id = models.IntegerField(unique=True, null=True, blank=True)  # New field for Student Enrollment ID
    USER_TYPE_CHOICES = [
        ('Admin', 'Admin'),
        ('Student', 'Student'),
        ('Guide', 'Guide'),
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
    is_active = models.BooleanField(default=True)
    is_staff = models.BooleanField(default=False)

    objects = UserManager()

    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = []

    class Meta:
        db_table = 'user_master'

    def __str__(self):
        return self.email
    
# Token traking table
class TokenTracking(models.Model):
    user = models.ForeignKey(UserMaster, on_delete=models.CASCADE, related_name="tokens")
    access_token = models.CharField(max_length=1024)  
    refresh_token = models.CharField(max_length=1024)  
    ip_address = models.GenericIPAddressField()
    access_expires_at = models.DateTimeField()
    refresh_expires_at = models.DateTimeField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Token for {self.user.email}"
    
    class Meta:
        db_table = 'token_tracking'

# ----------------------------------------------------------------------------------------

# Models for stage 2 - Guide registration and group allocation and idea finalization

# ----------------------------------------------------------------------------------------
class Guide(models.Model):
    id = models.AutoField(primary_key=True)
    user = models.OneToOneField(
        UserMaster,
        on_delete=models.CASCADE,
        related_name='guide_profile',
        limit_choices_to={'usertype': 'Guide'}
    )
    name = models.CharField(max_length=255)  
    status = models.CharField(max_length=20)
    mobile_no = models.CharField(max_length=10, unique=True, null=True)

    class Meta:
        db_table = 'guide'

    def __str__(self):
        return self.name


class Expertise(models.Model):
    id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True, null=True)

    class Meta:
        db_table = 'expertise'
        verbose_name_plural = 'Expertise'

    def __str__(self):
        return self.title


class GuideExpertise(models.Model):
    id = models.AutoField(primary_key=True)
    guide = models.ForeignKey(
        Guide,
        on_delete=models.CASCADE,
        related_name='expertise_links'
    )
    expertise = models.ForeignKey(
        Expertise,
        on_delete=models.CASCADE,
        related_name='guide_links'
    )

    class Meta:
        db_table = 'guide_expertise'
        unique_together = ('guide', 'expertise')
        verbose_name_plural = 'Guide Expertise'

    def __str__(self):
        return f"{self.guide.name} - {self.expertise.title}"


class GuideProjectInterest(models.Model):
    id = models.AutoField(primary_key=True)
    class Priority(models.TextChoices):
        P1 = "P1", "Priority 1"
        P2 = "P2", "Priority 2"
        P3 = "P3", "Priority 3"
    guide = models.ForeignKey(
        Guide,
        on_delete=models.CASCADE,
        related_name='project_interests'
    )
    group = models.ForeignKey(
        GroupFormation,
        on_delete=models.CASCADE,
        related_name='interested_guides'
    )
    priority = models.CharField(
        max_length=2,
        choices=Priority.choices
    )

    class Meta:
        db_table = 'guide_project_interest'
        unique_together = ('guide', 'group')
        ordering = ['priority']

    def __str__(self):
        return f"{self.guide.name} -> Group {self.group.id} (Priority {self.priority})"


class GuideGroup(models.Model):
    id = models.AutoField(primary_key=True)
    guide = models.ForeignKey(
        Guide,
        on_delete=models.CASCADE,
        related_name='assigned_groups'
    )
    group = models.ForeignKey(
        GroupFormation,
        on_delete=models.CASCADE,
        related_name='assigned_guides'
    )
    assigned_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'guide_group'
        unique_together = ('guide', 'group')

    def __str__(self):
        return f"Guide {self.guide.name} assigned to Group {self.group.id}"




# ----------------------------------------------------------------------------------------

# Models for stage 3 - Logbook & meeting Management

# ----------------------------------------------------------------------------------------

class LogMaster(models.Model):
     # Table: meeting_logs
    log_id = models.AutoField(primary_key=True)  
    # Primary key, auto-increment

    group_id = models.ForeignKey(
        GroupFormation,              # Foreign Key connection with group_formation
        on_delete=models.CASCADE,    # Delete logs if the group is deleted
        related_name="meeting_logs"
    )

    changes_suggested_prev = models.TextField(
        max_length=2000,
        blank=True, null=True,
        help_text="Text area to store changes suggested in the previous meeting"
    )

    changes_done_prev = models.TextField(
        max_length=2000,
        blank=False, null=False,
        help_text="Text area to store changes completed from the previous meeting"
    )

    suggested_changes_next = models.TextField(
        max_length=2000,
        blank=False, null=False,
        help_text="Text area to store suggested changes for the next meeting"
    )

    guide_remarks = models.TextField(
        max_length=2000,
        blank=False, null=False,
        help_text="Text area for guide’s remarks about the meeting or project progress"
    )

    approval_status = models.BooleanField(
        default=False,
        help_text="Boolean field to mark approval status (True = Approved, False = Pending)"
    )

    created_by = models.ForeignKey(
        'UserMaster',                  # Foreign Key connection with user_master
        on_delete=models.CASCADE,    # Delete logs if user is deleted
        related_name="created_meeting_logs"
    )

    created_at = models.DateTimeField(
        auto_now_add=True,
        help_text="Timestamp when the log entry was created"
    )
    
    class Meta:
        db_table = 'log_master'
        ordering = ["group_id", "log_id"] 

    def __str__(self):
        return f"Log {self.log_id} - Group {self.group.group_id}"

# ----------------------------------------------------------------------------------------

# Models for stage 5 - Document submissions, reviews and approvals

# ----------------------------------------------------------------------------------------

class SubmissionWindow(models.Model):
    id = models.AutoField(primary_key=True)
    name = models.CharField(max_length=100)  
    description = models.TextField(blank=True)
    batch = models.ForeignKey(
        'Batch',
        on_delete=models.SET_NULL,
        null=True,
        related_name="submissions"
    )
    submission_start = models.DateTimeField()
    submission_end = models.DateTimeField()
    is_active = models.BooleanField(default=True)
    created_on = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'submission_window'

    def __str__(self):
        return f"{self.name} is created on {self.created_on}"
    
class DocumentStatus(models.TextChoices):
    SUBMITTED="submitted","document submitted"
    GUIDE_REVISION="guide_revision","guide asked revision document"
    GUIDE_APPROVED="guide_approved","guide approved document"
    ADMIN_REVISION="admin_revision","admin asked revision document"
    ADMIN_APPROVED="admin_approved","admin approved document"

class ProjectDocument(models.Model):
    id = models.AutoField(primary_key=True)
    submission = models.ForeignKey(
        SubmissionWindow,
        on_delete=models.CASCADE,
        related_name="documents"
    )
    group = models.ForeignKey(
        'GroupFormation',
        on_delete=models.CASCADE,
        related_name='documents'
    )
    version = models.IntegerField()
    file = models.FileField(upload_to="project_documents/")
    status = models.CharField(
        max_length=20,
        choices=DocumentStatus.choices,
        default=DocumentStatus.SUBMITTED
    )
    is_latest = models.BooleanField(default=True)
    uploaded_by = models.ForeignKey(
        'UserMaster',
        on_delete=models.SET_NULL,
        null=True,
        related_name='uploaded_documents'
    )
    uploaded_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'project_document'
    
class DocumentComment(models.Model):

    ROLE_CHOICES = [
        ("GUIDE", "Guide"),
        ("ADMIN", "Admin"),
    ]

    id = models.AutoField(primary_key=True)
    document = models.ForeignKey(
        ProjectDocument,
        on_delete=models.CASCADE,
        related_name='comments'
    )
    commented_by = models.ForeignKey(
        'UserMaster',
        on_delete=models.SET_NULL,
        null=True,
        related_name='comments'
    )
    role = models.CharField(max_length=10, choices=ROLE_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        db_table = 'document_comment'

class SubmissionStatus(models.Model):

    submission = models.ForeignKey(
        SubmissionWindow,
        on_delete=models.CASCADE,
        related_name="statuses"
    )
    group = models.ForeignKey(
        'GroupFormation',
        on_delete=models.CASCADE
    )
    approved_document = models.ForeignKey(
        ProjectDocument,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    HARD_COPY_STATUS = [
        ("NOT_REQUIRED", "Not Required"),
        ("REQUESTED", "Requested"),
        ("SUBMITTED", "Submitted"),
        ("VERIFIED", "Verified"),
    ]
    hardcopy_status = models.CharField(
        max_length=20,
        choices=HARD_COPY_STATUS,
        default="NOT_REQUIRED"
    )
    hardcopy_requested_at = models.DateTimeField(null=True, blank=True)
    hardcopy_submitted_at = models.DateTimeField(null=True, blank=True)
    hardcopy_verified_at = models.DateTimeField(null=True, blank=True)
    submitted_by = models.ForeignKey(
        'UserMaster',
        on_delete=models.SET_NULL,
        null=True
    )
    submitted_on = models.DateTimeField(null=True, blank=True)
    updated_on = models.DateTimeField(auto_now=True)

    class Meta:
        db_table = 'submission_status'


