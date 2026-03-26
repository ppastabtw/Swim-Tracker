import json
import re
import subprocess


STROKE_MAP = {
    'freestyle': 'freestyle',
    'free': 'freestyle',
    'backstroke': 'backstroke',
    'back': 'backstroke',
    'breaststroke': 'breaststroke',
    'breast': 'breaststroke',
    'butterfly': 'butterfly',
    'fly': 'butterfly',
    'medley': 'individual_medley',
    'individual medley': 'individual_medley',
    'im': 'individual_medley',
}


class SwimsetAdapter:
    source_name = 'fina'

    def run_spider(self, swimset_dir: str, output_path: str) -> bool:
        """Run the Scrapy spider from the cloned swimset repo."""
        result = subprocess.run(
            ['scrapy', 'crawl', 'fina', '-o', output_path],
            capture_output=True,
            cwd=swimset_dir,
        )
        return result.returncode == 0

    def load_json(self, path: str) -> list[dict]:
        """Load pre-scraped swimset JSON output."""
        with open(path) as f:
            return json.load(f)

    def normalize_events(self, raw_data: list[dict]) -> list[dict]:
        """Convert raw swimset JSON into a flat list of time records."""
        records = []

        for event in raw_data:
            meet_name = event.get('competition', '')
            year = event.get('year', '')
            location = event.get('location-name', '')
            event_title = event.get('event-title', '')

            distance, stroke, gender, relay = self._parse_event_title(event_title)
            course = self._infer_course(event_title, meet_name)

            # Build meet date from available fields
            start_day = event.get('start-day', '1')
            start_month = event.get('start-month', '1')
            end_day = event.get('end-day', start_day)
            end_month = event.get('end-month', start_month)
            meet_date = self._build_date(year, start_month, start_day)
            meet_end_date = self._build_date(year, end_month, end_day)

            for phase in event.get('phases', []):
                for result in phase.get('results', []):
                    name = result.get('name', result.get('fullname', ''))
                    if not name:
                        continue

                    country = result.get('country', result.get('ioc', ''))
                    time_display = result.get('swimtime', result.get('time', ''))
                    rank = result.get('rank', result.get('place', ''))

                    # Parse splits if present
                    splits = []
                    for split in result.get('splits', []):
                        split_time = split.get('time', split.get('swimtime', ''))
                        if split_time:
                            splits.append(split_time)

                    records.append({
                        'meet_name': meet_name,
                        'meet_date': meet_date,
                        'meet_end_date': meet_end_date,
                        'meet_location': location,
                        'meet_year': year,
                        'event_title': event_title,
                        'distance': distance,
                        'stroke': stroke,
                        'gender': gender,
                        'relay': relay,
                        'course': course,
                        'swimmer_name': name.strip(),
                        'nationality': country[:3] if country else '',
                        'time': time_display,
                        'place': self._safe_int(rank),
                        'dq': time_display.upper() in ('DSQ', 'DQ', 'DNS', 'DNF'),
                        'splits': splits,
                    })

        return records

    def _parse_event_title(self, title: str) -> tuple[int, str, str, bool]:
        """Parse 'Men's 100m Butterfly' into (100, 'butterfly', 'male', False)."""
        title_lower = title.lower()

        # Gender
        if 'women' in title_lower or 'female' in title_lower:
            gender = 'female'
        elif 'men' in title_lower or 'male' in title_lower:
            gender = 'male'
        else:
            gender = 'unknown'

        # Relay
        relay = 'relay' in title_lower

        # Distance
        distance_match = re.search(r'(\d+)\s*m\b', title_lower)
        distance = int(distance_match.group(1)) if distance_match else 0

        # Stroke
        stroke = 'freestyle'
        for key, value in STROKE_MAP.items():
            if key in title_lower:
                stroke = value
                break

        return distance, stroke, gender, relay

    def _infer_course(self, event_title: str, meet_name: str) -> str:
        """FINA/World Aquatics events are almost always LCM."""
        text = (event_title + ' ' + meet_name).lower()
        if 'short course' in text or '25m' in text:
            return 'SCM'
        return 'LCM'

    def _build_date(self, year: str, month: str, day: str) -> str:
        """Build YYYY-MM-DD from parts."""
        try:
            y = int(year)
            m = int(month)
            d = int(day)
            return f'{y:04d}-{m:02d}-{d:02d}'
        except (ValueError, TypeError):
            return ''

    def _safe_int(self, value) -> int | None:
        if not value:
            return None
        try:
            return int(value)
        except (ValueError, TypeError):
            return None
