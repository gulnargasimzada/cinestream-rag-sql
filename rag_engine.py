import os
import chromadb
from dotenv import load_dotenv
from google import genai

load_dotenv()

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

# ==============================================================================
# Persistent In-Memory State for Instant Retrieval
# ==============================================================================
_chroma_client = None
_collection = None
_genai_client = None


def get_vector_collection():
  """Maintains a singleton in-memory ChromaDB collection to avoid reload delays."""
  global _chroma_client, _collection
  if _collection is not None:
    return _collection

  _chroma_client = chromadb.Client()
  _collection = _chroma_client.get_or_create_collection(
      name="cinestream_schema_knowledge"
  )

  if _collection.count() == 0:
    knowledge_documents = [
        (
            "movies_schema",
            (
                "Table 'movies': Columns include movie_id (INT, Primary Key),"
                " title (VARCHAR), genre (VARCHAR: Action, Comedy, Crime, Drama,"
                " Sci-Fi), release_year (INT), rental_rate (NUMERIC), rating"
                " (NUMERIC: scale 1.0 to 10.0)."
            ),
            {"type": "schema", "table": "movies"},
        ),
        (
            "customers_schema",
            (
                "Table 'customers': Columns include customer_id (INT, Primary"
                " Key), full_name (VARCHAR), email (VARCHAR), country (VARCHAR),"
                " subscription_type (VARCHAR: Basic, Standard, Premium),"
                " created_at (TIMESTAMP)."
            ),
            {"type": "schema", "table": "customers"},
        ),
        (
            "rentals_schema",
            (
                "Table 'rentals': Fact table containing rental_id (INT, Primary"
                " Key), customer_id (INT, Foreign Key referencing"
                " customers.customer_id), movie_id (INT, Foreign Key"
                " referencing movies.movie_id), rental_date (TIMESTAMP),"
                " return_date (TIMESTAMP), amount_paid (NUMERIC)."
            ),
            {"type": "schema", "table": "rentals"},
        ),
        (
            "relational_semantics",
            (
                "Relational Semantics: customers.customer_id joins with"
                " rentals.customer_id. movies.movie_id joins with"
                " rentals.movie_id. To calculate spending or financial revenue,"
                " aggregate SUM(rentals.amount_paid). To isolate movies rented"
                " by customer, join rentals with movies on movie_id."
            ),
            {"type": "relationships"},
        ),
    ]

    ids = [item[0] for item in knowledge_documents]
    documents = [item[1] for item in knowledge_documents]
    metadatas = [item[2] for item in knowledge_documents]
    _collection.add(ids=ids, documents=documents, metadatas=metadatas)

  return _collection


def get_genai_client():
  global _genai_client
  if _genai_client is None:
    _genai_client = genai.Client(api_key=GEMINI_API_KEY)
  return _genai_client


def retrieve_relevant_context(query: str, n_results: int = 2) -> str:
  """Queries cached ChromaDB to retrieve semantically matching schema context."""
  col = get_vector_collection()
  results = col.query(query_texts=[query], n_results=n_results)
  retrieved_docs = results.get("documents", [[]])[0]
  return "\n\n".join(retrieved_docs)


def generate_sql_with_rag(user_question: str) -> tuple[str, str]:
  """Instant RAG retrieval and direct invocation with active gemini-2.5-flash."""
  if not GEMINI_API_KEY:
    return (
        "",
        (
            "GEMINI_API_KEY is missing from environment variables (.env"
            " configuration required)."
        ),
    )

  context = retrieve_relevant_context(user_question, n_results=2)

  system_prompt = f"""You are a professional PostgreSQL database engineer. Synthesize an executable PostgreSQL query satisfying the user request strictly using the retrieved schema context.

### Retrieved Schema Context from Vector DB:
{context}

### User Natural Language Query:
{user_question}

### Strict Guidelines:
1. Return ONLY the raw SQL query. Do not wrap in markdown quotes (e.g. ```sql), and omit explanatory prose.
2. Ensure standard PostgreSQL syntax and strictly align with referenced table/column names.
3. Terminate the query with a semicolon.
"""

  try:
    client = get_genai_client()
    response = client.models.generate_content(
        model="gemini-3.8-flash",
        contents=system_prompt,
    )
    raw_sql = response.text.strip()

    if raw_sql.startswith("```sql"):
      raw_sql = raw_sql[6:]
    elif raw_sql.startswith("```"):
      raw_sql = raw_sql[3:]
    if raw_sql.endswith("```"):
      raw_sql = raw_sql[:-3]

    return raw_sql.strip(), context
  except Exception as e:
    return "", f"AI API generation error: {str(e)}"