"""
Patch scraper for League of Legends game patches.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime, date
import re
from .base import BaseScraper


class PatchScraper(BaseScraper):
    """Scraper for patch/version data."""
    
    def _extract_version_number(self, title_text: str) -> Optional[str]:
        """
        Extract version number from patch title text.
        
        Examples:
            "Patch 25.22 Notes" -> "25.22"
            "Patch 14.24 Notes" -> "14.24"
            "Patch 2025.S1.3 Notes" -> "2025.S1.3"
            "Patch 25.S1.2 Notes" -> "25.S1.2"
        
        Args:
            title_text: Text like "Patch 25.22 Notes"
        
        Returns:
            Version number string or None if not found
        """
        if not title_text:
            return None
        
        # Pattern to match patch versions like:
        # - 25.22, 14.24 (standard format)
        # - 2025.S1.3, 25.S1.2 (season format)
        # - 13.1B (with letter suffix)
        # - 13.24 (standard format)
        # Match "Patch " followed by version number until " Notes"
        pattern = r'Patch\s+([^\s]+?)(?:\s+Notes|$)'
        match = re.search(pattern, title_text, re.IGNORECASE)
        
        if match:
            return match.group(1).strip()
        
        return None
    
    def _parse_date(self, datetime_str: str) -> Optional[datetime]:
        """
        Parse ISO datetime string to datetime object.
        
        Args:
            datetime_str: ISO format string like "2025-11-04T19:00:00.000Z"
        
        Returns:
            datetime object or None if parsing fails
        """
        if not datetime_str:
            return None
        
        try:
            # Parse ISO format: "2025-11-04T19:00:00.000Z"
            # Remove the 'Z' and replace with +00:00 for timezone
            if datetime_str.endswith('Z'):
                datetime_str = datetime_str[:-1] + '+00:00'
            
            # Parse the datetime string
            dt = datetime.fromisoformat(datetime_str)
            return dt
        except (ValueError, AttributeError) as e:
            # Fallback: try parsing without microseconds and timezone
            try:
                # Remove microseconds and timezone info
                dt_str = datetime_str.split('.')[0].replace('Z', '')
                dt = datetime.fromisoformat(dt_str)
                return dt
            except (ValueError, AttributeError):
                return None
    
    def scrape(self, source_url: str = None, file_path: str = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape patch data from the provided URL or local HTML file.
        
        Args:
            source_url: URL to scrape patches from (or file path)
            file_path: Optional explicit file path to read HTML from (takes precedence)
        
        Returns:
            List of dictionaries in format {'lookup': {...}, 'defaults': {...}}
        """
        html_content = None
        source_type = None
        
        # Get the directory where this scraper file is located
        scraper_dir = Path(__file__).parent
        
        # Check if we should read from a file
        if file_path:
            # Explicit file path provided
            file_path_obj = Path(file_path)
            
            # If it's a relative path, resolve it relative to the scraper's directory
            if not file_path_obj.is_absolute():
                file_path_obj = scraper_dir / file_path_obj
            
            if file_path_obj.exists() and file_path_obj.is_file():
                try:
                    with open(file_path_obj, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    source_type = 'file'
                    source_url = str(file_path_obj)
                except Exception as e:
                    return [{
                        'error': f'Failed to read file {file_path}: {str(e)}',
                        'data': None
                    }]
            else:
                return [{
                    'error': f'File not found: {file_path_obj}',
                    'data': None
                }]
        elif source_url:
            # Check if source_url is actually a file path
            file_path_obj = Path(source_url)
            
            # If it's a relative path, resolve it relative to the scraper's directory
            if not file_path_obj.is_absolute():
                file_path_obj = scraper_dir / file_path_obj
            
            if file_path_obj.exists() and file_path_obj.is_file():
                # It's a file path, read from file
                try:
                    with open(file_path_obj, 'r', encoding='utf-8') as f:
                        html_content = f.read()
                    source_type = 'file'
                except Exception as e:
                    return [{
                        'error': f'Failed to read file {source_url}: {str(e)}',
                        'data': None
                    }]
            else:
                # It's a URL, fetch from web
                response = self.fetch_page(source_url)
                if not response:
                    return [{
                        'error': f'Failed to fetch {source_url}',
                        'data': None
                    }]
                html_content = response.text
                source_type = 'url'
        else:
            return [{
                'error': 'No source_url or file_path provided',
                'data': None
            }]
        
        # Parse the HTML
        soup = self.parse_html(html_content)
        
        if not soup:
            return [{
                'error': 'Failed to parse HTML content',
                'data': None
            }]
        
        patches_data = []
        
        # Find the container div that holds all patches
        # The container has class "sc-4d29e6fd-0 hzTXxn" - we'll search for the first part
        container = soup.find('div', class_='sc-4d29e6fd-0')
        
        if container:
            # Each patch is in an <a> tag with role="button" and data-testid="articlefeaturedcard-component"
            patch_links = container.find_all('a', {'role': 'button', 'data-testid': 'articlefeaturedcard-component'})
            
            # If that doesn't work, try just finding all anchor tags with role="button"
            if not patch_links:
                patch_links = container.find_all('a', role='button')
            
            for link in patch_links:
                # Extract patch version from card-title
                title_div = link.find('div', {'data-testid': 'card-title'})
                if not title_div:
                    continue
                
                title_text = title_div.get_text(strip=True)
                version_num = self._extract_version_number(title_text)
                
                if not version_num:
                    continue
                
                # Extract date from card-date
                date_div = link.find('div', {'data-testid': 'card-date'})
                if not date_div:
                    continue
                
                time_tag = date_div.find('time')
                if not time_tag:
                    continue
                
                datetime_str = time_tag.get('datetime')
                if not datetime_str:
                    continue
                
                # Parse the date
                dt = self._parse_date(datetime_str)
                if not dt:
                    continue
                
                # Convert to date object (remove time component)
                patch_date = dt.date()
                
                # Format data for database save
                patches_data.append({
                    'lookup': {'version_num': version_num},
                    'defaults': {'date': patch_date}
                })
        
        return patches_data
    
    def _parse_text_date(self, date_str: str) -> Optional[date]:
        """
        Parse date string from patchTXT.txt format.
        
        Examples:
            "November 5, 2025" -> date(2025, 11, 5)
            "January 9, 2025" -> date(2025, 1, 9)
            "December 13, 2013" -> date(2013, 12, 13)
        
        Args:
            date_str: Date string in format "Month Day, Year"
        
        Returns:
            date object or None if parsing fails
        """
        if not date_str:
            return None
        
        try:
            # Parse format: "Month Day, Year"
            # Example: "November 5, 2025"
            dt = datetime.strptime(date_str.strip(), "%B %d, %Y")
            return dt.date()
        except ValueError:
            # Try alternative format without comma (just in case)
            try:
                dt = datetime.strptime(date_str.strip(), "%B %d %Y")
                return dt.date()
            except ValueError:
                return None
    
    def _extract_version_from_text(self, version_str: str) -> Optional[str]:
        """
        Extract version number from text file format.
        
        Examples:
            "V25.22" -> "25.22"
            "V1.0.0.142f" -> "1.0.0.142f"
            "V1.0.0.140b" -> "1.0.0.140b"
            "V3.5 (Balance update)" -> "3.5"
            "V1.0.0.94(b)" -> "1.0.0.94(b)"
        
        Args:
            version_str: Version string starting with "V"
        
        Returns:
            Version number string without the "V" prefix, or None if not found
        """
        if not version_str:
            return None
        
        version_str = version_str.strip()
        
        # Remove "V" prefix if present
        if version_str.startswith('V'):
            version_str = version_str[1:]
        
        # Remove any parenthetical notes like "(Balance update)"
        # Keep parenthetical suffixes like "(b)" or "(f)" that are part of version
        # Pattern: remove text in parentheses that comes after a space
        # e.g., "3.5 (Balance update)" -> "3.5"
        # but "1.0.0.94(b)" -> "1.0.0.94(b)" (keep it)
        version_str = re.sub(r'\s+\([^)]+\)$', '', version_str)
        
        return version_str.strip() if version_str else None
    
    def scrape_from_text_file(self, file_path: str = None) -> List[Dict[str, Any]]:
        """
        Scrape patch data from patchTXT.txt file.
        
        The file format is:
            YYYY:
            Month Day, YYYY - V[version]
            ...
        
        Examples:
            "2025:"
            "November 5, 2025 - V25.22"
            "October 22, 2025 - V25.21"
        
        Args:
            file_path: Path to patchTXT.txt file. If None, uses default location
                      relative to scraper directory: rawhtml/patchPage/patchTXT.txt
        
        Returns:
            List of dictionaries in format {'lookup': {...}, 'defaults': {...}}
        """
        # Get the directory where this scraper file is located
        scraper_dir = Path(__file__).parent
        
        # Default file path if not provided
        if file_path is None:
            file_path = scraper_dir / 'rawhtml' / 'patchPage' / 'patchTXT.txt'
        else:
            file_path = Path(file_path)
            # If it's a relative path, resolve it relative to the scraper's directory
            if not file_path.is_absolute():
                file_path = scraper_dir / file_path
        
        if not file_path.exists() or not file_path.is_file():
            return [{
                'error': f'File not found: {file_path}',
                'data': None
            }]
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
        except Exception as e:
            return [{
                'error': f'Failed to read file {file_path}: {str(e)}',
                'data': None
            }]
        
        patches_data = []
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines and year headers (lines ending with ":")
            if not line or line.endswith(':'):
                continue
            
            # Parse format: "Month Day, Year - V[version]"
            # Example: "November 5, 2025 - V25.22"
            match = re.match(r'^(.+?)\s+-\s+(V.+)$', line)
            if not match:
                continue
            
            date_str = match.group(1).strip()
            version_str = match.group(2).strip()
            
            # Parse the date
            patch_date = self._parse_text_date(date_str)
            if not patch_date:
                continue
            
            # Extract version number
            version_num = self._extract_version_from_text(version_str)
            if not version_num:
                continue
            
            # Format data for database save
            patches_data.append({
                'lookup': {'version_num': version_num},
                'defaults': {'date': patch_date}
            })
        
        return patches_data

