import os
from dotenv import load_dotenv
import pandas as pd
import psycopg2
from rag_engine import generate_sql_with_rag
import streamlit as st

load_dotenv()

st.set_page_config(
    page_title="CineStream RAG Text-to-SQL Platform",
    page_icon="🎬",
    layout="wide",
)

st.title("🎬 CineStream: RAG-Powered Text-to-SQL Platform")
st.markdown(
    "Query relational CineStream schema using natural language. "
    "Powered by **ChromaDB Vector Retrieval** and **Gemini LLM**."
)


# -----------------------------------------------------------------------------
# Database Connection (Fast Timeout)
# -----------------------------------------------------------------------------
def get_db_connection():
  db_url = os.getenv("DATABASE_URL")
  if not db_url:
    return None
  try:
    return psycopg2.connect(db_url, sslmode="require", connect_timeout=3)
  except Exception:
    return None


# -----------------------------------------------------------------------------
# Fast Audit Logging
# -----------------------------------------------------------------------------
def log_query_execution(
    natural_query: str, sql: str, status: str, error_msg: str = None
):
  conn = get_db_connection()
  if conn:
    try:
      with conn.cursor() as cur:
        cur.execute(
            """
                    CREATE TABLE IF NOT EXISTS query_audit_logs (
                        log_id SERIAL PRIMARY KEY,
                        natural_query TEXT NOT NULL,
                        generated_sql TEXT NOT NULL,
                        execution_status VARCHAR(50) NOT NULL,
                        error_message TEXT,
                        executed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                    );
                """
        )
        cur.execute(
            """
                    INSERT INTO query_audit_logs (natural_query, generated_sql, execution_status, error_message)
                    VALUES (%s, %s, %s, %s);
                """,
            (natural_query, sql, status, error_msg),
        )
        conn.commit()
    except Exception:
      conn.rollback()
    finally:
      conn.close()


# -----------------------------------------------------------------------------
# Streamlit-Cached SQL Generation
# -----------------------------------------------------------------------------
@st.cache_data(show_spinner=False)
def cached_generate_sql(query: str):
  return generate_sql_with_rag(query)


# -----------------------------------------------------------------------------
# User Interface
# -----------------------------------------------------------------------------
user_query = st.text_input(
    "Enter your business question:",
    value="Show all movies",
    placeholder="e.g., Find movies with rating above genre average",
)

if st.button("Generate SQL", type="primary"):
  if user_query:
    with st.spinner("Processing via ChromaDB & Gemini..."):
      generated_sql, retrieved_context = cached_generate_sql(user_query)

    if generated_sql:
      st.subheader("Generated PostgreSQL Query")
      st.code(generated_sql, language="sql")

      with st.expander("🔍 Inspect Retrieved ChromaDB Vector Context"):
        st.info(retrieved_context)

      # Automated Database Execution against Supabase
      st.subheader("Query Execution & Live Database Results")
      conn = get_db_connection()
      if conn:
        try:
          df = pd.read_sql_query(generated_sql, conn)
          st.success(
              f"Query executed successfully! Returned {len(df)} row(s)."
          )
          st.dataframe(df, use_container_width=True)
          log_query_execution(user_query, generated_sql, "SUCCESS")
        except Exception as sql_err:
          st.error(f"Execution Error: {sql_err}")
          log_query_execution(user_query, generated_sql, "FAILED", str(sql_err))
        finally:
          conn.close()
      else:
        st.warning(
            "Live Supabase connection timed out. Showing generated SQL only."
        )
    else:
      st.error(retrieved_context)

with st.expander("📜 View Live Database Audit Logs"):
  conn = get_db_connection()
  if conn:
    try:
      logs_df = pd.read_sql_query(
          "SELECT * FROM query_audit_logs ORDER BY executed_at DESC LIMIT 10;",
          conn,
      )
      st.dataframe(logs_df, use_container_width=True)
    except Exception:
      pass
    finally:
      conn.close()