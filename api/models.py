from django.db import models
from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator, MaxValueValidator, RegexValidator
from django.utils.translation import gettext_lazy as _
from django.core.exceptions import ValidationError
from django.utils import timezone

phone_regex = RegexValidator(
    regex=r'^\+?1?\d{9,15}$',
    message=_("Phone number must be entered in the format: '+999999999'. Up to 15 digits allowed.")
)

def validate_future_date(value):
    if value > timezone.now():
        raise ValidationError(_('Date cannot be in the future'))

class User(AbstractUser):
    phone_number = models.CharField(
        max_length=15,
        unique=True,
        validators=[phone_regex],
        db_index=True,
        help_text=_("User's phone number in E.164 format")
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text=_("User's email address (optional)")
    )
    registration_timestamp = models.DateTimeField(
        auto_now_add=True,
        validators=[validate_future_date],
        help_text=_("When the user registered")
    )
    last_login = models.DateTimeField(
        auto_now=True,
        validators=[validate_future_date],
        help_text=_("Last login timestamp")
    )
    is_active = models.BooleanField(
        default=True,
        help_text=_("Whether this user should be treated as active.")
    )

    USERNAME_FIELD = 'phone_number'
    REQUIRED_FIELDS = ['username', 'first_name']

    class Meta:
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['first_name']),
            models.Index(fields=['email']),
            models.Index(fields=['is_active']),
        ]
        verbose_name = _('user')
        verbose_name_plural = _('users')

    def __str__(self):
        return f"{self.first_name} ({self.phone_number})"

    def clean(self):
        super().clean()
        if self.email and User.objects.exclude(pk=self.pk).filter(email=self.email).exists():
            raise ValidationError({'email': _('This email is already in use.')})

class Contact(models.Model):
    user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name='contacts',
        help_text=_("User who owns this contact")
    )
    name = models.CharField(
        max_length=100,
        db_index=True,
        help_text=_("Contact's name")
    )
    phone_number = models.CharField(
        max_length=15,
        validators=[phone_regex],
        db_index=True,
        help_text=_("Contact's phone number in E.164 format")
    )
    email = models.EmailField(
        blank=True,
        null=True,
        help_text=_("Contact's email address (optional)")
    )
    notes = models.TextField(
        blank=True,
        null=True,
        help_text=_("Additional notes about the contact")
    )
    tags = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_("Comma-separated tags")
    )
    groups = models.CharField(
        max_length=200,
        blank=True,
        null=True,
        help_text=_("Comma-separated groups")
    )
    privacy_settings = models.JSONField(
        default=dict,
        help_text=_("Privacy settings for the contact")
    )
    created_at = models.DateTimeField(
        auto_now_add=True,
        validators=[validate_future_date],
        help_text=_("When the contact was created")
    )
    updated_at = models.DateTimeField(
        auto_now=True,
        validators=[validate_future_date],
        help_text=_("When the contact was last updated")
    )

    class Meta:
        unique_together = ['user', 'phone_number']
        indexes = [
            models.Index(fields=['phone_number']),
            models.Index(fields=['name']),
            models.Index(fields=['user', 'phone_number']),
            models.Index(fields=['user', 'name']),
            models.Index(fields=['created_at']),
            models.Index(fields=['tags']),
            models.Index(fields=['groups']),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(phone_number=''),
                name='non_empty_phone_number'
            ),
            models.CheckConstraint(
                check=~models.Q(name=''),
                name='non_empty_name'
            )
        ]
        verbose_name = _('contact')
        verbose_name_plural = _('contacts')

    def __str__(self):
        return f"{self.name} ({self.phone_number})"

    def clean(self):
        super().clean()
        if self.phone_number == self.user.phone_number:
            raise ValidationError({
                'phone_number': _("You cannot add yourself as a contact.")
            })

class SpamReport(models.Model):
    REPORT_TYPES = [
        ('spam', _('Spam')),
        ('scam', _('Scam')),
        ('telemarketing', _('Telemarketing')),
        ('robocall', _('Robocall')),
        ('other', _('Other')),
    ]

    reported_number = models.CharField(
        max_length=15,
        validators=[phone_regex],
        db_index=True,
        help_text=_("The phone number being reported")
    )
    reporter = models.ForeignKey(
        User,
        on_delete=models.PROTECT,  # Don't delete reports if user is deleted
        related_name='spam_reports',
        help_text=_("User who made this report")
    )
    report_type = models.CharField(
        max_length=20,
        choices=REPORT_TYPES,
        help_text=_("Type of spam report")
    )
    details = models.TextField(
        blank=True,
        null=True,
        help_text=_("Additional details about the spam report")
    )
    evidence = models.FileField(
        upload_to='spam_evidence/%Y/%m/%d/',
        blank=True,
        null=True,
        help_text=_("Evidence file (optional)")
    )
    severity = models.IntegerField(
        validators=[MinValueValidator(1), MaxValueValidator(10)],
        help_text=_("Severity rating from 1 to 10")
    )
    timestamp = models.DateTimeField(
        auto_now_add=True,
        validators=[validate_future_date],
        help_text=_("When the report was created")
    )
    is_verified = models.BooleanField(
        default=False,
        help_text=_("Whether this report has been verified by moderators")
    )

    class Meta:
        indexes = [
            models.Index(fields=['reported_number']),
            models.Index(fields=['report_type']),
            models.Index(fields=['timestamp']),
            models.Index(fields=['reporter', 'reported_number']),
            models.Index(fields=['reported_number', 'severity']),
            models.Index(fields=['is_verified']),
        ]
        constraints = [
            models.CheckConstraint(
                check=~models.Q(reported_number=''),
                name='non_empty_reported_number'
            ),
            models.CheckConstraint(
                check=models.Q(severity__gte=1) & models.Q(severity__lte=10),
                name='valid_severity_range'
            ),
            models.UniqueConstraint(
                fields=['reporter', 'reported_number'],
                name='unique_reporter_number',
                condition=models.Q(timestamp__date=models.F('timestamp__date')),
                violation_error_message=_("You can only report a number once per day.")
            )
        ]
        verbose_name = _('spam report')
        verbose_name_plural = _('spam reports')

    def __str__(self):
        return f"Spam Report: {self.reported_number} ({self.report_type})"

    def clean(self):
        super().clean()
        if self.reported_number == self.reporter.phone_number:
            raise ValidationError({
                'reported_number': _("You cannot report your own number as spam.")
            }) 