from flask import Flask, request, jsonify
from flask_cors import CORS
import os
import pandas as pd
import json
import glob
import re
from datetime import datetime

from langchain_community.vectorstores import Chroma
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.llms import Ollama
from langchain_classic.chains import create_retrieval_chain
from langchain_classic.chains.combine_documents import create_stuff_documents_chain
from langchain_core.prompts import ChatPromptTemplate

app = Flask(__name__)
CORS(app)

# --- 1. CONFIGURATION & PATHS ---
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, 'data', 'chroma_db')
HISTORY_DIR = os.path.join(BASE_DIR, 'data', 'chat_history')
os.makedirs(HISTORY_DIR, exist_ok=True)

# --- 2. LOAD AI ENGINE (Runs once when server starts) ---
print("⏳ Loading AI Components... Please wait.")
embedding_model = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
vector_db = Chroma(persist_directory=DB_PATH, embedding_function=embedding_model)
raw_llm = Ollama(model="llama3") 

chat_prompt = ChatPromptTemplate.from_template("""
You are a compassionate, clinical mental health assistant.
Use the following context to answer the user's question.
RULES:
1. VALIDATE the user's emotion first.
2. Use Behavioural Activation techniques.
3. If user mentions SELF-HARM, ignore context and provide crisis disclaimer.
4. Keep answers concise.

Context: {context}
Recent History: {chat_history}
User: {input}
Assistant:
""")

document_chain = create_stuff_documents_chain(raw_llm, chat_prompt)
qa_chain = create_retrieval_chain(vector_db.as_retriever(search_kwargs={"k": 2}), document_chain)
print("✅ AI Engine Loaded Successfully!")

# --- 3. HELPER FUNCTIONS ---
def get_chat_history(session_id):
    file_path = os.path.join(HISTORY_DIR, f"{session_id}.json")
    if os.path.exists(file_path):
        with open(file_path, 'r') as f:
            return json.load(f)
    return []

def save_chat_history(session_id, messages):
    file_path = os.path.join(HISTORY_DIR, f"{session_id}.json")
    with open(file_path, 'w') as f:
        json.dump(messages, f)

def auto_rename_session(session_id, first_user_message):
    try:
        prompt = f"Create a maximum 3-word title for a therapy chat that starts with: '{first_user_message}'. Output ONLY the title, no quotes, no extra words."
        raw_title = raw_llm.invoke(prompt).strip()
        safe_title = re.sub(r'[^a-zA-Z0-9]', '_', raw_title).strip('_')[:25]
        new_session_id = f"{safe_title}_{datetime.now().strftime('%H%M')}"
        
        old_file = os.path.join(HISTORY_DIR, f"{session_id}.json")
        new_file = os.path.join(HISTORY_DIR, f"{new_session_id}.json")
        
        if os.path.exists(old_file):
            os.rename(old_file, new_file)
        return new_session_id
    except Exception as e:
        print(f"Auto-titling failed: {e}")
        return session_id

# --- 4. API ENDPOINTS ---
@app.route('/api/chat', methods=['POST'])
def chat():
    data = request.json
    user_message = data.get('message', '')
    session_id = data.get('session_id', '')

    if not user_message:
        return jsonify({'error': 'No message provided'}), 400

    # If no session ID is provided, create a new one
    if not session_id:
        session_id = datetime.now().strftime("Session_%Y-%m-%d_%H-%M-%S")

    # 1. Load History & Append User Message
    messages = get_chat_history(session_id)
    messages.append({"role": "user", "content": user_message})

    # 2. Format the last 5 messages for the LLM
    history_str = "".join([f"{msg['role'].upper()}: {msg['content']}\n" for msg in messages[-5:]])

    try:
        # 3. Generate AI Response
        response = qa_chain.invoke({"input": user_message, "chat_history": history_str})
        ai_text = response["answer"]
        
        # 4. Append AI Response & Save
        messages.append({"role": "assistant", "content": ai_text})
        save_chat_history(session_id, messages)

        # 5. Trigger Auto-Titling if this is the first exchange
        if len(messages) == 2 and session_id.startswith("Session_"):
            session_id = auto_rename_session(session_id, user_message)

        return jsonify({
            'response': ai_text,
            'session_id': session_id # Send back the session ID so the frontend remembers it
        })
    
    except Exception as e:
        print(f"Error during AI generation: {e}")
        return jsonify({'error': 'Failed to generate response.'}), 500
    


