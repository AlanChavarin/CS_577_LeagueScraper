# Scrapers Module

This module contains all web scraping logic for collecting League of Legends data from external sources.

## Structure

- `base.py` - Base scraper class with common functionality (rate limiting, error handling, database saving)
- `champion_scraper.py` - Scraper for champion data
- `patch_scraper.py` - Scraper for patch/version data
- `game_scraper.py` - Scraper for game/match data

## Usage

### Base Scraper Features

All scrapers inherit from `BaseScraper` which provides:

- **Rate Limiting**: Automatic delay between requests
- **Error Handling**: Graceful handling of network errors
- **Session Management**: Persistent HTTP session with headers
- **HTML Parsing**: BeautifulSoup integration
- **Database Saving**: Helper method to save scraped data to Django models

### Implementing a Scraper

```python
from .base import BaseScraper
from league.models import Champion

class MyScraper(BaseScraper):
    def scrape(self, source_url: str = None, **kwargs):
        # Your scraping logic here
        response = self.fetch_page(source_url)
        if response:
            soup = self.parse_html(response.text)
            # Parse and extract data
            data = [{
                'lookup': {'name': 'Jinx'},  # Fields to identify existing records
                'defaults': {  # Fields to update/create
                    'damage_type': 'Physical',
                    'primary_role': 'ADC',
                    # ...
                }
            }]
            return data
        return []
```

### Running a Scraper

#### Via API Endpoint

```bash
# Scrape champions
POST /api/league/scrapers/champions/
{
    "source_url": "https://example.com/champions",
    "save_to_db": true
}

# Scrape patches
POST /api/league/scrapers/patches/
{
    "source_url": "https://example.com/patches",
    "save_to_db": true
}

# Scrape games
POST /api/league/scrapers/games/
{
    "source_url": "https://example.com/games",
    "tournament_id": 1,
    "season_id": 1,
    "save_to_db": true
}
```

#### Via Django Shell

```python
from league.scrapers.champion_scraper import ChampionScraper
from league.models import Champion

scraper = ChampionScraper()
data = scraper.scrape(source_url="https://example.com/champions")
scraper.save_to_database(data, Champion)
```

## Libraries Used

- **beautifulsoup4**: HTML parsing
- **requests**: HTTP requests
- **lxml**: Fast XML/HTML parser
- **selenium**: For JavaScript-heavy sites (optional)
- **httpx**: Modern async HTTP client (optional)

## Best Practices

1. **Rate Limiting**: Always respect website rate limits
2. **Error Handling**: Implement robust error handling
3. **Data Validation**: Validate scraped data before saving
4. **Logging**: Log important events and errors
5. **User-Agent**: Set appropriate User-Agent headers
6. **Respect robots.txt**: Check robots.txt before scraping

