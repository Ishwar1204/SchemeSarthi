import os
from dotenv import load_dotenv
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough

# --- CONFIG ---
# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# Path to your existing database
CURRENT_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(CURRENT_DIR, "..", "chroma_db_data")

# --- 1. SETUP THE RETRIEVER (The Search Engine) ---
embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vectorstore = Chroma(persist_directory=DB_PATH, embedding_function=embedding_function)
retriever = vectorstore.as_retriever(search_kwargs={"k": 3})

# --- 2. SETUP THE LLM (The Brain) ---

llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY")) 

# --- 3. DEFINE THE PROMPT (The Instructions) ---
# This tells the AI how to behave.
template = """You are SchemeSaarthi, an expert government scheme assistant for India.
Use the following pieces of retrieved context to answer the user's question.
If you don't know the answer, just say that you don't know, don't try to make up an answer.
Keep the answer concise and helpful.

Context:
{context}

Question:
{question}

Answer:"""

prompt = ChatPromptTemplate.from_template(template)

# --- 4. BUILD THE CHAIN (Input -> Search -> Think -> Output) ---
def format_docs(docs):
    return "\n\n".join(doc.page_content for doc in docs)

rag_chain = (
    {"context": retriever | format_docs, "question": RunnablePassthrough()}
    | prompt
    | llm
)

# --- 5. RUN THE INTERACTIVE LOOP ---
if __name__ == "__main__":
    print("🤖 SchemeSaarthi is Ready! (Type 'exit' to stop)")
    print("-" * 50)
    
    while True:
        user_query = input("\n🗣️  You: ")
        if user_query.lower() in ["exit", "quit"]:
            break
            
        print("thinking...", end="", flush=True)
        
        # Stream the response so it looks like it's typing
        response = rag_chain.invoke(user_query)
        
        print(f"\r🤖 Saarthi: {response.content}")
        print("-" * 50)