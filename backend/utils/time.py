from decimal import Decimal, ROUND_HALF_UP
import re


def display_to_seconds(s: str) -> Decimal:
    """Convert a display time string to seconds as Decimal.

    '1:45.23' -> Decimal('105.2300')
    '26.45'   -> Decimal('26.4500')
    """
    s = s.strip()
    if ':' in s:
        minutes, rest = s.split(':', 1)
        return (Decimal(minutes) * 60 + Decimal(rest)).quantize(Decimal('0.0001'))
    return Decimal(s).quantize(Decimal('0.0001'))


def seconds_to_display(t: Decimal) -> str:
    """Convert seconds to a display time string.

    Decimal('105.23') -> '1:45.23'
    Decimal('26.45')  -> '26.45'
    """
    t = Decimal(str(t))
    if t >= 60:
        minutes = int(t // 60)
        seconds = t - (minutes * 60)
        sec_str = f'{seconds:.2f}'
        if seconds < 10:
            sec_str = f'0{sec_str}'
        return f'{minutes}:{sec_str}'
    return f'{t:.2f}'
