from flask import Flask, render_template, request, redirect, send_file, jsonify
from reportlab.pdfgen import canvas
from dotenv import load_dotenv
load_dotenv()
import google.generativeai as genai
import sqlite3
import requests
import os
import urllib.parse

app = Flask(__name__)

# =====================
# GEMINI AI SETUP
# =====================
genai.configure(api_key=os.getenv("GEMINI_API_KEY"))
model = genai.GenerativeModel("gemini-2.5-flash-lite")

latest_recipe = ""
chat_history = []

# =====================
# PEXELS IMAGE
# =====================
PEXELS_API_KEY = os.getenv("PEXELS_API_KEY")

def get_recipe_image(query):
    try:
        headers = {"Authorization": PEXELS_API_KEY}

        search_query = urllib.parse.quote(f"{query} recipe")

        url = f"https://api.pexels.com/v1/search?query={search_query}&per_page=10"

        res = requests.get(url, headers=headers, timeout=10)

        if res.status_code != 200:
            return ""

        data = res.json()
        photos = data.get("photos", [])

        if photos:
            return photos[0]["src"]["large"]

    except Exception as e:
        print("Image Error:", e)

    return ""

# =====================
# DATABASE
# =====================
def init_db():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()

    cur.execute("""CREATE TABLE IF NOT EXISTS history(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        query TEXT,
        language TEXT,
        response TEXT
    )""")

    cur.execute("""CREATE TABLE IF NOT EXISTS favorites(
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        recipe TEXT,
        response TEXT,
        image_url TEXT
    )""")

    conn.commit()
    conn.close()

init_db()

# =====================
# HOME
# =====================
@app.route("/")
def home():
    return render_template("index.html")

# =====================
# SEARCH RECIPE
# =====================
@app.route("/search", methods=["POST"])
def search():
    global latest_recipe

    query = request.form["query"]
    language = request.form["language"]

    prompt = f"""
You are CookMate AI, a professional chef assistant.

Language: {language}

If input has commas treat as INGREDIENTS else RECIPE NAME.

Format:
🍳 Recipe Name
📖 Description
⏱️ Time
🥗 Nutrition
🛒 Ingredients
👨‍🍳 Steps
💡 Tip

Respond ONLY in {language}.
User: {query}
"""

    try:
        response = model.generate_content(prompt)
        result = response.text
        latest_recipe = result
    except Exception as e:
        result = str(e)

    recipe_name = query

    if "🍳" in result:
        try:
            recipe_name = result.split("🍳")[1].split("\n")[0].strip()
        except:
            pass

    image_url = get_recipe_image(recipe_name)

    video_url = "https://www.youtube.com/results?search_query=" + urllib.parse.quote(recipe_name + " recipe")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO history(query, language, response) VALUES (?, ?, ?)",
        (query, language, result)
    )
    conn.commit()
    conn.close()

    chat_history.clear()
    chat_history.append(f"Chef: I have prepared this recipe for you: {result}")

    return render_template(
        "result.html",
        result=result,
        query=query,
        image_url=image_url,
        video_url=video_url
    )

# =====================
# CHATBOT ROUTE
# =====================
@app.route("/chat", methods=["POST"])
def chat():
    global chat_history

    user_message = request.form.get("message")

    if not user_message:
        return jsonify({"reply": "Empty message"})

    chat_history.append(f"User: {user_message}")
    
    # ✅ EE RENDU LINES REPLACE CHEYYI
    system_prompt = """You are CookMate AI, a friendly chef assistant.
- You love cooking and food
- You can also have casual friendly conversations
- Keep answers SHORT and DIRECT (2-3 lines max)
- No long bullet points or explanations
- Be warm, fun and conversational
- For cooking questions, give practical tips
"""
    prompt = system_prompt + "\n" + "\n".join(chat_history) + "\nChef:"

    try:
        response = model.generate_content(prompt)
        reply = response.text
    except Exception as e:
        reply = "Error: " + str(e)

    chat_history.append(f"Chef: {reply}")
    return jsonify({"reply": reply})

# =====================
# HISTORY
# =====================
@app.route("/history")
def history():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT id, query, language FROM history ORDER BY id DESC")
    rows = cur.fetchall()
    conn.close()
    return render_template("history.html", rows=rows)

# =====================
# FAVORITES
# =====================
@app.route("/favorite", methods=["POST"])
def favorite():
    recipe = request.form["recipe"]
    response = request.form["response"]
    image_url = request.form.get("image_url", "")

    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute(
        "INSERT INTO favorites(recipe, response, image_url) VALUES (?, ?, ?)",
        (recipe, response, image_url)
    )
    conn.commit()
    conn.close()

    return redirect("/favorites")

@app.route("/favorites")
def favorites():
    conn = sqlite3.connect("database.db")
    cur = conn.cursor()
    cur.execute("SELECT * FROM favorites ORDER BY id DESC")
    data = cur.fetchall()
    conn.close()
    return render_template("favorites.html", data=data)

# =====================
# PDF DOWNLOAD
# =====================
@app.route("/download_pdf")
def download_pdf():
    global latest_recipe

    if not latest_recipe:
        return "No recipe found", 400

    pdf = canvas.Canvas("recipe.pdf")
    y = 800

    for line in latest_recipe.split("\n"):
        pdf.drawString(40, y, line[:100])
        y -= 20
        if y < 50:
            pdf.showPage()
            y = 800

    pdf.save()

    return send_file("recipe.pdf", as_attachment=True)

# =====================
# RUN
# =====================
if __name__ == "__main__":
    app.run(debug=True)