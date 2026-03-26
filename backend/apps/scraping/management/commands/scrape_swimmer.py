from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.swimmers.models import Swimmer, SwimmerSource, Meet, Event, SwimTime
from apps.scraping.models import ScrapeJob, ScrapeJobLog
from scrapers.swimcloud import SwimCloudAdapter
from scrapers.swimrankings import SwimRankingsAdapter
from scrapers.normalizers import (
    normalize_swimmer,
    normalize_meet,
    normalize_event,
    normalize_swim_time,
)


ADAPTERS = {
    'swimcloud': SwimCloudAdapter,
    'swimrankings': SwimRankingsAdapter,
}


class Command(BaseCommand):
    help = 'Scrape a swimmer by external ID from a given source'

    def add_arguments(self, parser):
        parser.add_argument('--source', type=str, default='swimcloud', choices=ADAPTERS.keys())
        parser.add_argument('--id', type=str, required=True, help='External swimmer ID on the source platform')

    def handle(self, *args, **options):
        source = options['source']
        external_id = options['id']

        # Create a ScrapeJob to track this run
        job = ScrapeJob.objects.create(
            job_type='swimmer_times',
            source=source,
            status='running',
            parameters={'external_id': external_id},
            triggered_by='admin',
            started_at=timezone.now(),
        )
        self._log(job, 'info', f'Starting scrape for {source} swimmer {external_id}')

        try:
            adapter = ADAPTERS[source]()
            raw_data = adapter.get_swimmer_times(external_id)
        except Exception as e:
            self._fail(job, f'Adapter error: {e}')
            raise CommandError(str(e))

        # Upsert swimmer
        raw_swimmer = raw_data.get('swimmer', {})
        swimmer_kwargs = normalize_swimmer(raw_swimmer, source)

        swimmer_source = SwimmerSource.objects.filter(
            source=source, external_id=external_id,
        ).select_related('swimmer').first()

        if swimmer_source:
            swimmer = swimmer_source.swimmer
            # Update fields if we got better data
            if swimmer_kwargs['full_name'] and swimmer_kwargs['full_name'] != str(external_id):
                swimmer.full_name = swimmer_kwargs['full_name']
            if swimmer_kwargs['birth_year']:
                swimmer.birth_year = swimmer_kwargs['birth_year']
            if swimmer_kwargs['gender'] != 'unknown':
                swimmer.gender = swimmer_kwargs['gender']
            if swimmer_kwargs['nationality'] and swimmer_kwargs['nationality'] != 'USA':
                swimmer.nationality = swimmer_kwargs['nationality']
            swimmer.save()
            self._log(job, 'info', f'Updated existing swimmer: {swimmer.full_name}')
        else:
            swimmer = Swimmer.objects.create(**swimmer_kwargs)
            SwimmerSource.objects.create(
                swimmer=swimmer,
                source=source,
                external_id=external_id,
                raw_data=raw_data.get('swimmer', {}),
            )
            self._log(job, 'info', f'Created new swimmer: {swimmer.full_name}')

        # Update last_scraped_at
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
                self._log(job, 'warning', f'Skipping meet with no date: {meet_kwargs["name"]}')
                continue

            # Don't include empty external_id in defaults — it violates unique constraint
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

        # Mark job as success
        job.status = 'success'
        job.completed_at = timezone.now()
        job.result_summary = {
            'times_created': times_created,
            'times_skipped': times_skipped,
            'meets_created': meets_created,
        }
        job.save()

        self._log(job, 'info',
            f'Done: {times_created} times created, {times_skipped} skipped, {meets_created} new meets')
        self.stdout.write(self.style.SUCCESS(
            f'Successfully scraped swimmer {external_id}: '
            f'{times_created} times, {meets_created} meets'
        ))

    def _log(self, job, level, message):
        ScrapeJobLog.objects.create(job=job, level=level, message=message)
        self.stdout.write(message)

    def _fail(self, job, error_msg):
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.error_detail = error_msg
        job.save()
        self._log(job, 'error', error_msg)
