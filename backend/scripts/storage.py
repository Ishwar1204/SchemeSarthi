import os
import uuid
from dotenv import load_dotenv
from supabase import create_client

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

def get_supabase_client():
    """Get a Supabase client instance."""
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    return create_client(url, key)

def upload_document(file_bytes, original_filename, content_type="application/octet-stream"):
    """
    Upload a document to Supabase Storage.
    Returns the public URL of the uploaded file.
    """
    supabase = get_supabase_client()
    
    # Generate a unique filename to avoid collisions
    ext = original_filename.split(".")[-1] if "." in original_filename else "bin"
    unique_name = f"{uuid.uuid4().hex}_{original_filename}"
    storage_path = f"uploads/{unique_name}"
    
    # Upload to the 'documents' bucket
    response = supabase.storage.from_("documents").upload(
        path=storage_path,
        file=file_bytes,
        file_options={"content-type": content_type}
    )
    
    # Get public URL
    public_url = supabase.storage.from_("documents").get_public_url(storage_path)
    
    return public_url
