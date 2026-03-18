import subprocess
import json

# TODO: Implement swimset adapter
# GitHub: adghayes/swimset
# This is a one-time historical data import (FINA/Olympics)
# Clone the repo, run the Scrapy spider to produce JSON, then use load_json() below.
# Wire this up as a Django management command: python manage.py import_swimset --file results.json

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
