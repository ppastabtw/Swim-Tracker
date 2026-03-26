# TODO: Define swimmer domain models
# See IMPLEMENTATION_PLAN.md — Database Schema section for full field specs
#
# Models to implement:
#   - Swimmer
#   - SwimmerSource
#   - Team
#   - SwimmerTeamMembership
#   - Meet
#   - Event
#   - SwimTime
#   - RecruitingProfile
import uuid
from django.db import models

class Swimmer(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('unknown', 'Unknown'),
    ]

    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    full_name = models.CharField(max_length=255)
    birth_year = models.IntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, default='unknown')
    nationality = models.CharField(max_length=3, default='USA')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.full_name

    class Meta:
        ordering = ['full_name']


class SwimmerSource(models.Model):
    SOURCE_CHOICES = [
        ('swimcloud', 'SwimCloud'),
        ('swimrankings', 'SwimRankings'),
        ('usaswimming', 'USA Swimming'),
        ('fina', 'FINA'),
    ]

    swimmer = models.ForeignKey(Swimmer, on_delete=models.CASCADE, related_name='sources')
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    external_id = models.CharField(max_length=255)
    profile_url = models.URLField(null=True, blank=True)
    last_scraped_at = models.DateTimeField(null=True, blank=True)
    raw_data = models.JSONField(default=dict)

    def __str__(self):
        return f'{self.swimmer.full_name} — {self.source}'

    class Meta:
        unique_together = [('source', 'external_id')]


class Team(models.Model):
    TEAM_TYPE_CHOICES = [
        ('high_school', 'High School'),
        ('club', 'Club'),
        ('college', 'College'),
        ('national', 'National'),
    ]

    name = models.CharField(max_length=255)
    short_name = models.CharField(max_length=50, blank=True)
    team_type = models.CharField(max_length=20, choices=TEAM_TYPE_CHOICES)
    country = models.CharField(max_length=3, default='USA')
    state = models.CharField(max_length=10, blank=True)

    def __str__(self):
        return self.name

    class Meta:
        ordering = ['name']


class SwimmerTeamMembership(models.Model):
    swimmer = models.ForeignKey(Swimmer, on_delete=models.CASCADE, related_name='memberships')
    team = models.ForeignKey(Team, on_delete=models.CASCADE, related_name='memberships')
    season_year = models.IntegerField()
    is_current = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.swimmer.full_name} — {self.team.name} ({self.season_year})'

    class Meta:
        unique_together = [('swimmer', 'team', 'season_year')]


class Meet(models.Model):
    COURSE_CHOICES = [
        ('SCY', 'Short Course Yards'),
        ('SCM', 'Short Course Meters'),
        ('LCM', 'Long Course Meters'),
    ]
    MEET_TYPE_CHOICES = [
        ('dual', 'Dual'),
        ('invitational', 'Invitational'),
        ('conference', 'Conference'),
        ('championship', 'Championship'),
        ('olympic', 'Olympic'),
    ]

    name = models.CharField(max_length=255)
    start_date = models.DateField()
    end_date = models.DateField()
    course = models.CharField(max_length=3, choices=COURSE_CHOICES)
    meet_type = models.CharField(max_length=30, choices=MEET_TYPE_CHOICES)
    location_city = models.CharField(max_length=100)
    location_state = models.CharField(max_length=10, blank=True)
    location_country = models.CharField(max_length=3, default='USA')
    source = models.CharField(max_length=20, blank=True)
    external_id = models.CharField(max_length=255, blank=True)

    def __str__(self):
        return f'{self.name} ({self.start_date})'

    class Meta:
        ordering = ['-start_date']
        constraints = [
            models.UniqueConstraint(
                fields=['source', 'external_id'],
                condition=models.Q(external_id__gt=''),
                name='unique_meet_source_external_id',
            ),
        ]


class Event(models.Model):
    STROKE_CHOICES = [
        ('freestyle', 'Freestyle'),
        ('backstroke', 'Backstroke'),
        ('breaststroke', 'Breaststroke'),
        ('butterfly', 'Butterfly'),
        ('individual_medley', 'Individual Medley'),
    ]

    distance = models.IntegerField()
    stroke = models.CharField(max_length=20, choices=STROKE_CHOICES)
    relay = models.BooleanField(default=False)
    gender = models.CharField(max_length=10)

    def __str__(self):
        relay_str = 'Relay ' if self.relay else ''
        return f'{self.distance} {relay_str}{self.stroke.title()}'

    class Meta:
        unique_together = [('distance', 'stroke', 'relay', 'gender')]


class SwimTime(models.Model):
    swimmer = models.ForeignKey(Swimmer, on_delete=models.CASCADE, related_name='times')
    meet = models.ForeignKey(Meet, on_delete=models.CASCADE, related_name='times')
    event = models.ForeignKey(Event, on_delete=models.CASCADE, related_name='times')
    time_seconds = models.DecimalField(max_digits=10, decimal_places=4)
    time_display = models.CharField(max_length=20)
    heat = models.IntegerField(null=True, blank=True)
    lane = models.IntegerField(null=True, blank=True)
    place = models.IntegerField(null=True, blank=True)
    dq = models.BooleanField(default=False)
    splits = models.JSONField(null=True, blank=True)
    source = models.CharField(max_length=20)
    scraped_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f'{self.swimmer.full_name} — {self.event} — {self.time_display}'

    class Meta:
        unique_together = [('swimmer', 'meet', 'event', 'time_seconds')]
        indexes = [
            models.Index(fields=['swimmer', 'event', 'time_seconds']),
        ]


class RecruitingProfile(models.Model):
    swimmer = models.OneToOneField(Swimmer, on_delete=models.CASCADE, related_name='recruiting_profile')
    graduation_year = models.IntegerField(null=True, blank=True)
    high_school = models.CharField(max_length=255, blank=True)
    home_state = models.CharField(max_length=10, blank=True)
    verbal_commit_date = models.DateField(null=True, blank=True)
    signed_date = models.DateField(null=True, blank=True)
    committed_to_team = models.ForeignKey(Team, on_delete=models.SET_NULL, null=True, blank=True)
    power_index = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    last_updated = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f'{self.swimmer.full_name} — Recruiting Profile'
