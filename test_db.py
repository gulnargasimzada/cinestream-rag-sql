import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

def test_database_connection():
    """Verify that CI can securely connect to Supabase PostgreSQL using DATABASE_URL."""
    db_url = os.getenv("DATABASE_URL")
    assert db_url is not None, "DATABASE_URL environment variable is missing!"
    
    # Connect using session pooler
    conn = psycopg2.connect(db_url)
    cursor = conn.cursor()
    
    # Run a simple verification query
    cursor.execute("SELECT COUNT(*) FROM movies;")
    count = cursor.fetchone()[0]
    cursor.close()
    conn.close()
    
    # Check that test data exists
    assert count > 0, "No movies found in the database!"