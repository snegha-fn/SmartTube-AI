# SmartTube AI

AI-powered YouTube summarizer and transcript-based chat assistant built using Streamlit and Ollama.

---

## Features

- Generates concise summaries from YouTube transcripts
- Interactive chat with video content
- Timestamp-aware responses
- Local LLM inference using Ollama
- CPU-optimized processing
- History tracking for summarized videos

---
## Tech Stack

- Python
- Streamlit
- Ollama
- Phi-3 Mini
- YouTube Transcript API

---
## Installation

### Clone the repository

git clone https://github.com/YOUR_USERNAME/SmartTube-AI.git
cd SmartTube-AI

### Install dependencies

pip install -r requirements.txt

### Install Ollama model

ollama pull phi3:mini

### Run the application

streamlit run app.py

## Project Structure

=======
```bash
git clone https://github.com/YOUR_USERNAME/SmartTube-AI.git
cd SmartTube-AI
```

### Install dependencies

```bash
pip install -r requirements.txt
```

### Install Ollama model

```bash
ollama pull phi3:mini
```

### Run the application

```bash
streamlit run app.py
```

---

## Project Structure

```plaintext
SmartTube-AI/
│
├── app.py
├── requirements.txt
├── README.md
├── .gitignore
├── LICENSE
└── assets/
=======
```

---
## Future Improvements

- Multi-language support
- Export summaries as PDF
- Support for multiple LLMs
- RAG-based retrieval
- Cloud deployment

## License

---

## License

This project is licensed under the MIT License.
