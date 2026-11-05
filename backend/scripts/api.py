import os
import io
import tempfile
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, UploadFile, File, Form
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from langchain_chroma import Chroma
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_groq import ChatGroq
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser
from groq import Groq
from gtts import gTTS
import PyPDF2
from PIL import Image

from scripts.db import init_db, save_verification, get_session_history
from scripts.storage import upload_document

# Load environment variables
load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".env"))

# --- 1. SETUP & CONFIG ---
app = FastAPI(title="SchemeSaarthi Agentic API")

class QueryRequest(BaseModel):
    question: str
    language: str = "English"

class SpeakRequest(BaseModel):
    text: str
    language: str = "English"

# Global Variables
vectorstore = None
retriever = None
llm = None
groq_client = None

# --- 2. SPECIALIST PROMPTS (The Agents) ---

# Agent 1: Eligibility Specialist
eligibility_template = """You are the Eligibility Reasoning Agent. 
Your goal is to determine if a user qualifies for the scheme based on the rules.
1. Compare the user's details in the question to the criteria in the context.
2. If details are missing (like income or caste), explicitly ask for them.
3. Be strict. Cite the specific rule.

Context: {context}
Question: {question}
Analysis:"""

# Agent 2: Document Specialist
document_template = """You are the Document Readiness Agent.
List ONLY the official documents required based on the context.
1. Group them logically (Identity, Income, Property).
2. Mention any validity requirements (e.g., "Must be issued within 6 months").

Context: {context}
Question: {question}
Checklist:"""

# Agent 3: Rejection Diagnosis Agent (The Novel Angle)
rejection_template = """You are the Rejection Diagnosis Agent.
The user failed to get the benefit. Analyze the context to find "exclusion criteria" or common rejection reasons.
1. Explain WHY applications usually fail.
2. Suggest a fix if possible.
3. Use empathetic but professional language.

Context: {context}
Question: {question}
Diagnosis:"""

# Default Agent (Fallback)
general_template = """You are SchemeSaarthi. Answer the question helpfully based on the context.
Context: {context}
Question: {question}
Answer:"""

# Agent 5: Document Verification Agent (NEW)
verification_template = """You are the Document Verification Agent for Indian government schemes.
You have been given the text extracted from a document uploaded by a user, and the name of the scheme they are applying for.

Your job:
1. Identify what TYPE of document this is (Aadhaar, Income Certificate, Caste Certificate, PAN, etc.)
2. Check if this document type is typically REQUIRED for the given scheme.
3. Look for any red flags: expired dates, missing info, inconsistencies.
4. Give a clear VERDICT: VALID, INVALID, or NEEDS_REVIEW.

Scheme Context (from knowledge base):
{context}

Scheme Name: {scheme_name}

Extracted Document Text:
{document_text}

Provide your analysis in this format:
📄 Document Type: [identified type]
✅ Relevance to Scheme: [Yes/No + explanation]
🔍 Issues Found: [any problems or "None"]
📋 Verdict: [VALID / INVALID / NEEDS_REVIEW]
💡 Recommendation: [what the user should do next]"""

# --- 3. THE ORCHESTRATOR (The Router) ---
def get_router_decision(question):
    """
    Decides which agent should handle the request.
    This is a simple keyword-based router for speed (since we are running local).
    For production, we would use an LLM classifier here.
    """
    q = question.lower()
    
    if any(x in q for x in ["eligible", "am i", "can i apply", "qualify", "criteria"]):
        return "eligibility", eligibility_template
    elif any(x in q for x in ["document", "paper", "certificate", "proof", "attach"]):
        return "documents", document_template
    elif any(x in q for x in ["reject", "fail", "deny", "status", "wrong", "reason"]):
        return "rejection", rejection_template
    else:
        return "general", general_template

