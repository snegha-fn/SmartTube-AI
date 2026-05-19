import streamlit as st
import ollama
import time
import re
from youtube_transcript_api import YouTubeTranscriptApi

# ====================== PAGE CONFIG ======================
st.set_page_config(
    page_title="SmartTube AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ====================== SESSION STATE ======================
for key in ["history", "transcript", "transcript_list", "summary", 
            "messages", "summary_time", "video_id", "word_count", "current_url"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ["history", "messages", "transcript_list"] else ""

# ====================== HELPERS ======================
def extract_video_id(url: str) -> str:
    patterns = [
        r"v=([A-Za-z0-9_-]{11})",
        r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"embed/([A-Za-z0-9_-]{11})",
        r"shorts/([A-Za-z0-9_-]{11})",
    ]
    for p in patterns:
        m = re.search(p, url)
        if m:
            return m.group(1)
    return url.strip().split("/")[-1].split("?")[0]

def format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    return f"{h}:{m:02d}:{s:02d}" if h else f"{m}:{s:02d}"

def get_transcript(video_id: str):
    """Robust transcript fetching"""
    try:
        return YouTubeTranscriptApi().fetch(video_id)
    except:
        try:
            return YouTubeTranscriptApi.get_transcript(video_id)
        except Exception as e:
            raise ValueError(f"Could not fetch transcript: {e}")

def create_context(transcript_list, max_segments=110):
    """Smart context sampling for faster inference"""
    if len(transcript_list) <= max_segments:
        segs = transcript_list
    else:
        step = max(1, len(transcript_list) // max_segments)
        segs = transcript_list[::step]
    
    if isinstance(segs[0], dict):
        return "\n".join([f"[{format_time(item['start'])}] {item['text']}" for item in segs])
    else:
        return "\n".join([f"[{format_time(item.start)}] {item.text}" for item in segs])

# ====================== PROMPTS ======================
SUMMARY_PROMPT = """You are an expert YouTube content analyst. Create a clean, compelling summary.

Transcript:
{transcript}

Return **exactly** this format (no extra text):

# [Sharp, attractive title]

## TL;DR
[2-3 crisp, powerful sentences]

## 🔑 Key Insights
- [Clear insight with brief explanation]
- [Clear insight with brief explanation]
- [Clear insight with brief explanation]

## 📌 Standout Moments
- [Specific example or fact from video]
- [Specific example or fact from video]

## 🎯 Best For
[One sentence: who should watch this video]"""

CHAT_PROMPT = """You are an expert assistant who has watched this video.
Answer strictly based on the transcript only.

Transcript with timestamps:
{transcript}

Question: {question}

Answer naturally and concisely. Use [mm:ss] for timestamps when helpful."""

# ====================== UI ======================
tab1, tab2, tab3 = st.tabs(["🎬 New Video", "📜 History", "⚙️ Settings"])

with tab1:
    st.markdown("""
    <div style="text-align:center; padding: 2rem 0;">
        <h1 style="font-size: 3.2rem; background: linear-gradient(90deg, #a78bfa, #34d399, #60a5fa); 
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            🎬 SmartTube AI
        </h1>
        <p style="font-size: 1.2rem; color: #9ca3af;">YouTube Summary + Intelligent Chat</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([6, 1.4])
    with col1:
        url = st.text_input(
            "YouTube URL", 
            placeholder="https://www.youtube.com/watch?v=...",
            label_visibility="collapsed"
        )
    with col2:
        summarize_btn = st.button("⚡ Summarize", type="primary", use_container_width=True)

    # ====================== SUMMARIZE LOGIC ======================
    if (summarize_btn or (url and url != st.session_state.current_url and url.strip())) and url.strip():
        st.session_state.current_url = url
        t0 = time.time()
        progress = st.progress(0, text="Fetching transcript...")

        try:
            video_id = extract_video_id(url)
            transcript_list = get_transcript(video_id)

            # Handle both dict and object formats
            if isinstance(transcript_list[0], dict):
                full_text = " ".join([item['text'] for item in transcript_list])
                get_start = lambda x: x['start']
            else:
                full_text = " ".join([item.text for item in transcript_list])
                get_start = lambda x: x.start

            word_count = len(full_text.split())
            truncated = full_text[:14500]

            progress.progress(40, text="AI is thinking...")

            response = ollama.chat(
                model="phi3:mini",
                messages=[{"role": "user", "content": SUMMARY_PROMPT.format(transcript=truncated)}],
                options={"temperature": 0.3, "num_predict": 800, "num_ctx": 8192}
            )

            elapsed = round(time.time() - t0, 1)
            summary_text = response["message"]["content"]
            title = summary_text.split("\n")[0].replace("#", "").strip()

            # Save to history
            st.session_state.history.insert(0, {
                "title": title[:90],
                "url": url,
                "summary": summary_text,
                "transcript": full_text,
                "transcript_list": transcript_list,
                "video_id": video_id,
                "time": elapsed
            })

            # Update current session
            st.session_state.summary = summary_text
            st.session_state.transcript = full_text
            st.session_state.transcript_list = transcript_list
            st.session_state.summary_time = elapsed
            st.session_state.video_id = video_id
            st.session_state.word_count = word_count
            st.session_state.messages = []

            progress.progress(100, text="✅ Done!")
            time.sleep(0.4)
            progress.empty()

        except Exception as e:
            progress.empty()
            st.error(f"**Error:** {str(e)}")

    # ====================== DISPLAY SUMMARY & CHAT ======================
    if st.session_state.summary:
        duration = st.session_state.transcript_list[-1].start if hasattr(st.session_state.transcript_list[-1], 'start') else st.session_state.transcript_list[-1]['start']

        st.markdown(f"**Duration:** {format_time(duration)} | **Words:** {st.session_state.word_count:,} | **Processed in:** {st.session_state.summary_time}s")

        st.markdown("### 📝 Summary")
        st.markdown(st.session_state.summary)

        st.markdown("### 💬 Chat with the Video")
        for msg in st.session_state.messages:
            with st.chat_message(msg["role"]):
                st.markdown(msg["content"])

        if prompt := st.chat_input("Ask anything about the video..."):
            st.session_state.messages.append({"role": "user", "content": prompt})
            with st.chat_message("user"):
                st.markdown(prompt)

            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    t0 = time.time()
                    context = create_context(st.session_state.transcript_list)
                    resp = ollama.chat(
                        model="phi3:mini",
                        messages=[{"role": "user", "content": CHAT_PROMPT.format(transcript=context, question=prompt)}],
                        options={"temperature": 0.25, "num_predict": 600, "num_ctx": 8192}
                    )
                    answer = resp["message"]["content"]
                    elapsed = round(time.time() - t0, 1)
                st.markdown(answer)
                st.caption(f"⚡ {elapsed}s")
            st.session_state.messages.append({"role": "assistant", "content": answer})

# ====================== HISTORY TAB ======================
with tab2:
    st.subheader("📜 History")
    if not st.session_state.history:
        st.info("No videos summarized yet. Start in the **New Video** tab.")
    else:
        for i, item in enumerate(st.session_state.history):
            with st.expander(f"🎬 {item['title']}", expanded=False):
                st.caption(item['url'])
                st.write(item['summary'][:400] + "...")
                if st.button("Load", key=f"load_{i}"):
                    st.session_state.summary = item["summary"]
                    st.session_state.transcript = item["transcript"]
                    st.session_state.transcript_list = item["transcript_list"]
                    st.session_state.messages = []
                    st.switch_tab(tab1)

# ====================== SETTINGS TAB ======================
with tab3:
    st.subheader("⚙️ Settings")
    if st.button("🗑️ Clear All History"):
        st.session_state.history = []
        st.success("History cleared!")
        time.sleep(1)
        st.rerun()

st.caption("SmartTube AI • Built with Streamlit + Ollama (phi3:mini) • Optimized for CPU")
