from .base import BaseSwimScraper

# TODO: Implement USA Swimming adapter
# Based on swimulator (GitHub: alexkgrimes/swimulator) — abandoned reference code
# Requires Selenium + headless Chrome (add Chromium to celery_worker Dockerfile)
# Uses webdriver-manager to handle chromedriver installation automatically

class UsaSwimmingAdapter(BaseSwimScraper):
    source_name = 'usaswimming'

    def _get_driver(self):
        from selenium import webdriver
        from webdriver_manager.chrome import ChromeDriverManager
        from selenium.webdriver.chrome.service import Service

        options = webdriver.ChromeOptions()
        options.add_argument('--headless')
        options.add_argument('--no-sandbox')
        options.add_argument('--disable-dev-shm-usage')
        return webdriver.Chrome(
            service=Service(ChromeDriverManager().install()),
            options=options,
        )

    def get_swimmer_times(self, external_id: str) -> dict:
        raise NotImplementedError
