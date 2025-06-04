Project Overview

Build a chat interface that converts natural language queries into SQL and executes them on Databricks warehouse with Unity Catalog. The system should perform joins and unions based on simple conversational input.

Answer questions like "How many points of interest have changed in the latest version of some $versionname_$versionnumber" through natural language.


Team Assignments & Responsibilities

Frontend

Build chat interface with message history

Query input with loading states and typing indicators

Results display (Simple text for now)

Error handling UI with user-friendly messages

WebSocket integration for real-time updates

Responsive design for mobile/desktop

Backend (FastAPI)

FastAPI server with chat endpoints

Databricks SQL execution service

Query Intent Parser

Natural language preprocessing and tokenization

Intent classification (JOIN, UNION, FILTER, AGGREGATE, COUNT, etc.)

Entity extraction (table names, column names, values, operators)

Integration with LLM APIs for complex parsing

Schema feeder

Unity Catalog metadata ingestion and caching

Table relationship detection and scoring

Feeding orbis-metrics-definition also into the LLM for context? (can be experimented)

Metadata extraction service

Relationship detection algorithms

Schema context API

Table recommendation engine

SQL Generator

(Template-based SQL generation) SQL template system for common query patterns

Dynamic query building based on intent + schema context

Query validation and syntax checking

Error recovery and alternative query generation

Integration

Development environment (mcr-dev)

Databricks warehouse creation

Technical Stack

Backend

FastAPI with Python 3.9+

Databricks SQL Connector for warehouse connection

http://Socket.io  for WebSocket support (optional)

NLP Processing

OpenAI GPT-4 API or Anthropic Claude API

spaCy for basic NLP preprocessing

NLTK for text processing utilities

Fuzzy string matching libraries (fuzzywuzzy)

Discussion

NLP-to-SQL Strategy

Leverage existing LLM APIs (OpenAI GPT-4, Claude, or open-source alternatives)

Need to investigate see how we can get hands on the openai models

Domain knowledge ingestion:

Inject schema context into prompts

Create few-shot examples for specific data patterns

Build validation layers to catch and fix common errors

Template + AI approach:

Pre-built SQL templates for common patterns

LLM fills in specifics based on natural language

More reliable than pure generative approaches (suggestion from Toni A based on his interaction)

Hopefully by end of the 3 days we can get something like this to work Flow

User Input: "How many POIs changed in the latest OSM version?"
         ↓
Intent Parser: AGGREGATE + FILTER + TIME_BASED
Entities: [POIs, latest, version, changed]
         ↓
Schema Service: Identifies relevant tables (osm_changesets, poi_data)
         ↓
SQL Generator: 
SELECT COUNT(*) FROM poi_data p
JOIN osm_changesets c ON p.changeset_id = c.id  
WHERE c.version = (SELECT MAX(version) FROM osm_changesets)
AND p.status = 'modified'


Project Scope

Support 5-10 common query patterns

Handle 2-3 table JOINs reliably

Basic error handling and query validation

Clean chat interface with result visualization

Real-time query execution feedback

(For later)

Complex multi-table operations (4+ tables)

geo queries

Performance optimization with query caching