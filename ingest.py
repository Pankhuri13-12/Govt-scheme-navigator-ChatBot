# ingest.py
import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# ── STEP 1: Read all .txt files ───────────────────────────────────────────────
print("=" * 50)
print("  STEP 1 — Loading scheme files from /data/")
print("=" * 50)

docs     = []
data_dir = "data"

for fname in os.listdir(data_dir):
    if fname.endswith(".txt"):
        fpath = os.path.join(data_dir, fname)
        with open(fpath, encoding="utf-8") as f:
            content = f.read().strip()
        if len(content) > 100:
            docs.append(content)

print(f"  Loaded {len(docs)} files")

# ── STEP 2: Split into chunks ─────────────────────────────────────────────────
print("\n" + "=" * 50)
print("  STEP 2 — Splitting into chunks")
print("=" * 50)

splitter = RecursiveCharacterTextSplitter(
    chunk_size=800,
    chunk_overlap=100,
)

chunks = []
for doc in docs:
    chunks.extend(splitter.split_text(doc))

print(f"  Total chunks created: {len(chunks)}")
print(f"  Sample chunk:\n{chunks[0][:300]}\n...")

# ── STEP 3: Embed + Store in ChromaDB ────────────────────────────────────────
print("\n" + "=" * 50)
print("  STEP 3 — Embedding + saving to ChromaDB")
print("  First run downloads model ~90MB, please wait...")
print("=" * 50)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

db = Chroma.from_texts(
    texts=chunks,
    embedding=embeddings,
    persist_directory="./chroma_db"
)
db.persist()

print(f"\n  ChromaDB saved to ./chroma_db/")
print(f"  Total vectors stored: {len(chunks)}")
print(f"  Next step → python app.py")