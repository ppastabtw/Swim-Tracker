from django.contrib import admin
from .models import ScrapeJob, ScrapeJobLog


class ScrapeJobLogInline(admin.TabularInline):
    model = ScrapeJobLog
    extra = 0
    readonly_fields = ['timestamp']


@admin.register(ScrapeJob)
class ScrapeJobAdmin(admin.ModelAdmin):
    list_display = ['id', 'job_type', 'source', 'status', 'triggered_by', 'created_at', 'completed_at']
    list_filter = ['status', 'source', 'job_type', 'triggered_by']
    search_fields = ['id', 'celery_task_id']
    readonly_fields = ['id', 'created_at']
    inlines = [ScrapeJobLogInline]


@admin.register(ScrapeJobLog)
class ScrapeJobLogAdmin(admin.ModelAdmin):
    list_display = ['job', 'level', 'message', 'timestamp']
    list_filter = ['level']
    search_fields = ['message']
