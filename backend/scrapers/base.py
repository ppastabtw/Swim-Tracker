class BaseSwimScraper:
    """
    Abstract interface all scraper adapters must implement.

    Return contract for get_swimmer_times():
    {
        'swimmer': {'name': str, 'birth_year': int|None, 'gender': str},
        'meets': [
            {
                'name': str,
                'date': str,       # ISO format: 'YYYY-MM-DD'
                'course': str,     # 'SCY' | 'SCM' | 'LCM'
                'times': [
                    {
                        'distance': int,
                        'stroke': str,
                        'time': str,       # display string e.g. '1:45.23'
                        'place': int|None,
                        'dq': bool,
                        'splits': list,    # optional
                    }
                ]
            }
        ]
    }
    """

    source_name: str = ''

    def search_swimmer(self, name: str, **kwargs) -> list[dict]:
        raise NotImplementedError

    def get_swimmer_times(self, external_id: str) -> dict:
        raise NotImplementedError

    def get_team_roster(self, team_id: str) -> list[dict]:
        raise NotImplementedError

    def get_meet_results(self, meet_id: str) -> dict:
        raise NotImplementedError
