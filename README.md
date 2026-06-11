# 📐 MathMate v2.1 

> **Your Socratic NCERT Class 10 Mathematics Tutor.**
> A multimodal, AI-powered tutor that guides students to the answer, rather than just giving it away.

![MathMate Banner](https://img.shields.io/badge/MathMate-v2.1-6ee7b7?style=for-the-badge&logo=streamlit)
![Python](https://img.shields.io/badge/Python-3.9+-blue?style=for-the-badge&logo=python)
![Groq](https://img.shields.io/badge/LLM-Llama_3.3_70b-f87171?style=for-the-badge&logo=meta)
![FAISS](https://img.shields.io/badge/Vector_DB-FAISS-818cf8?style=for-the-badge)

## 🌟 Overview

**MathMate** is an advanced Retrieval-Augmented Generation (RAG) application specifically tailored for CBSE Class 10 NCERT Mathematics. Built with **Streamlit**, **LangChain**, and **Groq (Llama-3.3-70b)**, MathMate acts as a personal tutor. 

It employs a strict **Socratic Method**—meaning it will carefully guide you through a problem step-by-step using hints, rather than directly revealing the final answer. It features a custom **Insist Gate** and **Answer Leak Detection** to ensure mathematical integrity and encourage genuine learning.

## ✨ Key Features

- **🎙️ Multimodal Inputs:** Ask questions via text, voice (transcribed via Whisper), upload photos of handwritten working, or upload entire PDF worksheets!
- **📖 NCERT Knowledge Base:** Upload your NCERT textbook PDF to build a local **FAISS** vector index. MathMate will use exact textbook theorems and formulas to guide you.
- **🛡️ The "Insist Gate":** MathMate refuses to give you the final answer immediately. It will provide up to 4 hints. You must genuinely attempt the problem and explicitly ask for the answer multiple times before the gate opens.
- **🧮 Full KaTeX Support:** Beautiful, natively rendered mathematical equations and formulas in the chat interface.
- **👁️ Vision Intelligence:** Upload a photo of your notebook. MathMate will read your handwritten steps, identify exactly where you went wrong, and guide you back on track.

## 🛠️ Tech Stack

- **Frontend:** Streamlit with custom dark-mode CSS
- **LLM:** `llama-3.3-70b-versatile` powered by **Groq** for blazing fast inference
- **Vector Store:** FAISS (Facebook AI Similarity Search)
- **Embeddings:** HuggingFace Sentence Transformers
- **PDF Extraction:** PyMuPDF (`fitz`) & `pypdf`
- **Framework:** LangChain

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.9+
- A [Groq API Key](https://console.groq.com/keys)

### 2. Installation

Clone the repository and install the dependencies:

```bash
# Clone the repository
git clone https://github.com/YOUR_USERNAME/mathebot-rag.git
cd mathebot-rag

# Create and activate a virtual environment
python -m venv .venv
# On Windows:
.venv\Scripts\activate
# On Mac/Linux:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configuration

Create a `.env` file in the root directory and add your Groq API key:

```env
GROQ_API_KEY=your_groq_api_key_here
```

### 4. Run the Application

You can start the app using the provided batch script or via Streamlit directly:

```bash
# Using Streamlit directly
streamlit run app.py

# OR using the batch file (Windows)
run.bat
```

### 5. Using the App
1. When the app opens, upload your Class 10 NCERT Mathematics PDF using the sidebar.
2. Click **Build Knowledge Base**.
3. Start asking questions using Text, Voice, Image, or Worksheet formats!

## 🧠 How the Socratic Engine Works

MathMate evaluates your input and categorizes it into different modes:
- **ORIENT:** Helps you figure out where to begin.
- **PROBE:** Evaluates your handwritten or typed steps.
- **UNSTICK:** Provides micro-hints if you are stuck.
- **VERIFY:** Asks you to verify an answer you claim is correct.
- **CELEBRATE:** Congratulates genuine understanding.

*Disclaimer: MathMate is designed as an educational aid and should be used alongside traditional learning methods.*