# --- 4. STARTUP ---
@app.on_event("startup")
async def load_system():
    global vectorstore, retriever, llm, groq_client
    print("[INFO] Booting up Agentic Architecture...")
    
    # Path Setup
    current_dir = os.path.dirname(os.path.abspath(__file__))
    db_path = os.path.join(current_dir, "..", "chroma_db_data")

    # Load Memory
    embedding_function = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    vectorstore = Chroma(persist_directory=db_path, embedding_function=embedding_function)
    retriever = vectorstore.as_retriever(search_kwargs={"k": 4})
    
    # Load Brain (LLM)
    print("[INFO] Configuring Groq (Llama 3.3 70B)...")
    llm = ChatGroq(model="llama-3.3-70b-versatile", api_key=os.getenv("GROQ_API_KEY")) 
    
    # Load Groq client for Whisper (STT)
    groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
    
    # Initialize Neon DB
    try:
        init_db()
    except Exception as e:
        print(f"[WARNING] Neon DB init failed: {e}")
    
    print("[INFO] Orchestrator Ready (Groq + Whisper + Neon + Supabase)!")

# --- 5. CHAT ENDPOINT ---
@app.post("/ask")
async def ask_agent(request: QueryRequest):
    print(f"[INFO] Incoming: {request.question}")
    
    # A. ORCHESTRATION STEP
    intent, selected_template = get_router_decision(request.question)
    print(f"[INFO] Router Decision: Sending to {intent.upper()} AGENT")
    
    # B. RETRIEVAL STEP
    docs = retriever.invoke(request.question)
    context_text = "\n\n".join(doc.page_content for doc in docs)
    
    # C. GENERATION STEP
    try:
        prompt = ChatPromptTemplate.from_template(selected_template)
        chain = prompt | llm | StrOutputParser()
        response_text = chain.invoke({"context": context_text, "question": request.question})
    except Exception as e:
        print(f"[ERROR] Generation Error: {e}")
        response_text = "I encountered an error generating the response. Please try again."
    
    return {
        "answer": response_text,
        "agent_used": intent,
        "source_docs": len(docs)
    }

# --- 6. AUDIO: SPEECH-TO-TEXT (Groq Whisper) ---
@app.post("/transcribe")
async def transcribe_audio(
    audio: UploadFile = File(...),
    language: str = Form("en")
):
    """Transcribe audio to text using Groq Whisper."""
    print(f"[INFO] Transcribing audio... (language: {language})")
    
    try:
        # Read the uploaded audio file
        audio_bytes = await audio.read()
        
        # Save to a temp file (Groq SDK needs a file-like object with a name)
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
            tmp.write(audio_bytes)
            tmp_path = tmp.name
        
        # Call Groq Whisper API
        with open(tmp_path, "rb") as audio_file:
            transcription = groq_client.audio.transcriptions.create(
                file=("audio.wav", audio_file),
                model="whisper-large-v3-turbo",
                language=language,
                response_format="text"
            )
        
        # Clean up temp file
        os.unlink(tmp_path)
        
        print(f"[INFO] Transcription: {transcription}")
        return {"text": transcription, "language": language}
        
    except Exception as e:
        print(f"[ERROR] Transcription failed: {e}")
        raise HTTPException(status_code=500, detail=f"Transcription failed: {str(e)}")

# --- 7. AUDIO: TEXT-TO-SPEECH (gTTS) ---
@app.post("/speak")
async def text_to_speech(request: SpeakRequest):
    """Convert text to speech using gTTS."""
    print(f"[INFO] Generating speech... (language: {request.language})")
    
    try:
        lang_code = "hi" if request.language.lower() == "hindi" else "en"
        
        tts = gTTS(text=request.text, lang=lang_code, slow=False)
        
        # Generate MP3 into memory
        audio_buffer = io.BytesIO()
        tts.write_to_fp(audio_buffer)
        audio_buffer.seek(0)
        
        return StreamingResponse(
            audio_buffer,
            media_type="audio/mpeg",
            headers={"Content-Disposition": "inline; filename=response.mp3"}
        )
        
    except Exception as e:
        print(f"[ERROR] TTS failed: {e}")
        raise HTTPException(status_code=500, detail=f"TTS failed: {str(e)}")

