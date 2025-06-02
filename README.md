# Minimalist Telehealth System

A streamlined telehealth system for patient outreach focused on core functionality. This minimalist version removes all web interfaces and consolidates the database structure for simplicity while maintaining essential telephony capabilities.

## Features

- **Patient Management**: Simplified tracking of patients and their healthcare kits
- **Call Simulation**: Core telephony functionality for patient outreach
- **Consolidated Data**: Single database structure for all patient information
- **HIPAA Compliance**: Maintains audit logging and security features

## Technology Stack

- **Core**: Python 3.11+
- **External Services**:
  - Twilio for telephony integration
  - OpenAI for conversational AI
- **Database**: Single PostgreSQL database structure
- **Security**: 
  - Data encryption for sensitive information
  - Comprehensive audit logging

## Setup Instructions

1. **Clone the repository**
   ```bash
   git clone https://github.com/your-username/telehealth-minimal.git
   cd telehealth-minimal
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Set up environment variables**
   ```bash
   cp config/.env.example .env
   # Edit the .env file with your API keys and configuration
   ```

5. **Run the application**
   ```bash
   python src/app_minimal.py
   ```

## Environment Variables

Create a `.env` file based on `.env.example` with the following variables:

- `TWILIO_ACCOUNT_SID`: Your Twilio account SID
- `TWILIO_AUTH_TOKEN`: Your Twilio auth token
- `TWILIO_PHONE_NUMBER`: Your Twilio phone number for outbound calls
- `OPENAI_API_KEY`: Your OpenAI API key for conversations
- `DATABASE_URL`: URL for your PostgreSQL database
- `ENCRYPTION_KEY`: Key for encrypting sensitive data
- `LOG_LEVEL`: Logging level (INFO, DEBUG, etc.)

## Project Structure

The project has been simplified to focus on core functionality with minimal dependencies:

```
telehealth-minimal/
├── config/
│   └── .env.example       # Example configuration file
├── sql/
│   └── init_consolidated_db.sql  # Single database schema
├── src/
│   ├── app_minimal.py     # Main application entry point
│   ├── handlers/
│   │   └── database_handler.py  # Database interaction
│   ├── routes/
│   │   └── db_mock_data.py      # Mock data for demonstration
│   └── utils/
│       ├── audit_logger.py      # HIPAA compliant logging
│       └── security.py          # Data encryption & security
└── requirements.txt       # Minimal dependencies
```

## Consolidated Database

The system uses a single consolidated database with these key tables:

- `patient_kits`: Combined patient and kit information
- `call_logs`: Records of telephony interactions
- `audit_logs`: HIPAA-compliant activity tracking

## Usage

The minimalist system is designed to be used programmatically rather than through a web interface:

```python
# Import and initialize the telehealth system
from src.app_minimal import TelehealthSystem

# Create an instance of the system
telehealth = TelehealthSystem()

# List all patients in the system
patients = telehealth.list_patients()
print(f"Found {len(patients)} patients")

# Get details for a specific patient by kit ID
patient = telehealth.get_patient_details(kit_id="KIT00001")
if patient:
    print(f"Patient: {patient['patient_name']}")

# Initiate a call to a patient
call_sid = telehealth.initiate_call("KIT00001")
print(f"Initiated call with SID: {call_sid}")

# Get call logs for a specific patient
logs = telehealth.get_call_logs(kit_id="KIT00001")
print(f"Found {len(logs)} call records")
```

## Twilio Integration

For production use, you would need to:

1. Set up your Twilio account with a valid phone number
2. Configure your `.env` file with your Twilio credentials
3. Implement additional handlers for real telephony integration

## Environment Variables

Required environment variables:
- `TWILIO_ACCOUNT_SID`: Your Twilio account SID (with HIPAA BAA)
- `TWILIO_AUTH_TOKEN`: Your Twilio authentication token
- `TWILIO_PHONE_NUMBER`: Your Twilio phone number (format: +1XXXXXXXXXX)
- `OPENAI_API_KEY`: Your OpenAI API key
- `DATABASE_URL_PUBLIC`: PostgreSQL connection string for public tracking database
- `DATABASE_URL_PRIVATE`: PostgreSQL connection string for private PHI database
- `ENCRYPTION_KEY`: Key for encrypting PHI data at rest
- `API_KEY`: Secret key for accessing administrative endpoints

### Security Configuration
- `ENCRYPTION_KEY`: Generated encryption key for PHI data
- `DEBUG`: Set to False in production environments
- `POSTGRES_PASSWORD`: Password for public database
- `POSTGRES_PASSWORD_PRIVATE`: Separate password for private PHI database

## License

Apache License 2.0

## Contributors

Abdul Wadud Abbasi, Pharm.D.c
