import streamlit as st
import requests
import uuid

# --- CONFIG ---
API_URL = "http://127.0.0.1:8000"
PAGE_TITLE = "SchemeSaarthi AI 🇮🇳"
PAGE_ICON = "🚜"

# --- PAGE SETUP ---
st.set_page_config(page_title=PAGE_TITLE, page_icon=PAGE_ICON, layout="wide")

# Generate a unique session ID
if "session_id" not in st.session_state:
    st.session_state.session_id = str(uuid.uuid4())[:8]

# --- HEADER ---
st.title(f"{PAGE_ICON} {PAGE_TITLE}")
st.markdown("### Your Personal Assistant for Government Schemes")

# --- SIDEBAR ---
with st.sidebar:
    st.header("⚙️ Settings")
    language = st.selectbox("🌐 Select Language", ["English", "Hindi"])
    lang_code = "hi" if language == "Hindi" else "en"
    
    st.divider()
    
    # --- INPUT MODE ---
    st.header("🎤 Input Mode")
    input_mode = st.radio("Choose how to ask:", ["💬 Type", "🎙️ Voice"], horizontal=True)
    
    # Voice response toggle
    enable_voice_response = st.toggle("🔊 Voice Response", value=False, help="Hear the agent's answer as audio")
    
    st.divider()
    
    if st.button("🗑️ Clear Chat", use_container_width=True):
        st.session_state.messages = []
        st.rerun()

# --- TABS ---
tab_chat, tab_docs = st.tabs(["💬 Chat", "📄 Document Verification"])

# ========================================
# TAB 1: CHAT (Text + Audio)
# ========================================
with tab_chat:
    # --- CHAT HISTORY ---
    if "messages" not in st.session_state:
        st.session_state.messages = []

    # Display previous messages
    for message in st.session_state.messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

    # --- VOICE INPUT MODE ---
    if input_mode == "🎙️ Voice":
        st.info(f"🎤 Click the microphone to record your question in **{language}**")
        
        try:
            from audio_recorder_streamlit import audio_recorder
            audio_bytes = audio_recorder(
                text="Click to record",
                recording_color="#e74c3c",
                neutral_color="#2c3e50",
                icon_size="2x",
                pause_threshold=2.0,
                sample_rate=16000
            )
        except ImportError:
            audio_bytes = None
            st.warning("Audio recorder not available. Please install: `pip install audio-recorder-streamlit`")
        
        if audio_bytes:
            st.audio(audio_bytes, format="audio/wav")
            
            with st.spinner("🧠 Transcribing your speech..."):
                try:
                    # Send to /transcribe
                    files = {"audio": ("recording.wav", audio_bytes, "audio/wav")}
                    data = {"language": lang_code}
                    resp = requests.post(f"{API_URL}/transcribe", files=files, data=data, timeout=30)
                    
                    if resp.status_code == 200:
                        transcribed = resp.json().get("text", "").strip()
                        
                        if transcribed:
                            st.success(f"📝 You said: *\"{transcribed}\"*")
                            
                            # Add to chat
                            st.session_state.messages.append({"role": "user", "content": f"🎤 {transcribed}"})
                            
                            # Now ask the agent
                            with st.spinner("🧠 Agent is thinking..."):
                                payload = {"question": transcribed, "language": language}
                                agent_resp = requests.post(f"{API_URL}/ask", json=payload, timeout=60)
                                
                                if agent_resp.status_code == 200:
                                    data = agent_resp.json()
                                    answer = data.get("answer", "No answer received.")
                                    agent_name = data.get("agent_used", "General").upper()
                                    
                                    full_answer = f"**🛡️ Agent: `{agent_name}`**\n\n{answer}"
                                    st.session_state.messages.append({"role": "assistant", "content": full_answer})
                                    
                                    # Voice response
                                    if enable_voice_response:
                                        with st.spinner("🔊 Generating audio response..."):
                                            tts_resp = requests.post(
                                                f"{API_URL}/speak",
                                                json={"text": answer, "language": language},
                                                timeout=30
                                            )
                                            if tts_resp.status_code == 200:
                                                st.audio(tts_resp.content, format="audio/mpeg")
                                    
                                    st.rerun()
                        else:
                            st.warning("Couldn't understand the audio. Please try again.")
                    else:
                        st.error(f"Transcription failed (Status {resp.status_code})")
                except Exception as e:
                    st.error(f"🚨 Error: {e}")

    # --- TEXT INPUT MODE ---
    if prompt := st.chat_input("Ask about PMAY, Eligibility, or Documents..."):
        # Show user message
        st.session_state.messages.append({"role": "user", "content": prompt})
        with st.chat_message("user"):
            st.markdown(prompt)

        # Call the API
        with st.chat_message("assistant"):
            status_placeholder = st.empty()
            status_placeholder.markdown("🧠 *Orchestrator is analyzing intent...*")
            
            try:
                payload = {"question": prompt, "language": language}
                response = requests.post(f"{API_URL}/ask", json=payload, timeout=60)
                
                if response.status_code == 200:
                    data = response.json()
                    answer = data.get("answer", "No answer received.")
                    agent_name = data.get("agent_used", "General").upper()
                    
                    status_placeholder.markdown(f"**🛡️ Agent Active:** `{agent_name} Specialist`")
                    st.markdown(answer)
                    st.session_state.messages.append({"role": "assistant", "content": answer})
                    
                    # Voice response
                    if enable_voice_response:
                        with st.spinner("🔊 Generating audio..."):
                            tts_resp = requests.post(
                                f"{API_URL}/speak",
                                json={"text": answer, "language": language},
                                timeout=30
                            )
                            if tts_resp.status_code == 200:
                                st.audio(tts_resp.content, format="audio/mpeg")
                else:
                    status_placeholder.empty()
                    st.error(f"❌ Server Error (Status {response.status_code})")
                    st.code(response.text)
                    
            except Exception as e:
                status_placeholder.empty()
                st.error(f"🚨 Connection Error: {type(e).__name__}")
                st.info("Make sure the API server is running: `python -m uvicorn scripts.api:app --reload --port 8000`")

