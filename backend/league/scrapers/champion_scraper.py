"""
Champion scraper for League of Legends champions.
"""
from pathlib import Path
from typing import List, Dict, Any
from datetime import timedelta, date
from decimal import Decimal
from .base import BaseScraper


class ChampionScraper(BaseScraper):
    """Scraper for champion data."""
    
    def _parse_percentage(self, value: str) -> Decimal:
        """Parse percentage string (e.g., '60%') to Decimal (e.g., 60.00)"""
        if not value or value.strip() == '' or value == '-':
            return Decimal('0.00')
        value = value.strip().replace('%', '')
        try:
            return Decimal(value)
        except (ValueError, TypeError):
            return Decimal('0.00')
    
    def _parse_integer(self, value: str, default: int = 0) -> int:
        """Parse integer string to int"""
        if not value or value.strip() == '' or value == '-':
            return default
        try:
            return int(float(value.strip().replace(',', '')))
        except (ValueError, TypeError):
            return default
    
    def _parse_float(self, value: str, default: float = 0.0) -> float:
        """Parse float string to float"""
        if not value or value.strip() == '' or value == '-':
            return default
        try:
            return float(value.strip().replace(',', ''))
        except (ValueError, TypeError):
            return default
    
    def _parse_duration(self, value: str) -> timedelta:
        """Parse duration string (e.g., '32:48') to timedelta"""
        if not value or value.strip() == '' or value == '-':
            return None
        try:
            parts = value.strip().split(':')
            if len(parts) == 2:
                minutes = int(parts[0])
                seconds = int(parts[1])
                return timedelta(minutes=minutes, seconds=seconds)
            elif len(parts) == 3:
                hours = int(parts[0])
                minutes = int(parts[1])
                seconds = int(parts[2])
                return timedelta(hours=hours, minutes=minutes, seconds=seconds)
        except (ValueError, TypeError):
            pass
        return None
    
    def _parse_table_rows_to_champions(self, table_rows: List[List[str]]) -> List[Dict[str, Any]]:
        """
        Parse table rows into Champion model data format.
        
        Args:
            table_rows: List of rows, where first row is headers
            
        Returns:
            List of dictionaries in format {'lookup': {...}, 'defaults': {...}}
        """
        if not table_rows or len(table_rows) < 2:
            return []
        
        # Skip header row (first row)
        data_rows = table_rows[1:]
        champions = []
        
        for row in data_rows:
            if len(row) < 17:  # Need at least 17 columns
                continue
            
            # Extract champion name
            champion_name = row[0].strip()
            if not champion_name:
                continue
            
            # Map columns to model fields
            champion_data = {
                'lookup': {'name': champion_name},
                'defaults': {
                    # Required fields (set defaults if not in table)
                    'release_date': date(2009, 1, 1),  # Default date if not in table (LoL release date)
                    'primary_damage_type': '',  # Not in table (AD or AP)
                    
                    # Table data fields
                    'picks': self._parse_integer(row[1]),
                    'bans': self._parse_integer(row[2]),
                    'prioscore': self._parse_percentage(row[3]),
                    'wins': self._parse_integer(row[4]),
                    'losses': self._parse_integer(row[5]),
                    'winrate': self._parse_percentage(row[6]),
                    'KDA': self._parse_float(row[7]),
                    'avg_bt': self._parse_float(row[8]),
                    'avg_rp': self._parse_float(row[9]),
                    'gt': self._parse_duration(row[10]),
                    'csm': self._parse_float(row[11]),
                    'dpm': self._parse_integer(row[12]),
                    'gpm': self._parse_integer(row[13]),
                    'csd_15': self._parse_integer(row[14]),
                    'gd_15': self._parse_integer(row[15]),
                    'xpd_15': self._parse_integer(row[16]),
                }
            }
            champions.append(champion_data)
        
        return champions
    
    def scrape(self, source_url: str = None, file_path: str = None, **kwargs) -> List[Dict[str, Any]]:
        """
        Scrape champion data from the provided URL or local HTML file.
        
        Args:
            source_url: URL to scrape champions from (or file path)
            file_path: Optional explicit file path to read HTML from (takes precedence)
        
        Returns:
            List containing dictionary with scraped webpage data
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
                    source_url = str(file_path_obj)  # Use file path as source identifier
                except Exception as e:
                    return [{
                        'error': f'Failed to read file {file_path}: {str(e)}',
                        'data': None
                    }]
            else:
                return [{
                    'error': f'File not found: {file_path_obj} (resolved from {scraper_dir})',
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
        
        # Parse the HTML - WORK WITH THIS for precise extraction!
        soup = self.parse_html(html_content)
        
        if not soup:
            return [{
                'error': 'Failed to parse HTML content',
                'raw_html': html_content[:1000] if html_content else None  # First 1000 chars as fallback
            }]
        
        # WORK WITH THE SOUP OBJECT HERE to extract specific data
        # Example: soup.find('div', class_='champion-name') 
        # Example: soup.select('div.champion-list > div.champion-item')/
        # Example: soup.find_all('span', {'data-role': 'champion'})
        
        # Extract text content (without HTML tags) - use this for quick text searches only
        text_content = soup.get_text(separator=' ', strip=True)
        
        # Extract all links
        links = [{'href': a.get('href'), 'text': a.get_text(strip=True)} for a in soup.find_all('a', href=True)]
        
        # Extract all images
        images = [{'src': img.get('src'), 'alt': img.get('alt', '')} for img in soup.find_all('img', src=True)]

        # Check for embedded JSON data in script tags (common for JS-rendered tables)
        embedded_data = []
        script_tags = soup.find_all('script')
        for script in script_tags:
            script_content = script.string
            if script_content:
                # Look for common patterns like var data = {...}, window.data = {...}, etc.
                if any(keyword in script_content for keyword in ['var ', 'const ', 'let ', 'window.', 'data', 'champion', 'player']):
                    # Check if it looks like JSON
                    if '{' in script_content and '}' in script_content:
                        embedded_data.append({
                            'type': script.get('type', 'text/javascript'),
                            'content_preview': script_content[:500]  # First 500 chars
                        })
        
        # Find all tables with class 'playerslist'
        playersList_tables = soup.find_all('table', class_='playerslist')
        
        # Convert BeautifulSoup Tag objects to JSON-serializable format
        # Option 1: Convert to HTML strings
        playersList_html = [str(table) for table in playersList_tables]
        
        # Option 2: Extract structured data from tables (if you want the actual data)
        playersList_data = []
        for table in playersList_tables:
            rows = []
            # Find all rows (handle both thead and tbody if present)
            for tr in table.find_all('tr'):
                # Get all cells (td or th) - use find_all to preserve order
                cells_elements = tr.find_all(['td', 'th'])
                cells = []
                
                for cell in cells_elements:
                    # Simple extraction - get text and strip whitespace
                    # This handles nested elements automatically
                    cell_text = cell.get_text(separator=' ', strip=True)
                    # Clean up any special whitespace characters
                    cell_text = cell_text.replace('\xa0', ' ').replace('\u200b', '')  # Remove zero-width spaces
                    cell_text = ' '.join(cell_text.split())  # Collapse multiple spaces
                    cells.append(cell_text)
                
                # Add row if it has any cells
                if cells:
                    rows.append(cells)
            
            if rows:  # Only add tables with data
                playersList_data.append(rows)
        
        # Debug: Extract ALL cells from first data row to diagnose empty columns
        debug_info = {
            'total_tables': len(playersList_tables),
            'first_data_row_cells': []
        }
        
        if playersList_tables:
            first_table = playersList_tables[0]
            all_rows = first_table.find_all('tr')
            
            if len(all_rows) > 1:
                # Get the first data row (skip header)
                data_row = all_rows[1]
                all_cells = data_row.find_all(['td', 'th'])
                
                debug_info['first_data_row_cells'] = [
                    {
                        'index': i,
                        'tag': cell.name,
                        'html': str(cell)[:200],  # First 200 chars of HTML
                        'html_full': str(cell),  # Full HTML
                        'text_extracted': cell.get_text(separator=' ', strip=True),
                        'text_length': len(cell.get_text(separator=' ', strip=True)),
                        'has_nested_elements': len(cell.find_all()) > 0,
                        'nested_tags': [tag.name for tag in cell.find_all()[:5]],  # First 5 nested tags
                        'attributes': dict(cell.attrs),
                        'inner_html': cell.decode_contents()[:100] if cell.decode_contents() else ''
                    }
                    for i, cell in enumerate(all_cells)
                ]
                
                # Also check header row for comparison
                if all_rows:
                    header_row = all_rows[0]
                    header_cells = header_row.find_all(['td', 'th'])
                    debug_info['header_cells_count'] = len(header_cells)
                    debug_info['data_cells_count'] = len(all_cells)
                    debug_info['cell_count_match'] = len(header_cells) == len(all_cells)
        
        # Check if table appears to be JavaScript-rendered (has empty cells that should have data)
        empty_cell_count = 0
        total_cell_count = 0
        if debug_info.get('first_data_row_cells'):
            for cell_info in debug_info['first_data_row_cells']:
                total_cell_count += 1
                if cell_info.get('text_length', 0) == 0:
                    empty_cell_count += 1
        
        is_js_rendered = empty_cell_count > (total_cell_count * 0.3)  # If >30% empty, likely JS-rendered
        
        # Parse table data into Champion model format
        champions_data = []
        if playersList_data:
            # Process the first table (assuming it's the main champions table)
            for table_rows in playersList_data:
                champions = self._parse_table_rows_to_champions(table_rows)
                champions_data.extend(champions)
        
        # Return the scraped data
        # Note: You can't return BeautifulSoup Tag objects directly (not JSON serializable)
        return [{
            'source': source_url,
            'source_type': source_type,  # 'url' or 'file'
            'playersList_html': playersList_html,  # HTML strings of the tables
            'playersList_data': playersList_data,  # Structured data extracted from tables
            'champions_data': champions_data,  # Parsed champion data ready for database
            'champions_count': len(champions_data),
            'table_count': len(playersList_tables),
            'debug_info': debug_info,  # Detailed debug info for all cells in first data row
            'embedded_script_data': embedded_data,  # Check for JSON data in script tags
            'potential_js_rendering': {
                'is_likely_js_rendered': is_js_rendered,
                'empty_cells': empty_cell_count,
                'total_cells': total_cell_count,
                'note': 'If is_likely_js_rendered is true and source_type is "url", you may need to use Selenium/Playwright to wait for JavaScript to populate the table'
            }
        }]

