from datetime import date
from decimal import Decimal, InvalidOperation

from utils.time import display_to_seconds


VALID_GENDERS = {'male', 'female', 'unknown'}
VALID_COURSES = {'SCY', 'SCM', 'LCM'}
VALID_STROKES = {'freestyle', 'backstroke', 'breaststroke', 'butterfly', 'individual_medley'}


def normalize_swimmer(raw: dict, source: str) -> dict:
    """Raw swimmer dict -> kwargs for Swimmer model."""
    gender = raw.get('gender', 'unknown').lower()
    if gender in ('m', 'male'):
        gender = 'male'
    elif gender in ('f', 'female'):
        gender = 'female'
    else:
        gender = 'unknown'

    return {
        'full_name': raw.get('name', '').strip(),
        'birth_year': raw.get('birth_year'),
        'gender': gender,
        'nationality': raw.get('nationality', 'USA')[:3],
    }


def normalize_swimmer_source(raw: dict, source: str, swimmer_id=None) -> dict:
    """Raw swimmer dict -> kwargs for SwimmerSource model."""
    return {
        'source': source,
        'external_id': str(raw.get('external_id', '')),
        'profile_url': raw.get('profile_url') or None,
        'raw_data': raw,
    }


def normalize_meet(raw: dict, source: str) -> dict:
    """Raw meet dict -> kwargs for Meet model."""
    course = raw.get('course', '')
    if course not in VALID_COURSES:
        course = 'SCY'

    return {
        'name': raw.get('name', '').strip(),
        'start_date': _parse_date(raw.get('date', '')),
        'end_date': _parse_date(raw.get('end_date', raw.get('date', ''))),
        'course': course,
        'meet_type': raw.get('meet_type', 'invitational'),
        'location_city': raw.get('location_city', ''),
        'location_state': raw.get('location_state', ''),
        'location_country': raw.get('location_country', 'USA'),
        'source': source,
        'external_id': str(raw.get('external_id', '')),
    }


def normalize_event(raw: dict) -> dict:
    """Raw event/time dict -> kwargs for Event model."""
    stroke = raw.get('stroke', '').lower().replace(' ', '_')
    if stroke not in VALID_STROKES:
        stroke = 'freestyle'

    return {
        'distance': int(raw.get('distance', 0)),
        'stroke': stroke,
        'relay': raw.get('relay', False),
        'gender': raw.get('gender', 'unknown'),
    }


def normalize_swim_time(raw: dict, source: str) -> dict:
    """Raw time entry -> kwargs for SwimTime model.

    Expects swimmer, meet, and event FKs to be attached separately.
    """
    time_display = raw.get('time', '')
    time_seconds = _safe_parse_time(time_display)

    dq = raw.get('dq', False)
    if time_display.upper() in ('DQ', 'DQY', 'DQR'):
        dq = True

    return {
        'time_seconds': time_seconds,
        'time_display': time_display,
        'heat': _safe_int(raw.get('heat')),
        'lane': _safe_int(raw.get('lane')),
        'place': _safe_int(raw.get('place')),
        'dq': dq,
        'splits': raw.get('splits') or None,
        'source': source,
    }


def normalize_recruiting_profile(raw: dict) -> dict:
    """Raw recruiting dict -> kwargs for RecruitingProfile model."""
    return {
        'graduation_year': _safe_int(raw.get('graduation_year', raw.get('class_year'))),
        'high_school': raw.get('high_school', ''),
        'home_state': raw.get('home_state', raw.get('state', '')),
        'verbal_commit_date': _parse_date(raw.get('verbal_commit_date')),
        'signed_date': _parse_date(raw.get('signed_date')),
        'power_index': _safe_decimal(raw.get('power_index')),
    }


def _parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date):
        return value
    value = str(value).strip()
    for fmt in ('%Y-%m-%d', '%m/%d/%Y', '%m-%d-%Y', '%b %d, %Y'):
        try:
            from datetime import datetime
            return datetime.strptime(value, fmt).date()
        except ValueError:
            continue
    return None


def _safe_parse_time(time_display: str) -> Decimal | None:
    if not time_display:
        return None
    time_display = time_display.strip()
    if time_display.upper() in ('DQ', 'DQY', 'DQR', 'NS', 'NT', 'SCR', 'X'):
        return None
    try:
        return display_to_seconds(time_display)
    except (InvalidOperation, ValueError, ArithmeticError):
        return None


def _safe_int(value) -> int | None:
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _safe_decimal(value) -> Decimal | None:
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None
