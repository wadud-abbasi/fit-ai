# HIPAA AI FIT Kit Voice Assistant - Project Setup Guide

## Organized Project Structure

We've organized the project into a clean, modular structure for better maintainability:

```
HEALTHCARE CORPS/
├── src/                      # Main source code
│   ├── __init__.py           # Package initialization
│   ├── app.py                # Main Flask application
│   ├── handlers/             # Service handlers
│   │   ├── __init__.py
│   │   ├── database_handler.py
│   │   ├── whisper_handler.py
│   │   ├── coqui_tts_handler.py
│   │   ├── fit_kit_db_handler.py
│   │   └── openai_handler.py
│   ├── routes/               # API routes
│   │   ├── __init__.py
│   │   └── patient_routes.py
│   └── utils/                # Utility modules
│       ├── __init__.py
│       ├── audit_logger.py
│       ├── conversation_analyzer.py
│       └── data_retention.py
├── config/                   # Configuration files
│   └── .env.example          # Environment variables template
├── docker/                   # Docker configuration
│   ├── Dockerfile            # Application container setup
│   └── docker-compose.yml    # Multi-container deployment
├── scripts/                  # Utility scripts
│   └── update_imports.py     # Updates imports for new structure
├── sql/                      # Database schema definitions
│   ├── init_private_db.sql   # PHI database schema
│   └── init_public_db.sql    # Non-PHI tracking database schema
├── tests/                    # Test suites
├── run.py                    # Application entry point
└── README.md                 # Project documentation
```

## Database Setup

The system uses two PostgreSQL databases for HIPAA compliance:

1. **Public Database** (`fitkit_public`): Stores non-PHI data
   - FIT kit tracking information
   - Call logs (without PHI)
   - System audit trails

2. **Private Database** (`fitkit_private`): Stores PHI data
   - Patient demographic information
   - Conversation transcripts (encrypted)
   - PHI access logs

### Setting Up PostgreSQL Databases

#### Method 1: Using Docker Compose (Recommended for Development)

1. **Configure environment variables**:
   ```bash
   cp config/.env.example .env
   # Edit .env with your credentials
   ```

2. **Start the databases**:
   ```bash
   cd docker
   docker-compose up -d db_public db_private
   ```

#### Method 2: Manual PostgreSQL Setup

1. **Create databases using pgAdmin**:
   - Create `fitkit_public` database
   - Create `fitkit_private` database

2. **Initialize schema using SQL files**:
   - Open the SQL Query Tool for each database
   - Load and execute the corresponding SQL file from the `sql/` directory

3. **Importing Excel Data**:
   - Export your Excel data to CSV format
   - Use pgAdmin's Import/Export functionality:
     - Right-click table → Import/Export
     - Browse to your CSV file
     - Map columns correctly
     - Click "Import"

## Running the Application

### Development Mode

1. **Set up Python environment**:
   ```bash
   python -m venv .venv
   .venv\Scripts\activate  # On Windows
   pip install -r requirements.txt
   ```

2. **Configure environment variables**:
   ```bash
   cp config/.env.example .env
   # Edit .env with your API keys and database URLs
   ```

3. **Run the application**:
   ```bash
   python run.py
   ```

### Production Deployment

For production, use the Docker setup:

```bash
cd docker
docker-compose up -d
```

## Testing Calls

```bash
curl -X POST http://localhost:5000/call/start \
  -d "to=+1XXXXXXXXXX" \
  -d "mrn=PATIENT-12345" \
  -d "reminder_type=fit_kit"
```

## Accessing PostgreSQL Databases

### Using pgAdmin

1. **Connect to databases**:
   - Public database: `localhost:5432` (default port)
   - Private database: `localhost:5433` (secondary port)
   
2. **Running queries**:
   - Public database: `SELECT * FROM fit_kit_tracking LIMIT 10;`
   - Private database: `SELECT * FROM patients LIMIT 10;`

### Using Command Line

```bash
# Connect to public database
psql -h localhost -p 5432 -U postgres -d fitkit_public

# Connect to private database
psql -h localhost -p 5433 -U postgres -d fitkit_private
```

## Troubleshooting

- **Database connection issues**: Check that PostgreSQL is running and accessible
- **Import path errors**: Run `python scripts/update_imports.py` to fix import statements
- **Docker issues**: Ensure Docker is running and ports 5432/5433 are available
- **Twilio connectivity**: Use ngrok to expose your local server
