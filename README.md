# InsightAgent 🤖
Hey there! Ever stared at a giant CSV file and wished it would just tell you what's important? Me too.

That's why I built InsightAgent.

This isn't just another dashboard tool. It's a proactive AI Data Consultant. You upload your data (up to 4,000 rows), tell the agent who you are (like a "CEO" or "Sales Manager"), and it does all the work.

It analyzes your data's "fingerprint" and writes a full report with insights, recommendations, and data quality warnings.

[!IMPORTANT] A Quick Heads-Up! 🚀

This agent uses the powerful Google Gemini API to do its thinking. When you click "Analyze," the AI is reading and interpreting your data summary to build a custom report just for you.

Please give it about 30-60 seconds to work its magic. It's not frozen, it's just thinking really hard! 🧠

✨ Features
Proactive Analysis: It tells you the insights. No more searching for needles in a haystack.

Deep Personalization: The entire analysis changes based on the "Role" (e.g., CEO, Marketing) and "Tone" (e.g., Formal, Casual) you select.

The "Living" Agent: The AI has a voice! It speaks its Executive Summary out loud using Text-to-Speech (TTS).

Data Quality First: Before anything else, the agent tells you about problems in your data (missing values, duplicates, etc.).

AI-Generated Charts: The agent doesn't just give text; it writes the code for 5-6 Plotly charts (histograms, bar charts, and even a regression plot) to visualize its findings.

Interactive "Deep-Dive": The AI suggests a filter (e.g., "Analyze the 'North' region"), and you can click a button to re-run the entire analysis on just that segment.

Downloadable PDF: Get a clean, text-based PDF of the full report with one click.

💡 How the Magic Works
This is the cool part. We don't send your 2,000-row file to the AI (that would be slow and expensive!).

Pandas "Smart Summary": The app first creates a "fingerprint" of your data using Pandas (.describe(), .info(), .corr(), etc.).

Gemini "Master Prompt": It sends this tiny (but dense) "Smart Summary" to the Gemini API, along with your Role and Tone.

JSON & Charts: The AI is forced to return a perfectly structured JSON object. The app parses this JSON to build the entire dashboard, including executing the Plotly code strings that the AI generated.

🛠️ Tech Stack
UI (Frontend): Streamlit

Data (Analysis): Pandas

The "Brain": Google Gemini API (google-generativeai)

Charts: Plotly Express

The "Voice": gTTS (Google Text-to-Speech)

The "Report": FPDF (fpdf2)

Regression Model: Plotly trendline='ols' (which uses statsmodels behind the scenes)

🚀 How to Run It
Clone this repo:

Bash

git clone [your-repo-link]
cd InsightAgent
Create a virtual environment:

Bash

python -m venv venv
.\venv\Scripts\activate  # Windows
# source venv/bin/activate  # Mac/Linux
Install the goodies:

Bash

pip install -r requirements.txt
Add your API Key:

Create a folder named .streamlit

Inside it, create a file named secrets.toml

Add your Google Gemini key to that file:

Ini, TOML

GOOGLE_API_KEY = "AlzaSy...[your_key_here]"
Run the app!

Bash

streamlit run app.py
Built with ❤️ and a lot of prompts.
