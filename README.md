# VnStock Screener

A full-stack stock screening and analysis application for the Vietnamese market, featuring real-time "Smart Board", technical signals, and financial metric filtering.

## Features
- **Smart Board**: Real-time market overview with separate columns for Watchlist, Highlights (Gainers/Volume), and Sectors (VN30, Banks, etc.).
- **Screener**: Filter 1400+ stocks by P/E, P/B, ROE, Market Cap, Technical Signals (RSI, MACD), and more.
- **Data Persistence**: Automated data collection and local database storage.
- **Production Ready**: Dockerized setup with Nginx reverse proxy and auto-restart policies.

## Installation & Setup

### Prerequisites
- [Docker Desktop](https://www.docker.com/products/docker-desktop) installed and running.

### Quick Start
1.  **Clone the repository:**
    ```bash
    git clone <repository_url>
    cd vnstock-screener
    ```

2.  **Start the application:**
    ```bash
    docker-compose up -d
    ```
    This command downloads necessary images, builds the frontend/backend, and starts the services in the background.

3.  **Access the App:**
    - Open your browser to `http://localhost`.
    - The API is available at `http://localhost/api`.

## Backup & Maintenance

### Data Persistence
The application stores all stock market data in a SQLite database located at:
`./backend/data/vnstock_data.db`

This file is mapped from the Docker container to your host machine, ensuring data is safe even if containers are rebuilt or removed.

### How to Backup
To backup your database, simply copy the `backend/data` folder to a safe location:

**Windows PowerShell:**
```powershell
Copy-Item -Path .\backend\data -Destination C:\Backups\vnstock_data_backup -Recurse
```

**Linux/Mac:**
```bash
cp -r backend/data ~/backups/vnstock_data_backup
```

### Updating Data
The system includes a smart updater that runs automatically. To manually trigger an update or check logs:

```bash
# View backend logs
docker-compose logs -f backend

# Trigger update (via API)
curl -X POST http://localhost/api/database/update?task_name=daily_screener
```

## Project Structure
- `backend/`: FastAPI application, collecting data from vnstock/cophieu68.
- `src/`: React frontend application (Vite + TailwindCSS).
- `docker-compose.yml`: Orchestration for services.
- `nginx.conf`: Production web server configuration.

## Troubleshooting
- **Frontend not loading?** Check if port 80 is occupied (`netstat -ano | findstr :80`).
- **Data missing?** The initial scrape takes a few minutes. Check logs: `docker-compose logs -f backend`.
