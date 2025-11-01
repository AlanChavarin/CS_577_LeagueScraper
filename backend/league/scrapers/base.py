"""
Base scraper class providing common functionality for all scrapers.
"""
import logging
import time
from abc import ABC, abstractmethod
from typing import Dict, List, Optional, Any
import requests
from bs4 import BeautifulSoup
from django.utils import timezone

logger = logging.getLogger(__name__)


class BaseScraper(ABC):
    """Base class for all scrapers with common functionality."""
    
    def __init__(self, base_url: str = None, delay: float = 1.0, timeout: int = 30):
        """
        Initialize base scraper.
        
        Args:
            base_url: Base URL for the scraper
            delay: Delay between requests in seconds (for rate limiting)
            timeout: Request timeout in seconds
        """
        self.base_url = base_url
        self.delay = delay
        self.timeout = timeout
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.last_request_time = 0
    
    def _rate_limit(self):
        """Implement rate limiting between requests."""
        current_time = time.time()
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.delay:
            sleep_time = self.delay - time_since_last_request
            time.sleep(sleep_time)
        
        self.last_request_time = time.time()
    
    def fetch_page(self, url: str, params: Optional[Dict] = None, headers: Optional[Dict] = None) -> Optional[requests.Response]:
        """
        Fetch a page with rate limiting and error handling.
        
        Args:
            url: URL to fetch
            params: Query parameters
            headers: Additional headers
        
        Returns:
            Response object or None if request fails
        """
        self._rate_limit()
        
        try:
            request_headers = self.session.headers.copy()
            if headers:
                request_headers.update(headers)
            
            response = self.session.get(
                url,
                params=params,
                headers=request_headers,
                timeout=self.timeout
            )
            response.raise_for_status()
            return response
        except requests.RequestException as e:
            logger.error(f"Failed to fetch {url}: {str(e)}")
            return None
    
    def parse_html(self, html_content: str, parser: str = 'lxml') -> Optional[BeautifulSoup]:
        """
        Parse HTML content into BeautifulSoup object.
        
        Args:
            html_content: HTML string
            parser: Parser to use ('lxml', 'html.parser', 'html5lib')
        
        Returns:
            BeautifulSoup object or None if parsing fails
        """
        try:
            return BeautifulSoup(html_content, parser)
        except Exception as e:
            logger.error(f"Failed to parse HTML: {str(e)}")
            return None
    
    @abstractmethod
    def scrape(self, *args, **kwargs) -> List[Dict[str, Any]]:
        """
        Main scraping method to be implemented by subclasses.
        
        Returns:
            List of dictionaries containing scraped data
        """
        pass
    
    def save_to_database(self, data: List[Dict[str, Any]], model_class):
        """
        Save scraped data to database.
        
        Args:
            data: List of dictionaries containing model data
            model_class: Django model class to save to
        """
        created_count = 0
        updated_count = 0
        
        for item in data:
            try:
                obj, created = model_class.objects.update_or_create(
                    **item.get('lookup', {}),
                    defaults=item.get('defaults', {})
                )
                if created:
                    created_count += 1
                else:
                    updated_count += 1
            except Exception as e:
                logger.error(f"Failed to save {model_class.__name__}: {str(e)}")
        
        logger.info(f"Saved {created_count} new, {updated_count} updated {model_class.__name__} records")
        return created_count, updated_count

