# TODO: Define scrape job tracking models
# See IMPLEMENTATION_PLAN.md — Database Schema section for full field specs
#
# Models to implement:
#   - ScrapeJob
#   - ScrapeJobLog

import uuid 
from django.db import models

class ScrapeJob(models.Model):
    JOB_TYPE_CHOICES = [
        ('swimmer_times', 'Swimmer Times'),
        ('team_roster', 'Team Roster'),
        ('meet_results', 'Meet Results'),
        ('bulk_import', 'Bulk Import'),
    ]
    SOURCE_CHOICES = [
        ('swimcloud', 'SwimCloud'),
        ('swimrankings', 'SwimRankings'),
        ('usaswimming', 'USA Swimming'),
        ('fina', 'FINA'),
    ]
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('running', 'Running'),
        ('success', 'Success'),
        ('failed', 'Failed'),
        ('partial', 'Partial'),
    ]
    TRIGGER_BY_CHOICES = [
        ('schedule', 'Schedule'),
        ('api', 'API'),
        ('admin', 'Admin'),
    ]
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    job_type = models.CharField(max_length=50, choices=JOB_TYPE_CHOICES)
    source = models.CharField(max_length=20, choices=SOURCE_CHOICES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES)
    parameters = models.JSONField(default=dict)
    result_summary = models.JSONField(null=True, blank=True)
    error_detail = models.TextField(blank=True)
    celery_task_id = models.CharField(max_length=255, blank=True)
    triggered_by = models.CharField(max_length=20, choices=TRIGGER_BY_CHOICES)
    created_at = models.DateTimeField(auto_now_add=True)
    started_at = models.DateTimeField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f'{self.job_type} ({self.status})'

    class Meta:
        ordering = ['-created_at']


class ScrapeJobLog(models.Model):
    LEVEL_CHOICES = [
        ('info', 'Info'),
        ('warning', 'Warning'),
        ('error', 'Error'),
    ]

    job = models.ForeignKey(ScrapeJob, on_delete=models.CASCADE, related_name='logs')
    level = models.CharField(max_length=10, choices=LEVEL_CHOICES, default='info')
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    extra = models.JSONField(null=True, blank=True)

    def __str__(self):
        return f'[{self.level.upper()}] {self.message[:50]}'

    class Meta:
        ordering = ['timestamp']