import os
import shutil
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.document_loaders import DirectoryLoader, TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter

# --- CONFIG ---
DATA_PATH = "scheme_data_final"  
DB_PATH = "chroma_db_data"

def ingest_data():
    # 1. CHECK IF DATA EXISTS
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: Folder '{DATA_PATH}' not found.")
        return

    print(f"📂 Loading documents from '{DATA_PATH}'...")
    
    # 2. LOAD DOCUMENTS
    loader = DirectoryLoader(DATA_PATH, glob="*.txt", loader_cls=TextLoader, loader_kwargs={'encoding': 'utf-8'})
    documents = loader.load()
    
    if len(documents) == 0:
        print("❌ Error: No documents found!")
        return
        
    print(f"   ✅ Loaded {len(documents)} schemes.")

    # 3. SPLIT TEXT
    print("✂️  Splitting documents into chunks...")
    text_splitter = RecursiveCharacterTextSplitter(
        chunk_size=1000,
        chunk_overlap=200,
        separators=["DETAILS:", "BENEFITS:", "\n\n", "\n", " ", ""]
    )
    chunks = text_splitter.split_documents(documents)
    print(f"   ✅ Created {len(chunks)} chunks.")

    # 4. EMBED & STORE
    print("🧠 Generating Embeddings & Appending to DB...")
    
    # Create the Vector Store
    # We are NOT deleting the old DB. We are just adding to it.
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    
    vectorstore = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_function,
        persist_directory=DB_PATH
    )
    
    print(f"🎉 Success! Data added to '{DB_PATH}'.")

if __name__ == "__main__":
    ingest_data()