# --- ADD THIS CONFIG ---
MOOD_FILE = os.path.join(BASE_DIR, 'data', 'mood_log.csv')

# --- NEW API ENDPOINTS ---

@app.route('/api/sessions', methods=['GET'])
def get_sessions():
    """Returns a list of all saved chat history files."""
    files = glob.glob(os.path.join(HISTORY_DIR, "*.json"))
    files.sort(key=os.path.getmtime, reverse=True) # Sort newest to oldest
    
    sessions = []
    for f in files:
        file_id = os.path.basename(f).replace(".json", "")
        # Clean up the name for display (e.g., "Exam_Anxiety_1245" -> "Exam Anxiety")
        display_name = re.sub(r'_\d{4}$', '', file_id).replace("_", " ") 
        sessions.append({"id": file_id, "name": display_name})
        
    return jsonify(sessions)

@app.route('/api/session/<session_id>', methods=['GET'])
def load_session(session_id):
    """Returns the chat history for a specific session."""
    messages = get_chat_history(session_id)
    return jsonify({"session_id": session_id, "messages": messages})

@app.route('/api/mood', methods=['GET', 'POST'])
def handle_mood():
    """Saves a new mood score, or returns all past scores for the chart."""
    if request.method == 'POST':
        data = request.json
        score = data.get('score')
        if score:
            # Save to CSV
            new_data = pd.DataFrame({"Date": [datetime.now().strftime("%Y-%m-%d %H:%M:%S")], "Mood_Score": [score]})
            new_data.to_csv(MOOD_FILE, mode='a', header=not os.path.exists(MOOD_FILE), index=False)
            return jsonify({"success": True})
        return jsonify({"error": "No score provided"}), 400
    
    # GET Request: Return data for the chart
    if os.path.exists(MOOD_FILE):
        df = pd.read_csv(MOOD_FILE)
        return jsonify({"dates": df['Date'].tolist(), "scores": df['Mood_Score'].tolist()})
    
    return jsonify({"dates": [], "scores": []})

# --- ADD THIS TO YOUR CONFIGURATION AT THE TOP ---
SUMMARY_FILE = os.path.join(BASE_DIR, 'data', 'session_summaries.txt')

# --- ADD THIS TO YOUR API ENDPOINTS ---
@app.route('/api/summarize', methods=['POST'])
def summarize_session():
    data = request.json
    session_id = data.get('session_id')
    
    if not session_id:
        return jsonify({"error": "No active session."}), 400

    # 1. Get the current chat history
    messages = get_chat_history(session_id)
    if not messages:
        return jsonify({"error": "Session is empty."}), 400

    # 2. Format the text for Llama-3
    conversation_text = "".join([f"{msg['role'].upper()}: {msg['content']}\n" for msg in messages])
    
    try:
        # 3. Ask Llama-3 to summarize
        prompt = f"Summarize this therapy session in 3 bullet points:\n{conversation_text}"
        summary = raw_llm.invoke(prompt).strip()
        
        # 4. Save to your text file log
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = f"\n\n[Session: {timestamp} | ID: {session_id}]\n{summary}\n-------------------"
        with open(SUMMARY_FILE, 'a', encoding='utf-8') as f:
            f.write(entry)
            
        # 5. Send it back to the frontend
        return jsonify({"summary": summary})
        
    except Exception as e:
        print(f"Error summarizing: {e}")
        return jsonify({"error": "Failed to generate summary."}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)