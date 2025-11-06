# Django Backend

## Database Setup with Docker

This project uses PostgreSQL running in Docker. To start the database:

1. From the project root directory, start PostgreSQL:
   ```bash
   docker-compose up -d
   ```
   This will start PostgreSQL in the background.

2. To stop the database:
   ```bash
   docker-compose down
   ```

3. To view database logs:
   ```bash
   docker-compose logs -f db
   ```

## Setup

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows: `venv\Scripts\activate`
   - macOS/Linux: `source venv/bin/activate`

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the `backend` directory (optional, defaults work with docker-compose):
   ```env
   SECRET_KEY=your-secret-key-here
   DEBUG=True
   POSTGRES_DB=postgres
   POSTGRES_USER=postgres
   POSTGRES_PASSWORD=postgres
   POSTGRES_HOST=localhost
   POSTGRES_PORT=5433
   ```

5. Make sure PostgreSQL is running (see Database Setup above)

6. Create migrations for the league app:
   ```bash
   python manage.py makemigrations league
   ```

7. Run migrations:
   ```bash
   python manage.py migrate
   ```

8. Create a superuser (optional):
   ```bash
   python manage.py createsuperuser
   ```

9. Run the development server:
   ```bash
   python manage.py runserver
   ```

The server will run on `http://localhost:8000`

## Database Schema

The project includes the following database tables (models) for League of Legends data:

- **Champion**: League of Legends champions with damage types, roles, and release dates
- **Patch**: Game patches/versions with version numbers and dates
- **ChampionPatch**: Junction table linking champions to patches with change types (buffs, nerfs, etc.)
- **Tournament**: Tournaments with tier classifications and associated patches
- **Team**: Teams with region information
- **Season**: Competitive seasons
- **WinLossRecord**: Champion win/loss records per season
- **Game**: Individual games with team matchups, champion picks (10 total), and lane-specific winners

All models include timestamps (`created_at`, `updated_at`) and are registered in the Django admin.

## Data Science Libraries Included

- numpy
- pandas
- scipy
- scikit-learn
- matplotlib
- seaborn

## API Endpoints

### Admin Panel
- Admin panel: `http://localhost:8000/admin`
- API browser: `http://localhost:8000/api`

### REST API Endpoints
All endpoints support filtering, searching, and pagination:

- `GET/POST /api/league/champions/` - List/Create champions
- `GET/PUT/PATCH/DELETE /api/league/champions/{id}/` - Champion details
- `GET/POST /api/league/patches/` - List/Create patches
- `GET/PUT/PATCH/DELETE /api/league/patches/{id}/` - Patch details
- `GET/POST /api/league/champion-patches/` - List/Create champion-patch relationships
- `GET/POST /api/league/tournaments/` - List/Create tournaments
- `GET/PUT/PATCH/DELETE /api/league/tournaments/{id}/` - Tournament details
- `GET/POST /api/league/teams/` - List/Create teams
- `GET/PUT/PATCH/DELETE /api/league/teams/{id}/` - Team details
- `GET/POST /api/league/seasons/` - List/Create seasons
- `GET/PUT/PATCH/DELETE /api/league/seasons/{id}/` - Season details
- `GET/POST /api/league/win-loss-records/` - List/Create win/loss records
- `GET/PUT/PATCH/DELETE /api/league/win-loss-records/{id}/` - Win/loss record details
- `GET/POST /api/league/games/` - List/Create games
- `GET/PUT/PATCH/DELETE /api/league/games/{id}/` - Game details
- `GET /api/league/games/{id}/picks/` - Get champion picks for a game

### Scraper API Endpoints

- `POST /api/league/scrapers/champions/` - Trigger champion scraping
- `POST /api/league/scrapers/patches/` - Trigger patch scraping
- `POST /api/league/scrapers/games/` - Trigger game scraping
- `GET /api/league/scrapers/status/` - Get scraper status
- `GET /api/league/scrapers/health/` - Health check endpoint

See `league/scrapers/README.md` for detailed usage.

### Example API Queries

- Filter champions by role: `/api/league/champions/?primary_role=ADC`
- Search champions: `/api/league/champions/?search=jinx`
- Filter games by team: `/api/league/games/?blue_team=1`
- Filter games by patch: `/api/league/games/?patch=1`
- Get win/loss records for a season: `/api/league/win-loss-records/?season=1`