# --- 8. DOCUMENT VERIFICATION ---
@app.post("/verify-document")
async def verify_document(
    file: UploadFile = File(...),
    scheme_name: str = Form("General"),
    session_id: str = Form("default")
):
    """Upload, extract text, verify document against scheme, and store results."""
    print(f"[INFO] Verifying document '{file.filename}' for scheme '{scheme_name}'")
    
    try:
        file_bytes = await file.read()
        file_type = file.filename.split(".")[-1].lower() if "." in file.filename else "unknown"
        
        # --- A. EXTRACT TEXT ---
        extracted_text = ""
        
        if file_type == "pdf":
            # Extract text from PDF
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
            for page in pdf_reader.pages:
                page_text = page.extract_text()
                if page_text:
                    extracted_text += page_text + "\n"
        elif file_type in ["jpg", "jpeg", "png", "bmp"]:
            # For images, note that text extraction is limited without OCR
            extracted_text = "[Image uploaded — visual document. OCR text extraction is limited. Please verify manually or upload PDF version.]"
        else:
            extracted_text = f"[Unsupported file type: {file_type}]"
        
        if not extracted_text.strip():
            extracted_text = "[No readable text could be extracted from this document.]"
        
        # --- B. UPLOAD TO SUPABASE STORAGE ---
        file_url = ""
        try:
            file_url = upload_document(file_bytes, file.filename, file.content_type or "application/octet-stream")
            print(f"[INFO] File uploaded to Supabase: {file_url}")
        except Exception as e:
            print(f"[WARNING] Supabase upload failed: {e}")
            file_url = "upload_failed"
        
        # --- C. LLM VERIFICATION ---
        # Get scheme context from vector store
        docs = retriever.invoke(scheme_name)
        context_text = "\n\n".join(doc.page_content for doc in docs)
        
        # Run verification through the LLM
        prompt = ChatPromptTemplate.from_template(verification_template)
        chain = prompt | llm | StrOutputParser()
        
        verification_result = chain.invoke({
            "context": context_text,
            "scheme_name": scheme_name,
            "document_text": extracted_text[:3000]  # Limit to avoid token overflow
        })
        
        # Determine validity from the verdict
        is_valid = "VALID" in verification_result and "INVALID" not in verification_result
        
        # --- D. SAVE TO NEON DB ---
        record_id = None
        try:
            record_id = save_verification(
                session_id=session_id,
                filename=file.filename,
                file_type=file_type,
                scheme_name=scheme_name,
                file_url=file_url,
                extracted_text=extracted_text[:5000],  # Limit storage
                verification_result=verification_result,
                is_valid=is_valid
            )
            print(f"[INFO] Verification saved to Neon DB (ID: {record_id})")
        except Exception as e:
            print(f"[WARNING] Neon DB save failed: {e}")
        
        return {
            "filename": file.filename,
            "scheme_name": scheme_name,
            "verification_result": verification_result,
            "is_valid": is_valid,
            "file_url": file_url,
            "record_id": record_id
        }
        
    except Exception as e:
        print(f"[ERROR] Document verification failed: {e}")
        raise HTTPException(status_code=500, detail=f"Verification failed: {str(e)}")

# --- 9. VERIFICATION HISTORY ---
@app.get("/verification-history/{session_id}")
async def get_history(session_id: str):
    """Get document verification history for a session."""
    try:
        rows = get_session_history(session_id)
        history = []
        for row in rows:
            history.append({
                "id": row[0],
                "filename": row[1],
                "scheme_name": row[2],
                "verification_result": row[3],
                "is_valid": row[4],
                "uploaded_at": str(row[5]),
                "file_url": row[6]
            })
        return {"history": history}
    except Exception as e:
        print(f"[ERROR] History fetch failed: {e}")
        return {"history": [], "error": str(e)}

@app.get("/")
def home():
    return {"status": "Agent Orchestrator Online 🟢 (Audio + Documents + DB)"}