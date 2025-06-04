import os
import json
import requests
from typing import Dict, Optional
from dataclasses import dataclass
from enum import Enum

class ModelType(Enum):
    OLLAMA = "ollama"

@dataclass
class NLToSQLConfig:
    model_type: ModelType = ModelType.OLLAMA
    model_name: str = "deepseek"
    ollama_base_url: str = "http://localhost:11434"
    temperature: float = 0.1
    max_tokens: int = 1000

class NLToSQL:    
    def __init__(self, config: Optional[NLToSQLConfig] = None):
        self.config = config or NLToSQLConfig()
        
        if self.config.model_type == ModelType.OLLAMA:
            self._validate_ollama_connection()
    
    def _validate_ollama_connection(self):
        try:
            response = requests.get(f"{self.config.ollama_base_url}/api/tags")
            response.raise_for_status()
            
            models = [model["name"] for model in response.json().get("models", [])]
            if self.config.model_name not in models:
                print(f"Warning: Model '{self.config.model_name}' not found in Ollama. "
                      f"Available models: {', '.join(models)}")
                print(f"You can pull it with: ollama pull {self.config.model_name}")
                
        except requests.exceptions.RequestException as e:
            print(f"Error connecting to Ollama at {self.config.ollama_base_url}")
            print("Make sure Ollama is running and the base URL is correct.")
            raise
    
    def _generate_sql_with_ollama(self, prompt: str) -> str:
        url = f"{self.config.ollama_base_url}/api/generate"
        
        system_prompt = """
        You are a SQL expert that converts natural language to SQL.
        Respond with ONLY the SQL query, no explanations or markdown formatting.
        """
        
        payload = {
            "model": self.config.model_name,
            "prompt": prompt,
            "system": system_prompt,
            "stream": False,
            "options": {
                "temperature": self.config.temperature,
                "max_tokens": self.config.max_tokens
            }
        }
        
        try:
            response = requests.post(url, json=payload)
            response.raise_for_status()
            return response.json().get("response", "").strip()
        except Exception as e:
            print(f"Error generating SQL: {str(e)}")
            raise
    
    def to_sql(self, natural_language_query: str, schema_info: Optional[str] = None) -> str:
        prompt = f"Convert the following natural language query to SQL"
        if schema_info:
            prompt += f" using this schema information:\n\n{schema_info}\n\n"
        else:
            prompt += ":\n\n"
            
        prompt += f"Query: {natural_language_query}\n\nSQL:"
        
        if self.config.model_type == ModelType.OLLAMA:
            return self._generate_sql_with_ollama(prompt)
        else:
            raise ValueError(f"Unsupported model type: {self.config.model_type}")

if __name__ == "__main__":
    SCHEMA_INFO = """
    Tables:
    - points_of_interest (id, name, type, latitude, longitude, version)
    - versions (id, name, version_number, created_at)
    
    Relationships:
    - points_of_interest.version = versions.version_number
    """
    
    nlp_to_sql = NLToSQL()
    
    query = "Find all restaurants in the latest version"
    
    try:
        sql = nlp_to_sql.to_sql(query, SCHEMA_INFO)
        print(f"\nNatural Language: {query}")
        print(f"Generated SQL: {sql}")
    except Exception as e:
        print(f"Error: {str(e)}")
