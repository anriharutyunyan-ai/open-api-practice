from dotenv import load_dotenv
from openai import OpenAI

load_dotenv()

client = OpenAI()

user_prompt =input("Enter your promp")

response = client.responses.create(
    model="gpt-4.1-mini",
    input="Give me a list of the 5 fastest bikes in the world."
)

print(response.output_text)

from flask import Flask, render_template, request, session
from dotenv import load_dotenv
from openai import OpenAI
import os


load_dotenv()

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = Flask(__name__)
app.secret_key = "supersecretkey"  
@app.route("/", methods=["GET", "POST"])
def index():
    if "history" not in session:
        session["history"] = []

    output = ""
    if request.method == "POST":
        user_prompt = request.form["prompt"]
        category = request.form.get("category", "general")

        system_prompt = f"""
        You are a professional {category} mechanic.
        Provide clear, step-by-step advice.
        Include safety warnings and required tools.
        """

        response = client.responses.create( 
            model="gpt-4.1-mini",
            input=f"{system_prompt}\nUser: {user_prompt}"
        )
        output = response.output_text

       
        session["history"].append({"prompt": user_prompt, "response": output})
        session.modified = True

    return render_template("index.html", output=output, history=session.get("history"))

if __name__ == "__main__":
    app.run(debug=True)
