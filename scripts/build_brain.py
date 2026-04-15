import os
from langchain_community.document_loaders import TextLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.vectorstores import Chroma

# PATHS
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(BASE_DIR, 'data', 'processed', 'knowledge_base.txt')
DB_PATH = os.path.join(BASE_DIR, 'data', 'chroma_db')

def build_vector_db():
    print("--- 🧠 STARTED: Building the Brain ---")

    # 1. Load the Data
    if not os.path.exists(DATA_PATH):
        print(f"❌ Error: File not found at {DATA_PATH}")
        return

    loader = TextLoader(DATA_PATH, encoding='utf-8')
    documents = loader.load()
    print(f"✔ Loaded knowledge base: {len(documents[0].page_content)} characters")

    # 2. Split into Chunks (Critical Step)
    # chunk_size=500: Enough for one therapeutic concept
    # chunk_overlap=50: Keeps context between cuts
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    chunks = text_splitter.split_documents(documents)
    print(f"✔ Split into {len(chunks)} knowledge chunks")

    # 3. Initialize Embedding Model (The Translator)
    # We use 'all-MiniLM-L6-v2'. It's small, fast, and great for English.
    # It runs locally on your CPU (no API key needed).
    print("⏳ Loading AI Model (this might take a minute)...")
    embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

    # 4. Create and Save the Database
    print("⏳ Creating Vector Database...")
    # This actually converts text -> numbers and saves to disk
    vector_db = Chroma.from_documents(
        documents=chunks,
        embedding=embedding_model,
        persist_directory=DB_PATH
    )
    
    # Force save to disk (older versions of Chroma need this, newer ones do it auto)
    # vector_db.persist() 
    
    print(f"✔ SUCCESS! Brain saved to: {DB_PATH}")
    print("--- 🧠 COMPLETED ---")

if __name__ == "__main__":
    build_vector_db()