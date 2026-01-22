from flask import Flask, request, jsonify, render_template
from openai import OpenAI
from supabase import create_client
import os
from dotenv import load_dotenv

# 1. Load environment variables from .env file
load_dotenv()

# 2. Initialize Flask with explicit folder paths
# This ensures Flask knows exactly where to look for HTML and CSS/JS
app = Flask(__name__, template_folder='templates', static_folder='static')

# 3. Configuration & Client Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
OPENAI_API_KEY = os.environ.get("OPENAI_API_KEY")

# Initialize Supabase (Database)
try:
    if SUPABASE_URL and SUPABASE_KEY:
        supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
        print("✅ Supabase connected.")
    else:
        supabase = None
        print("⚠️ Supabase credentials missing. 'Similar Cases' feature disabled.")
except Exception as e:
    print(f"❌ Supabase Init Error: {e}")
    supabase = None

# Initialize OpenAI (AI Model)
try:
    if OPENAI_API_KEY:
        client = OpenAI(api_key=OPENAI_API_KEY)
        print("✅ OpenAI connected.")
    else:
        client = None
        print("⚠️ OpenAI API Key missing.")
except Exception as e:
    print(f"❌ OpenAI Init Error: {e}")
    client = None


# --- Helper Functions ---

def embed_query(text: str) -> list[float]:
    """Generate embeddings for text using OpenAI"""
    if not client: return []
    try:
        response = client.embeddings.create(
            model="text-embedding-3-small",
            input=text
        )
        return response.data[0].embedding
    except Exception as e:
        print(f"Embedding Error: {e}")
        return []

def semantic_search(user_message: str) -> list:
    """Search for similar past cases in Supabase"""
    if not supabase: return []
    
    try:
        query_embedding = embed_query(user_message)
        if not query_embedding: return []

        # Calls the Postgres RPC function 'match_conversations'
        res = supabase.rpc(
            "match_conversations",
            {
                "query_embedding": query_embedding,
                "match_count": 3,
                "match_threshold": 0.5
            }
        ).execute()
        
        return res.data if res.data else []
    except Exception as e:
        print(f"Search Error (Check if 'match_conversations' RPC exists in Supabase): {e}")
        return []


# --- Routes ---

@app.route("/")
def index():
    """Serves the main HTML page"""
    return render_template("index.html")

@app.route("/api/chat", methods=["POST"])
def chat():
    """Handles the chat logic"""
    if not client:
        return jsonify({"error": "OpenAI API Key is missing on the server."}), 500

    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "")
    category = data.get("category", "general")
    
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    # 1. Search for similar past cases (RAG)
    search_results = semantic_search(user_message)
    
    # 2. Format Context for the AI
    context_text = ""
    if search_results:
        context_parts = []
        for i, row in enumerate(search_results):
            prompt = row.get('prompt', 'N/A')
            response_text = row.get('response', 'N/A')
            context_parts.append(f"--- SIMILAR CASE {i+1} ---\nProblem: {prompt}\nSolution: {response_text}")
        context_text = "\n\n".join(context_parts)
    
    # 3. Construct the System Prompt
    system_prompt = f"""
    You are an expert mechanic specializing in {category}. 
    Format your response with standard Markdown: use **Bold** for headers/warnings and bullet points for steps.
    
    Structure your advice as follows:
    1. **Diagnosis**: What is likely wrong.
    2. **Safety Warning**: Crucial safety steps (battery disconnect, jack stands, etc).
    3. **Tools Required**: Bulleted list.
    4. **Step-by-Step Fix**: Clear instructions.
    5. **Recommendation**: When to see a professional.

    Use the provided CONTEXT (similar past cases) if relevant to refine your answer.
    """
    
    rag_instruction = f"CONTEXT FROM DATABASE:\n{context_text}" if context_text else "No similar past cases found."
    
    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "system", "content": rag_instruction},
        {"role": "user", "content": user_message}
    ]
    
    try:
        # 4. Generate AI Response
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",
            messages=messages,
            temperature=0.7,
            max_tokens=800
        )
        
        ai_response = response.choices[0].message.content
        
        # 5. Save conversation to Supabase (if connected)
        if supabase:
            try:
                new_embedding = embed_query(user_message)
                if new_embedding:
                    supabase.table('conversations').insert({
                        "prompt": user_message,
                        "response": ai_response,
                        "category": category,
                        "embedding": new_embedding
                    }).execute()
            except Exception as e:
                print(f"Failed to save conversation: {e}")
        
        return jsonify({
            "text": ai_response,
            "similar_cases": search_results
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == "__main__":
    app.run(debug=True, port=5000)