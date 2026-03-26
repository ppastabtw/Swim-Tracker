import json
import re
from datetime import datetime

import requests
from bs4 import BeautifulSoup

from .base import BaseSwimScraper

BASE_URL = 'https://www.swimcloud.com'
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
}

STROKE_MAP = {
    'Free': 'freestyle',
    'Back': 'backstroke',
    'Breast': 'breaststroke',
    'Fly': 'butterfly',
    'IM': 'individual_medley',
}

COURSE_MAP = {
    'L': 'LCM',
    'S': 'SCM',
    'Y': 'SCY',
}


class SwimCloudAdapter(BaseSwimScraper):
    source_name = 'swimcloud'

    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(HEADERS)

    def search_swimmer(self, name: str, **kwargs) -> list[dict]:
        # SwimCloud doesn't have a public search API we can easily scrape
        raise NotImplementedError('SwimCloud search not yet implemented')

    def get_swimmer_times(self, external_id: str) -> dict:
        # Get profile page for swimmer info
        profile_soup = self._get(f'/swimmer/{external_id}/')
        swimmer_info = self._parse_swimmer_info(profile_soup, external_id)

        # Get meets page for all times
        meets_soup = self._get(f'/swimmer/{external_id}/meets/')
        meets = self._parse_meets_page(meets_soup)

        return {
            'swimmer': swimmer_info,
            'meets': meets,
        }

    def get_team_roster(self, team_id: str, **kwargs) -> list[dict]:
        raise NotImplementedError('SwimCloud roster scraping not yet implemented')

    def get_meet_results(self, meet_id: str) -> dict:
        raise NotImplementedError('SwimCloud meet results scraping not yet implemented')

    def _get(self, path: str) -> BeautifulSoup:
        url = f'{BASE_URL}{path}'
        r = self.session.get(url, timeout=30)
        r.raise_for_status()
        return BeautifulSoup(r.text, 'html.parser')

    def _parse_swimmer_info(self, soup: BeautifulSoup, external_id: str) -> dict:
        name = ''
        h1 = soup.find('h1')
        if h1:
            name = h1.text.strip()

        # Location/team info from the div after h1
        hometown = ''
        if h1:
            info_div = h1.find_next('div')
            if info_div:
                hometown = info_div.text.strip()

        # Extract nationality from JSON-LD structured data
        nationality = ''
        for script in soup.find_all('script', type='application/ld+json'):
            try:
                ld = json.loads(script.text)
                location = ld.get('homeLocation', {})
                nationality = location.get('addressCountry', '')
            except (json.JSONDecodeError, AttributeError):
                pass

        return {
            'name': name,
            'external_id': external_id,
            'birth_year': None,
            'gender': 'unknown',
            'nationality': nationality,
            'hometown': hometown,
        }

    def _parse_meets_page(self, soup: BeautifulSoup) -> list[dict]:
        meets = []
        cards = soup.find_all('div', class_='c-swimmer-meets__card')

        for card in cards:
            header = card.find('div', class_='c-swimmer-meets__header')
            if not header:
                continue

            header_text = header.get_text(separator='|', strip=True)
            meet_name, meet_date, meet_location = self._parse_header(header_text)

            # Extract meet ID from the link
            link = card.find('a', class_='c-swimmer-meets__link-mask')
            meet_external_id = ''
            if link and link.get('href'):
                match = re.search(r'/results/(\d+)/', link['href'])
                if match:
                    meet_external_id = match.group(1)

            # Parse times from the table
            table = card.find('table')
            if not table:
                continue

            times = []
            for row in table.find_all('tr'):
                tds = row.find_all('td')
                if len(tds) < 4:
                    continue

                event_text = tds[0].text.strip()
                time_display = tds[1].text.strip()
                place_text = tds[3].text.strip()

                distance, stroke, course = self._parse_event(event_text)

                place = None
                if place_text and place_text != '–':
                    match = re.search(r'(\d+)', place_text)
                    if match:
                        place = int(match.group(1))

                times.append({
                    'event': event_text,
                    'distance': distance,
                    'stroke': stroke,
                    'time': time_display,
                    'place': place,
                    'dq': time_display.upper() in ('DQ', 'DQY', 'DQR'),
                    'splits': [],
                })

            meets.append({
                'name': meet_name,
                'date': meet_date,
                'course': course if times else 'SCY',
                'location_city': meet_location.split(',')[0].strip() if meet_location else '',
                'location_country': meet_location.split(',')[-1].strip() if meet_location else '',
                'external_id': meet_external_id,
                'times': times,
            })

        return meets

    def _parse_header(self, header_text: str) -> tuple[str, str, str]:
        """Parse 'Meet Name|Completed|Jul 4-7, 2024|Toronto, ON, CAN' into parts."""
        parts = [p.strip() for p in header_text.split('|')]

        meet_name = parts[0] if parts else ''

        # Find the date part — look for something with a year
        meet_date = ''
        location = ''
        for part in parts[1:]:
            if part == 'Completed':
                continue
            if re.search(r'\d{4}', part):
                meet_date = self._parse_date(part)
            elif part and not meet_date:
                continue
            elif part:
                location = part

        return meet_name, meet_date, location

    def _parse_date(self, date_str: str) -> str:
        """Parse 'Jul 4-7, 2024' or 'Dec 1-3, 2023' into 'YYYY-MM-DD'."""
        date_str = date_str.replace('–', '-').replace('\u2013', '-')
        # Try to get the start date: 'Jul 4-7, 2024' -> 'Jul 4, 2024'
        match = re.match(r'(\w+)\s+(\d+)(?:-\w*\s*\d+)?,?\s*(\d{4})', date_str)
        if match:
            month_str, day, year = match.groups()
            try:
                dt = datetime.strptime(f'{month_str} {day} {year}', '%b %d %Y')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass

        # Try 'May 31-Jun 2, 2024' format
        match = re.match(r'(\w+)\s+(\d+)-\w+\s+\d+,?\s*(\d{4})', date_str)
        if match:
            month_str, day, year = match.groups()
            try:
                dt = datetime.strptime(f'{month_str} {day} {year}', '%b %d %Y')
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                pass

        return ''

    def _parse_event(self, event_text: str) -> tuple[int, str, str]:
        """Parse '100 L Back' into (100, 'backstroke', 'LCM')."""
        parts = event_text.split()
        distance = 0
        stroke = 'freestyle'
        course = 'SCY'

        if not parts:
            return distance, stroke, course

        # First part is distance
        if parts[0].isdigit():
            distance = int(parts[0])

        # Second part is course code (L/S/Y), third is stroke
        if len(parts) >= 3 and parts[1] in COURSE_MAP:
            course = COURSE_MAP[parts[1]]
            stroke_raw = parts[2]
        elif len(parts) >= 2:
            stroke_raw = parts[1]
        else:
            stroke_raw = ''

        stroke = STROKE_MAP.get(stroke_raw, stroke_raw.lower())
        return distance, stroke, course
