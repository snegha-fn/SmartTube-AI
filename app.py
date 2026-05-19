import streamlit as st
import ollama
import time
import re
from youtube_transcript_api import YouTubeTranscriptApi

# ─── Page Config ─────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SmartTube AI",
    page_icon="🎬",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# ─── Session State ───────────────────────────────────────────────────────────
for key in ["history", "transcript", "transcript_list", "summary", "messages", 
            "summary_time", "video_id", "word_count", "current_url"]:
    if key not in st.session_state:
        st.session_state[key] = [] if key in ["history", "messages", "transcript_list"] else ""

# ─── Helpers ────────────────────────────────────────────────────────────────
def extract_video_id(url: str) -> str:
    patterns = [
        r"v=([A-Za-z0-9_-]{11})", r"youtu\.be/([A-Za-z0-9_-]{11})",
        r"embed/([A-Za-z0-9_-]{11})", r"shorts/([A-Za-z0-9_-]{11})",
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
    """Optimized transcript fetcher"""
    try:
        return YouTubeTranscriptApi().fetch(video_id)
    except:
        try:
            return YouTubeTranscriptApi.get_transcript(video_id)
        except:
            try:
                return YouTubeTranscriptApi().fetch(video_id, languages=['en', 'en-US', 'en-GB'])
            except Exception as e:
                raise ValueError(f"Transcript unavailable: {e}")

def create_context(transcript_list, max_segments=110):
    """Smart sampling - better than taking only first N segments"""
    if len(transcript_list) <= max_segments:
        segs = transcript_list
    else:
        step = max(1, len(transcript_list) // max_segments)
        segs = transcript_list[::step]
    
    if isinstance(segs[0], dict):
        return "\n".join([f"[{format_time(item['start'])}] {item['text']}" for item in segs])
    else:
        return "\n".join([f"[{format_time(item.start)}] {item.text}" for item in segs])

# ─── Optimized Prompts ───────────────────────────────────────────────────────
SUMMARY_PROMPT = """You are an expert content analyst. Create a compelling, insight-rich summary of this YouTube video.

Transcript:
{transcript}

Respond in this **exact format** — nothing else outside these sections:

# [Craft a sharp, specific title]

## Summary
[2-3 crisp sentences. What is the video about and why it matters?]

## 🔑 Key Insights
- [Insight with brief explanation]
- [Insight with brief explanation]

## 📌 Standout Moments
- [Specific fact, example or technique]
- [Specific fact, example or technique]"""

CHAT_PROMPT = """You are an expert assistant with full knowledge of this YouTube video.

Answer the user's question based **strictly** on the transcript.
- Be concise and direct
- Include timestamps like [1:23] when citing specific parts
- Use bullet points for examples
- If information is not in the transcript, say so

Transcript:
{transcript}

Question: {question}
Answer:"""

# ─── Top Tabs ───────────────────────────────────────────────────────────────
tab1, tab2, tab3 = st.tabs(["🎬 New Video", "📜 History", "⚙️ Settings"])

# ====================== TAB 1: NEW VIDEO ======================
with tab1:
    st.markdown("""
    <div style="background: linear-gradient(135deg, #0d0d1a, #12091f); border: 1px solid #1e1e3a; 
                border-radius: 20px; padding: 2.8rem 3rem; margin-bottom: 2rem; text-align:center;">
        <h1 style="font-size: 3rem; font-weight: 800; background: linear-gradient(90deg, #a78bfa, #34d399, #60a5fa);
                   -webkit-background-clip: text; -webkit-text-fill-color: transparent;">
            🎬 SmartTube AI
        </h1>
        <p style="color:#9ca3af; font-size:1.1rem;">Fast Summary + Smart Chat</p>
    </div>
    """, unsafe_allow_html=True)

    col1, col2 = st.columns([6, 1.4])
    with col1:
        url = st.text_input("YouTube URL", placeholder="https://www.youtube.com/watch?v=...", label_visibility="collapsed")
    with col2:
        summarize_btn = st.button("⚡ Summarize", type="primary", use_container_width=True)

    # ─── Summarize Logic (Optimized) ─────────────────────────────────────────
    if (summarize_btn or (url and url != st.session_state.current_url and url.strip())) and url.strip():
        st.session_state.current_url = url
        t0 = time.time()
        progress = st.progress(0, text="Fetching transcript...")

        try:
            video_id = extract_video_id(url)
            transcript_list = get_transcript(video_id)

            # Handle both object and dict formats
            if isinstance(transcript_list[0], dict):
                full_text = " ".join(item['text'] for item in transcript_list)
                get_start = lambda x: x['start']
                get_text = lambda x: x['text']
            else:
                full_text = " ".join(item.text for item in transcript_list)
                get_start = lambda x: x.start
                get_text = lambda x: x.text

            word_count = len(full_text.split())
            truncated = full_text[:14000]   # Reduced for speed

            progress.progress(35, text="Generating summary...")

            # === OPTIMIZED OLLAMA CALL ===
            response = ollama.chat(
                model="phi3:mini",
                messages=[{"role": "user", "content": SUMMARY_PROMPT.format(transcript=truncated)}],
                options={
                    "temperature": 0.3,
                    "num_predict": 750,
                    "top_p": 0.9,
                    "num_ctx": 8192,
                }
            )

            elapsed = round(time.time() - t0, 1)
            summary_text = response["message"]["content"]
            title_line = summary_text.split("\n")[0].replace("#", "").strip()

            # Save to history
            st.session_state.history.insert(0, {
                "title": title_line[:80],
                "url": url,
                "summary": summary_text,
                "transcript": full_text,
                "transcript_list": transcript_list,
                "video_id": video_id,
                "time": elapsed
            })

            # Update session
            st.session_state.summary = summary_text
            st.session_state.transcript = full_text
            st.session_state.transcript_list = transcript_list
            st.session_state.summary_time = elapsed
            st.session_state.video_id = video_id
            st.session_state.word_count = word_count
            st.session_state.messages = []

            progress.progress(100, text="Done!")
            time.sleep(0.3)
            progress.empty()

        except Exception as e:
            progress.empty()
            st.error(f"**Error:** {e}")

    # ─── Display Summary + Chat ─────────────────────────────────────────────
    if st.session_state.summary:
        duration = (st.session_state.transcript_list[-1].start 
                   if not isinstance(st.session_state.transcript_list[0], dict) 
                   else st.session_state.transcript_list[-1]['start'])

        st.markdown(f"""
        <div style="display:flex; gap:1rem; margin:1rem 0;">
            <div style="background:#111118; border:1px solid #1e1e3a; border-radius:8px; padding:0.6rem 1.2rem;">
                🕐 {format_time(duration)}
            </div>
            <div style="background:#111118; border:1px solid #1e1e3a; border-radius:8px; padding:0.6rem 1.2rem;">
                📝 {st.session_state.word_count:,} words
            </div>
            <div style="background:#111118; border:1px solid #1e1e3a; border-radius:8px; padding:0.6rem 1.2rem;">
                ⚡ {st.session_state.summary_time}s
            </div>
        </div>
        """, unsafe_allow_html=True)

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
                    snippet = create_context(st.session_state.transcript_list, max_segments=110)

                    resp = ollama.chat(
                        model="phi3:mini",
                        messages=[{"role": "user", "content": CHAT_PROMPT.format(transcript=snippet, question=prompt)}],
                        options={
                            "temperature": 0.25,
                            "num_predict": 550,
                            "top_p": 0.85,
                            "num_ctx": 8192,
                        }
                    )
                    answer = resp["message"]["content"]
                    elapsed = round(time.time() - t0, 1)

                st.markdown(answer)
                st.caption(f"⚡ {elapsed}s")

            st.session_state.messages.append({"role": "assistant", "content": answer})

# ====================== TAB 2: HISTORY ======================
with tab2:
    st.subheader("📜 History")
    if not st.session_state.history:
        st.info("No videos yet. Go to New Video tab.")
    else:
        for i, item in enumerate(st.session_state.history):
            with st.expander(f"🎬 {item['title']}", expanded=False):
                st.caption(item['url'])
                if st.button("Load Video", key=f"load_{i}"):
                    st.session_state.summary = item["summary"]
                    st.session_state.transcript = item["transcript"]
                    st.session_state.transcript_list = item["transcript_list"]
                    st.session_state.messages = []
                    st.switch_tab(tab1)

# ====================== TAB 3: SETTINGS ======================
with tab3:
    st.subheader("⚙️ Settings")
    if st.button("🗑️ Clear History"):
        st.session_state.history = []
        st.success("History cleared!")
        time.sleep(0.8)
        st.rerun()
