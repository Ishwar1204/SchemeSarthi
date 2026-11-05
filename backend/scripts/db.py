import os
import psycopg2
from dotenv import load_dotenv

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

def get_connection():
    """Get a connection to the Neon PostgreSQL database."""
    return psycopg2.connect(os.getenv("NEON_DATABASE_URL"))

def init_db():
    """Create the document_verifications table if it doesn't exist."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        CREATE TABLE IF NOT EXISTS document_verifications (
            id SERIAL PRIMARY KEY,
            session_id TEXT,
            filename TEXT NOT NULL,
            file_type TEXT,
            scheme_name TEXT,
            file_url TEXT,
            extracted_text TEXT,
            verification_result TEXT,
            is_valid BOOLEAN,
            uploaded_at TIMESTAMP DEFAULT NOW()
        );
    """)
    conn.commit()
    cur.close()
    conn.close()
    print("[DB] ✅ Neon DB initialized — table ready.")

def save_verification(session_id, filename, file_type, scheme_name, file_url, extracted_text, verification_result, is_valid):
    """Save a document verification record to Neon DB."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        INSERT INTO document_verifications 
        (session_id, filename, file_type, scheme_name, file_url, extracted_text, verification_result, is_valid)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
        RETURNING id;
    """, (session_id, filename, file_type, scheme_name, file_url, extracted_text, verification_result, is_valid))
    record_id = cur.fetchone()[0]
    conn.commit()
    cur.close()
    conn.close()
    return record_id

def get_session_history(session_id):
    """Get all document verification records for a session."""
    conn = get_connection()
    cur = conn.cursor()
    cur.execute("""
        SELECT id, filename, scheme_name, verification_result, is_valid, uploaded_at, file_url
        FROM document_verifications 
        WHERE session_id = %s 
        ORDER BY uploaded_at DESC;
    """, (session_id,))
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return rows
