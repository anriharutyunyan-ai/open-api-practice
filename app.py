from flask import Flask, request, jsonify, send_from_directory
from openai import OpenAI
from supabase import create_client
import os
from dotenv import load_dotenv  


load_dotenv()


SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

app = Flask(__name__, static_folder='public')
# app.secret_key = os.getenv("FLASK_SECRET_KEY", "super_secret_key_change_this")

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def embed_query(text: str) -> list[float]:
    """Generate embeddings for text"""
    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )
    return response.data[0].embedding

def semantic_search(user_message: str) -> list:
    """Semantic search in Supabase"""
    if not supabase:
        return []
    
    try:
        # Generate embedding for the query
        query_embedding = embed_query(user_message)
        
        # Call Supabase RPC function
        res = supabase.rpc(
            "match_conversations",
            {
                "query_embedding": query_embedding,
                "match_count": 5,
                "match_threshold": 0.7
            }
        ).execute()
        
        return res.data if res.data else []
    except Exception as e:
        print(f"Semantic search error: {e}")
        return []


@app.get("/")
def index():
    return send_from_directory("public", "index.html")


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    user_message = data.get("message", "")
    category = data.get("category", "general")
    
    # Validate input
    if not user_message:
        return jsonify({"error": "No message provided"}), 400
    
    # Conduct semantic search
    search_results = semantic_search(user_message)
    
    # Format context from search results
    context = ""
    if search_results:
        context_parts = []
        for i, row in enumerate(search_results):
            similarity = row.get('similarity', 0)
            prompt = row.get('prompt', '')
            response = row.get('response', '')
            context_parts.append(
                f"[Similar Case {i+1} | Similarity: {similarity:.1%}]\n"
                f"Problem: {prompt}\n"
                f"Solution: {response}"
            )
        context = "\n\n".join(context_parts)
    
    # Build system prompt
    system_prompt = f"""
    You are a professional {category} mechanic with 20 years of experience.
    Provide clear, step-by-step diagnostic and repair advice.
    Include safety warnings, required tools, and estimated difficulty level.
    Be practical and concise.
    
    Additional instructions:
    1. If similar cases are provided, reference them when relevant
    2. Always prioritize safety
    3. List required tools
    4. Estimate difficulty (Beginner/Intermediate/Expert)
    5. Mention if professional help is recommended
    """
    
    # Build RAG message with context
    rag_message = {
        "role": "system",
        "content": (
            "USE the retrieved context below to answer. IF it doesn't contain the answer, "
            "use your general knowledge as a professional mechanic.\n\n"
            f"Context from similar cases:\n{context if context else 'No similar cases found.'}"
        )
    }
    
    # Build full user message
    full_user_message = {
        "role": "user",
        "content": (
            f"I need help with a {category} problem:\n"
            f"{user_message}\n\n"
            "Please provide professional mechanic advice."
        )
    }

    # Create full message list in correct order
    full_message_list = [
        {"role": "system", "content": system_prompt},
        rag_message,
        full_user_message
    ]
    
    try:
        # Get AI response - CORRECTED: removed invalid "input" parameter
        response = client.chat.completions.create(
            model="gpt-3.5-turbo",  
            messages=full_message_list,
            max_tokens=500,
            temperature=0.7
        )
        
        ai_response = response.choices[0].message.content
        
        # Generate embedding for the query
        embedding = None
        try:
            embedding = embed_query(user_message)
        except Exception as e:
            print(f"Embedding error: {e}")
        
        # Save to Supabase
        if supabase and embedding:
            try:
                supabase.table('conversations').insert({
                    "prompt": user_message,
                    "response": ai_response,
                    "category": category,
                    "embedding": embedding
                }).execute()
            except Exception as e:
                print(f"Supabase save error: {e}")
        
        return jsonify({
            "text": ai_response,
            "similar_cases": search_results[:3]  # Send top 3 similar cases
        })
        
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/<path:path>')
def serve_static(path):
    return send_from_directory('public', path)

if __name__ == "__main__":
    app.run(debug=True)