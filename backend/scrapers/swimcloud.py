from .base import BaseSwimScraper

# TODO: Implement SwimCloud adapter
# First run: pip install SwimScraper
# Then inspect: python -c "import SwimScraper; help(SwimScraper)"
# and fill in the exact method calls below.

class SwimCloudAdapter(BaseSwimScraper):
    source_name = 'swimcloud'

    def __init__(self):
        # TODO: initialize SwimScraper client
        pass

    def search_swimmer(self, name: str, **kwargs) -> list[dict]:
        raise NotImplementedError

    def get_swimmer_times(self, external_id: str) -> dict:
        raise NotImplementedError

    def get_team_roster(self, team_id: str) -> list[dict]:
        raise NotImplementedError

    def get_meet_results(self, meet_id: str) -> dict:
        raise NotImplementedError
