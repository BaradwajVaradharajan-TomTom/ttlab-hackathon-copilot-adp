# Developer Guide

This guide provides instructions for setting up and running the different components of the application.

## Table of Contents
- [Frontend](#frontend)
- [Backend](#backend)
- [NLP to SQL Service](#nlp-to-sql-service)

## Frontend

### Prerequisites
- Node.js (v18 or higher)
- npm (v9 or higher)

### Setup
1. Navigate to the frontend directory:
   ```bash
   cd frontend
   ```

2. Install dependencies:
   ```bash
   npm install
   ```

### Running the Development Server
```bash
npm run dev
```

The application will be available at `http://localhost:5173`

## Backend

### Prerequisites
- Python 3.9+
- pip (Python package manager)

### Setup
1. Navigate to the backend directory:
   ```bash
   cd backend
   ```

2. Create and activate a virtual environment:
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Configure environment variables:
   - Copy `.env.example` to `.env`
   - Update the `.env` file with your Databricks credentials

### Running the Server
```bash
python run.py
```

The API will be available at `http://localhost:8000`

### API Documentation
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## NLP to SQL Service

### Prerequisites
- Python 3.9+
- pip (Python package manager)
- Ollama (https://ollama.ai/)

### Setup
1. Install and start Ollama:
   ```bash
   # Follow installation instructions at https://ollama.ai/
   # Start the Ollama server
   ollama serve
   ```

2. Pull the desired model (e.g., llama3):
   ```bash
   ollama pull llama3
   ```

3. Navigate to the nlptosql directory:
   ```bash
   cd nlptosql
   ```

4. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

### Running the NLP to SQL Converter
```bash
python nlp_to_sql.py
```

### Example Usage
```python
from nlp_to_sql import NLToSQL

# Initialize the converter
nlp_to_sql = NLToSQL()

# Example schema information
schema_info = """
Tables:
- points_of_interest (id, name, type, latitude, longitude, version)
- versions (id, name, version_number, created_at)

Relationships:
- points_of_interest.version = versions.version_number
"""

# Convert natural language to SQL
query = "Find all restaurants in the latest version"
try:
    sql = nlp_to_sql.to_sql(query, schema_info)
    print(f"Generated SQL: {sql}")
except Exception as e:
    print(f"Error: {str(e)}")
```

## Development Workflow

1. Start the backend server:
   ```bash
   cd backend
   python run.py
   ```

2. In a new terminal, start the frontend development server:
   ```bash
   cd frontend
   npm run dev
   ```

3. Access the application at `http://localhost:5173`

## Environment Variables

### Backend (`.env`)
```
DATABRICKS_SERVER_HOSTNAME=your-databricks-workspace-url
DATABRICKS_HTTP_PATH=your-http-path
DATABRICKS_TOKEN=your-personal-access-token
DATABRICKS_CATALOG=your-catalog
DATABRICKS_SCHEMA=your-schema
```

## Troubleshooting
- If you encounter dependency issues, try:
  ```bash
  rm -rf node_modules package-lock.json
  npm install
  ```