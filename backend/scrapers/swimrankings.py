from .base import BaseSwimScraper

# TODO: Implement SwimRankings adapter
# pip install swimrankingsscraper
# API: SwimrankingsScraper().get_athlete(id).list_meets()

class SwimRankingsAdapter(BaseSwimScraper):
    source_name = 'swimrankings'

    def __init__(self):
        # TODO: initialize SwimrankingsScraper client
        pass

    def search_swimmer(self, name: str, **kwargs) -> list[dict]:
        raise NotImplementedError

    def get_swimmer_times(self, external_id: str) -> dict:
        raise NotImplementedError

    def get_team_roster(self, team_id: str) -> list[dict]:
        raise NotImplementedError

    def get_meet_results(self, meet_id: str) -> dict:
        raise NotImplementedError
