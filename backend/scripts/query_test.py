from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# Point to the same database folder
DB_PATH = "./chroma_db_data"

def search_scheme(query):
    # 1. Load the DB
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embedding_function)

    # 2. Perform the Search (Similarity Search)
    # k=3 means "give me the top 3 most relevant chunks"
    results = vectorstore.similarity_search(query, k=3)

    # 3. Display Results
    print(f"\n🔍 Query: {query}")
    print("-" * 50)
    
    if not results:
        print("No results found.")
    
    for i, doc in enumerate(results):
        print(f"📄 [Result {i+1}] (Source: Page {doc.metadata.get('page', '?')})")
        print(doc.page_content[:300] + "...") # Show just the first 300 chars
        print("-" * 50)

if __name__ == "__main__":
    # Test queries - Try changing these!
    search_scheme("What is the maximum income limit for EWS category?")
    search_scheme("Why was my application rejected?")