from celery import shared_task
from django.utils import timezone

from apps.swimmers.models import Swimmer, SwimmerSource, Meet, Event, SwimTime, Team, SwimmerTeamMembership
from apps.scraping.models import ScrapeJob, ScrapeJobLog
from scrapers.swimcloud import SwimCloudAdapter
from scrapers.swimrankings import SwimRankingsAdapter
from scrapers.normalizers import normalize_swimmer, normalize_meet, normalize_event, normalize_swim_time


ADAPTERS = {
    'swimcloud': SwimCloudAdapter,
    'swimrankings': SwimRankingsAdapter,
}


def _log(job, level, message):
    ScrapeJobLog.objects.create(job=job, level=level, message=message)


def _ingest_swimmer_times(raw_data, source, external_id, job):
    """Shared ingestion logic used by tasks and management commands."""
    raw_swimmer = raw_data.get('swimmer', {})
    swimmer_kwargs = normalize_swimmer(raw_swimmer, source)

    # Upsert swimmer
    swimmer_source = SwimmerSource.objects.filter(
        source=source, external_id=external_id,
    ).select_related('swimmer').first()

    if swimmer_source:
        swimmer = swimmer_source.swimmer
        if swimmer_kwargs['full_name'] and swimmer_kwargs['full_name'] != str(external_id):
            swimmer.full_name = swimmer_kwargs['full_name']
        if swimmer_kwargs['birth_year']:
            swimmer.birth_year = swimmer_kwargs['birth_year']
        if swimmer_kwargs['gender'] != 'unknown':
            swimmer.gender = swimmer_kwargs['gender']
        if swimmer_kwargs['nationality'] and swimmer_kwargs['nationality'] != 'USA':
            swimmer.nationality = swimmer_kwargs['nationality']
        swimmer.save()
        _log(job, 'info', f'Updated existing swimmer: {swimmer.full_name}')
    else:
        swimmer = Swimmer.objects.create(**swimmer_kwargs)
        SwimmerSource.objects.create(
            swimmer=swimmer,
            source=source,
            external_id=external_id,
            raw_data=raw_data.get('swimmer', {}),
        )
        _log(job, 'info', f'Created new swimmer: {swimmer.full_name}')

    SwimmerSource.objects.filter(
        source=source, external_id=external_id,
    ).update(last_scraped_at=timezone.now())

    # Ingest times
    times_created = 0
    times_skipped = 0
    meets_created = 0

    for raw_meet in raw_data.get('meets', []):
        meet_kwargs = normalize_meet(raw_meet, source)

        if not meet_kwargs['start_date']:
            _log(job, 'warning', f'Skipping meet with no date: {meet_kwargs["name"]}')
            continue

        if not meet_kwargs.get('external_id'):
            meet_kwargs.pop('external_id', None)
            meet_kwargs.pop('source', None)

        meet, created = Meet.objects.get_or_create(
            name=meet_kwargs['name'],
            start_date=meet_kwargs['start_date'],
            course=meet_kwargs['course'],
            defaults=meet_kwargs,
        )
        if created:
            meets_created += 1

        for raw_time in raw_meet.get('times', []):
            event_kwargs = normalize_event(raw_time)
            event_kwargs['gender'] = swimmer.gender

            if not event_kwargs['distance']:
                continue

            event, _ = Event.objects.get_or_create(**event_kwargs)
            time_kwargs = normalize_swim_time(raw_time, source)

            if time_kwargs['time_seconds'] is None:
                times_skipped += 1
                continue

            _, created = SwimTime.objects.get_or_create(
                swimmer=swimmer,
                meet=meet,
                event=event,
                time_seconds=time_kwargs['time_seconds'],
                defaults=time_kwargs,
            )
            if created:
                times_created += 1
            else:
                times_skipped += 1

    return times_created, times_skipped, meets_created


