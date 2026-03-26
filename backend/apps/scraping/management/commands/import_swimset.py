from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from apps.swimmers.models import Swimmer, SwimmerSource, Meet, Event, SwimTime
from apps.scraping.models import ScrapeJob, ScrapeJobLog
from scrapers.swimset import SwimsetAdapter
from scrapers.normalizers import normalize_swim_time


class Command(BaseCommand):
    help = 'Import historical FINA/Olympic data from swimset JSON file'

    def add_arguments(self, parser):
        parser.add_argument('--file', type=str, required=True, help='Path to swimset JSON output file')

    def handle(self, *args, **options):
        file_path = options['file']

        job = ScrapeJob.objects.create(
            job_type='bulk_import',
            source='fina',
            status='running',
            parameters={'file': file_path},
            triggered_by='admin',
            started_at=timezone.now(),
        )
        self._log(job, 'info', f'Starting swimset import from {file_path}')

        adapter = SwimsetAdapter()
        try:
            raw_data = adapter.load_json(file_path)
        except Exception as e:
            self._fail(job, f'Failed to load JSON: {e}')
            raise CommandError(str(e))

        self._log(job, 'info', f'Loaded {len(raw_data)} events from JSON')

        records = adapter.normalize_events(raw_data)
        self._log(job, 'info', f'Normalized to {len(records)} individual time records')

        swimmers_created = 0
        meets_created = 0
        times_created = 0
        times_skipped = 0

        for record in records:
            # Skip relays and invalid records
            if record['relay'] or not record['distance'] or not record['time']:
                times_skipped += 1
                continue

            # Upsert swimmer by name + nationality (no external IDs for FINA data)
            swimmer, created = Swimmer.objects.get_or_create(
                full_name=record['swimmer_name'],
                nationality=record['nationality'] or 'UNK',
                defaults={
                    'gender': record['gender'],
                },
            )
            if created:
                swimmers_created += 1
                SwimmerSource.objects.create(
                    swimmer=swimmer,
                    source='fina',
                    external_id=f"fina-{record['swimmer_name'].lower().replace(' ', '-')}",
                    raw_data={},
                )

            # Upsert meet
            if not record['meet_date']:
                times_skipped += 1
                continue

            meet, created = Meet.objects.get_or_create(
                name=record['meet_name'],
                start_date=record['meet_date'],
                course=record['course'],
                defaults={
                    'end_date': record['meet_end_date'] or record['meet_date'],
                    'meet_type': 'championship',
                    'location_city': record['meet_location'],
                    'location_country': record['nationality'][:3] if record['nationality'] else '',
                    'source': 'fina',
                },
            )
            if created:
                meets_created += 1

            # Upsert event
            event, _ = Event.objects.get_or_create(
                distance=record['distance'],
                stroke=record['stroke'],
                relay=False,
                gender=record['gender'],
            )

            # Normalize and create time
            time_kwargs = normalize_swim_time(record, 'fina')
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

        job.status = 'success'
        job.completed_at = timezone.now()
        job.result_summary = {
            'swimmers_created': swimmers_created,
            'meets_created': meets_created,
            'times_created': times_created,
            'times_skipped': times_skipped,
        }
        job.save()

        summary = (
            f'Import complete: {swimmers_created} swimmers, '
            f'{meets_created} meets, {times_created} times '
            f'({times_skipped} skipped)'
        )
        self._log(job, 'info', summary)
        self.stdout.write(self.style.SUCCESS(summary))

    def _log(self, job, level, message):
        ScrapeJobLog.objects.create(job=job, level=level, message=message)
        self.stdout.write(message)

    def _fail(self, job, error_msg):
        job.status = 'failed'
        job.completed_at = timezone.now()
        job.error_detail = error_msg
        job.save()
        self._log(job, 'error', error_msg)
