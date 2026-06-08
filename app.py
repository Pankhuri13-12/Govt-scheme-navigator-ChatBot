# app.py
import streamlit as st
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma
from langchain_groq import ChatGroq

st.set_page_config(page_title="Govt Scheme Navigator", page_icon="🏛️")
st.title("🏛️ Government Scheme Navigator")
st.caption("Ask me anything about Indian government schemes!")

# ── Load DB and LLM ──────────────────────────────────────────────────────────
@st.cache_resource
def load_resources():
    embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
    db = Chroma(persist_directory="./chroma_db",
                embedding_function=embeddings)
    llm = ChatGroq(
        api_key=st.secrets["GROQ_API_KEY"],
        model="llama-3.3-70b-versatile"
    )
    return db, llm

db, llm = load_resources()

# ── Chat History ─────────────────────────────────────────────────────────────
if "messages" not in st.session_state:
    st.session_state.messages = []

for msg in st.session_state.messages:
    st.chat_message(msg["role"]).write(msg["content"])

# ── Chat Input ───────────────────────────────────────────────────────────────
if question := st.chat_input("Ask about a government scheme..."):
    st.session_state.messages.append({"role": "user", "content": question})
    st.chat_message("user").write(question)

    # Retrieve relevant chunks from ChromaDB
    results = db.similarity_search(question, k=4)
    context = "\n\n".join([r.page_content for r in results])

    # Build prompt
    prompt = f"""You are a helpful assistant explaining Indian government schemes.
Answer ONLY using the context below.
If the answer is not in the context, say "I don't have information about that scheme."

CONTEXT:
{context}

QUESTION: {question}

ANSWER:"""

    # Get answer from LLM
    answer = llm.invoke(prompt).content

    st.session_state.messages.append({"role": "assistant", "content": answer})
    st.chat_message("assistant").write(answer)