@shared_task(bind=True, max_retries=3, rate_limit='10/m')
def scrape_swimmer_by_id(self, source: str, external_id: str, job_id: str = None):
    """Scrape a single swimmer's times from a source."""
    # Create or retrieve job
    if job_id:
        job = ScrapeJob.objects.get(id=job_id)
    else:
        job = ScrapeJob.objects.create(
            job_type='swimmer_times',
            source=source,
            status='running',
            parameters={'external_id': external_id},
            triggered_by='api',
            started_at=timezone.now(),
            celery_task_id=self.request.id or '',
        )

    job.status = 'running'
    job.started_at = timezone.now()
    job.celery_task_id = self.request.id or ''
    job.save()
    _log(job, 'info', f'Starting scrape for {source} swimmer {external_id}')

    try:
        adapter = ADAPTERS[source]()
        raw_data = adapter.get_swimmer_times(external_id)
    except Exception as exc:
        _log(job, 'error', f'Adapter error: {exc}')
        if self.request.retries < self.max_retries:
            job.status = 'pending'
            job.save()
            _log(job, 'warning', f'Retrying ({self.request.retries + 1}/{self.max_retries})')
            raise self.retry(countdown=60 * 2 ** self.request.retries, exc=exc)
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.error_detail = str(exc)
        job.save()
        return

    try:
        times_created, times_skipped, meets_created = _ingest_swimmer_times(
            raw_data, source, external_id, job,
        )
    except Exception as exc:
        _log(job, 'error', f'Ingestion error: {exc}')
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.error_detail = str(exc)
        job.save()
        return

    job.status = 'success'
    job.completed_at = timezone.now()
    job.result_summary = {
        'times_created': times_created,
        'times_skipped': times_skipped,
        'meets_created': meets_created,
    }
    job.save()
    _log(job, 'info', f'Done: {times_created} times, {meets_created} meets')


@shared_task(bind=True, max_retries=3, rate_limit='5/m')
def scrape_team_roster(self, source: str, team_id: str, gender: str = 'M', job_id: str = None):
    """Scrape a team roster and fan out to scrape each swimmer."""
    if job_id:
        job = ScrapeJob.objects.get(id=job_id)
    else:
        job = ScrapeJob.objects.create(
            job_type='team_roster',
            source=source,
            status='running',
            parameters={'team_id': team_id, 'gender': gender},
            triggered_by='api',
            started_at=timezone.now(),
            celery_task_id=self.request.id or '',
        )

    job.status = 'running'
    job.started_at = timezone.now()
    job.save()
    _log(job, 'info', f'Scraping {source} team roster {team_id} ({gender})')

    try:
        adapter = ADAPTERS[source]()
        roster = adapter.get_team_roster(team_id, gender=gender)
    except Exception as exc:
        _log(job, 'error', f'Adapter error: {exc}')
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.error_detail = str(exc)
        job.save()
        return

    _log(job, 'info', f'Found {len(roster)} swimmers on roster')

    # Fan out: scrape each swimmer as a separate task
    for swimmer_data in roster:
        ext_id = swimmer_data.get('external_id', '')
        if ext_id:
            scrape_swimmer_by_id.delay(source, ext_id)

    job.status = 'success'
    job.completed_at = timezone.now()
    job.result_summary = {'roster_count': len(roster)}
    job.save()


@shared_task
def nightly_update_active_swimmers():
    """Re-scrape swimmers not updated in the last 24 hours."""
    from datetime import timedelta
    cutoff = timezone.now() - timedelta(hours=24)
    stale_sources = SwimmerSource.objects.filter(
        last_scraped_at__lt=cutoff,
    ).select_related('swimmer')[:50]

    job = ScrapeJob.objects.create(
        job_type='bulk_import',
        source='mixed',
        status='running',
        parameters={'batch_size': len(stale_sources)},
        triggered_by='schedule',
        started_at=timezone.now(),
    )

    count = 0
    for ss in stale_sources:
        scrape_swimmer_by_id.delay(ss.source, ss.external_id)
        count += 1

    job.status = 'success'
    job.completed_at = timezone.now()
    job.result_summary = {'swimmers_queued': count}
    job.save()
    _log(job, 'info', f'Queued {count} swimmers for update')


@shared_task
def nightly_update_college_teams():
    """Re-scrape all college team rosters."""
    teams = Team.objects.filter(team_type='college')

    job = ScrapeJob.objects.create(
        job_type='team_roster',
        source='swimcloud',
        status='running',
        parameters={'team_count': teams.count()},
        triggered_by='schedule',
        started_at=timezone.now(),
    )

    count = 0
    for team in teams:
        # Get the team's external ID from SwimCloud if we have it
        for gender in ('M', 'F'):
            scrape_team_roster.delay('swimcloud', str(team.id), gender)
            count += 1

    job.status = 'success'
    job.completed_at = timezone.now()
    job.result_summary = {'roster_scrapes_queued': count}
    job.save()
    _log(job, 'info', f'Queued {count} roster scrapes')
