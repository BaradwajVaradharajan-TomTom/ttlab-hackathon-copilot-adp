from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Dict, Any
import os
from dotenv import load_dotenv
import databricks.sql as dbsql
from databricks.sql.client import Connection

load_dotenv()

app = FastAPI(title="Databricks Query API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class QueryRequest(BaseModel):
    query: str

class DatabricksService:
    def __init__(self):
        self.connection = self._create_connection()
    
    def _create_connection(self) -> Connection:
        return dbsql.connect(
            server_hostname=os.getenv("DATABRICKS_SERVER_HOSTNAME"),
            http_path=os.getenv("DATABRICKS_HTTP_PATH"),
            access_token=os.getenv("DATABRICKS_TOKEN")
        )
    
    def execute_query(self, query: str) -> List[Dict[str, Any]]:
        cursor = self.connection.cursor()
        try:
            cursor.execute(query)
            columns = [desc[0] for desc in cursor.description]
            rows = cursor.fetchall()
            return [dict(zip(columns, row)) for row in rows]
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))
        finally:
            cursor.close()

db_service = DatabricksService()

@app.get("/")
async def root():
    return {"message": "Databricks Query API is running"}

@app.post("/query")
async def execute_query(request: QueryRequest):
    try:
        results = db_service.execute_query(request.query)
        return {"results": results}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
