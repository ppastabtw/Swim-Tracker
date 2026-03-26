import re

import requests
from bs4 import BeautifulSoup
from decouple import config

from .base import BaseSwimScraper

STROKE_MAP = {
    'freestyle': 'freestyle',
    'backstroke': 'backstroke',
    'breaststroke': 'breaststroke',
    'butterfly': 'butterfly',
    'medley': 'individual_medley',
}

COURSE_MAP = {
    '25m': 'SCM',
    '50m': 'LCM',
}


class SwimRankingsAdapter(BaseSwimScraper):
    source_name = 'swimrankings'

    def __init__(self):
        self.flaresolverr_url = config('FLARESOLVERR_URL', default='http://flaresolverr:8191/v1')

    def search_swimmer(self, name: str, **kwargs) -> list[dict]:
        raise NotImplementedError('SwimRankings search not yet implemented')

    def get_swimmer_times(self, external_id: str) -> dict:
        url = f'https://www.swimrankings.net/index.php?page=athleteDetail&athleteId={external_id}'
        soup = self._fetch(url)

        swimmer_info = self._parse_swimmer_info(soup, external_id)
        times_table = self._find_best_times_table(soup)
        meets = self._parse_times_table(times_table) if times_table else []

        return {
            'swimmer': swimmer_info,
            'meets': meets,
        }

    def get_team_roster(self, team_id: str) -> list[dict]:
        raise NotImplementedError('SwimRankings roster not yet implemented')

    def get_meet_results(self, meet_id: str) -> dict:
        raise NotImplementedError('SwimRankings meet results not yet implemented')

    def _fetch(self, url: str) -> BeautifulSoup:
        r = requests.post(self.flaresolverr_url, json={
            'cmd': 'request.get',
            'url': url,
            'maxTimeout': 60000,
        }, timeout=90)
        r.raise_for_status()
        data = r.json()
        if data.get('status') != 'ok':
            raise RuntimeError(f'FlareSolverr error: {data}')
        html = data['solution']['response']
        return BeautifulSoup(html, 'html.parser')

    def _parse_swimmer_info(self, soup: BeautifulSoup, external_id: str) -> dict:
        """Parse 'NEELEMAN, Bas (1996)NED' from the page."""
        name = ''
        birth_year = None
        nationality = ''
        gender = 'unknown'

        # The name/info is in the first table's first cell or in a heading
        # Look for pattern: NAME, First (YEAR) COUNTRY
        text = soup.get_text()
        match = re.search(
            r'([A-Z][A-Z\s\-]+),\s*(\w[\w\s\-]*?)\s*\((\d{4})\s*\)\s*([A-Z]{2,3})',
            text,
        )
        if match:
            last_name = match.group(1).strip().title()
            first_name = match.group(2).strip().title()
            name = f'{first_name} {last_name}'
            birth_year = int(match.group(3))
            nationality = match.group(4)[:3]

        # Gender is not reliably available on SwimRankings profile pages.
        # Leave as 'unknown' — can be set manually or from another source.

        return {
            'name': name,
            'external_id': external_id,
            'birth_year': birth_year,
            'gender': gender,
            'nationality': nationality,
        }

    def _find_best_times_table(self, soup: BeautifulSoup):
        """Find the personal bests table by its headers."""
        for table in soup.find_all('table'):
            ths = table.find_all('th')
            headers = [th.text.strip() for th in ths]
            if 'Event' in headers and 'Time' in headers and 'Course' in headers:
                # Make sure this is the clean inner table (no nested duplicates)
                nested = table.find('table')
                if nested:
                    return self._find_best_times_table_inner(table)
                return table
        return None

    def _find_best_times_table_inner(self, outer_table):
        """If tables are nested, find the innermost one with actual data rows."""
        tables = outer_table.find_all('table')
        best = None
        best_rows = 0
        for t in tables:
            rows = t.find_all('tr')
            data_rows = [r for r in rows if r.find_all('td')]
            if len(data_rows) > best_rows:
                best = t
                best_rows = len(data_rows)
        return best or outer_table

    def _parse_times_table(self, table) -> list[dict]:
        """Parse the best times table into meets format."""
        meets_by_key = {}
        rows = table.find_all('tr')

        for row in rows:
            tds = row.find_all('td')
            if len(tds) < 7:
                continue

            event_text = tds[0].text.strip()
            course_text = tds[1].text.strip()
            time_display = tds[2].text.strip()
            date_text = tds[4].text.strip().replace('\xa0', ' ')
            city = tds[5].text.strip().replace('\xa0', ' ')
            meet_name = tds[6].text.strip()

            # Skip relay laps
            if 'Lap' in event_text:
                continue

            # Skip invalid times
            if not time_display or time_display in ('DNS', 'DNF', 'DSQ'):
                continue

            distance, stroke = self._parse_event(event_text)
            course = COURSE_MAP.get(course_text, 'LCM')
            date = self._parse_date(date_text)

            if not distance or not date:
                continue

            # Group by meet
            key = (meet_name, date)
            if key not in meets_by_key:
                # Extract country from city if present: "Bielefeld (GER)"
                location_country = ''
                city_clean = city
                country_match = re.search(r'\(([A-Z]{3})\)', city)
                if country_match:
                    location_country = country_match.group(1)
                    city_clean = city[:country_match.start()].strip()

                meets_by_key[key] = {
                    'name': meet_name,
                    'date': date,
                    'course': course,
                    'location_city': city_clean,
                    'location_country': location_country,
                    'times': [],
                }

            meets_by_key[key]['times'].append({
                'event': event_text,
                'distance': distance,
                'stroke': stroke,
                'time': time_display,
                'place': None,
                'dq': False,
                'splits': [],
            })

        return list(meets_by_key.values())

    def _parse_event(self, event_text: str) -> tuple[int, str]:
        """Parse '100m Freestyle' into (100, 'freestyle')."""
        distance_match = re.search(r'(\d+)m', event_text)
        distance = int(distance_match.group(1)) if distance_match else 0

        stroke = 'freestyle'
        event_lower = event_text.lower()
        for key, value in STROKE_MAP.items():
            if key in event_lower:
                stroke = value
                break

        return distance, stroke

    def _parse_date(self, date_text: str) -> str:
        """Parse '16 Jun 2013' into '2013-06-16'."""
        months = {
            'jan': '01', 'feb': '02', 'mar': '03', 'apr': '04',
            'may': '05', 'jun': '06', 'jul': '07', 'aug': '08',
            'sep': '09', 'oct': '10', 'nov': '11', 'dec': '12',
        }
        match = re.search(r'(\d{1,2})\s+(\w{3})\s+(\d{4})', date_text)
        if match:
            day, month_str, year = match.groups()
            month = months.get(month_str.lower(), '01')
            return f'{year}-{month}-{int(day):02d}'
        return ''