# ========================================
# TAB 2: DOCUMENT VERIFICATION
# ========================================
with tab_docs:
    st.header("📄 Document Verification Agent")
    st.markdown("Upload your documents and our AI will verify if they're valid for your chosen scheme.")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        uploaded_file = st.file_uploader(
            "Upload a document",
            type=["pdf", "jpg", "jpeg", "png"],
            help="Upload your Aadhaar, Income Certificate, Caste Certificate, or any other scheme document"
        )
    
    with col2:
        scheme_name = st.selectbox(
            "Select Scheme",
            [
                "PMAY (Pradhan Mantri Awas Yojana)",
                "Ladki Bahin Yojana",
                "PMAY-G (Gramin)",
                "Mahatma Jyotirao Phule Jan Arogya Yojana",
                "Maharashtra Swadhar Yojana",
                "Other"
            ]
        )
        
        if scheme_name == "Other":
            scheme_name = st.text_input("Enter scheme name:")
    
    if uploaded_file and scheme_name:
        if st.button("🔍 Verify Document", type="primary", use_container_width=True):
            with st.spinner("🧠 AI is analyzing your document..."):
                try:
                    files = {"file": (uploaded_file.name, uploaded_file.getvalue(), uploaded_file.type)}
                    data = {
                        "scheme_name": scheme_name,
                        "session_id": st.session_state.session_id
                    }
                    
                    resp = requests.post(f"{API_URL}/verify-document", files=files, data=data, timeout=60)
                    
                    if resp.status_code == 200:
                        result = resp.json()
                        
                        # Display result with styling
                        is_valid = result.get("is_valid", False)
                        
                        if is_valid:
                            st.success("✅ Document appears VALID for this scheme")
                        else:
                            st.warning("⚠️ Document may have issues — see details below")
                        
                        st.markdown("---")
                        st.markdown("### 🤖 Verification Analysis")
                        st.markdown(result.get("verification_result", "No result available."))
                        
                        # Show metadata
                        with st.expander("📊 Details"):
                            st.json({
                                "filename": result.get("filename"),
                                "scheme": result.get("scheme_name"),
                                "is_valid": result.get("is_valid"),
                                "file_url": result.get("file_url"),
                                "record_id": result.get("record_id")
                            })
                    else:
                        st.error(f"❌ Verification failed (Status {resp.status_code})")
                        st.code(resp.text)
                        
                except Exception as e:
                    st.error(f"🚨 Error: {e}")
    
    # --- VERIFICATION HISTORY ---
    st.divider()
    st.subheader("📜 Verification History")
    
    try:
        hist_resp = requests.get(f"{API_URL}/verification-history/{st.session_state.session_id}", timeout=10)
        if hist_resp.status_code == 200:
            history = hist_resp.json().get("history", [])
            if history:
                for item in history:
                    status_icon = "✅" if item["is_valid"] else "❌"
                    with st.expander(f"{status_icon} {item['filename']} — {item['scheme_name']} ({item['uploaded_at'][:10]})"):
                        st.markdown(item["verification_result"])
                        if item.get("file_url"):
                            st.markdown(f"[📎 View Document]({item['file_url']})")
            else:
                st.caption("No documents verified yet in this session.")
        else:
            st.caption("Could not load history.")
    except:
        st.caption("ℹ️ Start the API server to see verification history.")