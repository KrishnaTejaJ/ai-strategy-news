import os
import json
import feedparser
from groq import Groq
from datetime import datetime

# --- CONFIGURATION ---
RESEARCH_THEMES = "AI Policy, US-China tech competition, Semi-conductor supply chains, AI Governance"
GROQ_MODEL = "llama-3.3-70b-versatile"
OUTPUT_DIR = "ai-daily" # This folder must exist in your repo

def get_all_entries():
    with open('feeds.json') as f:
        config = json.load(f)
    all_entries = []
    for url in config['feeds']:
        try:
            feed = feedparser.parse(url)
            for entry in feed.entries[:5]: 
                all_entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get('summary', '')[:500]
                })
        except Exception as e:
            print(f"Error parsing {url}: {e}")
    return all_entries

def scout_relevance(entries):
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    manifest = "\n".join([f"- INDEX {i}: {e['title']}" for i, e in enumerate(entries)])
    prompt = f"Identify TOP 5 relevant to: {RESEARCH_THEMES}. Return ONLY JSON with key 'indices'.\n{manifest}"
    
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=GROQ_MODEL,
        response_format={"type": "json_object"}
    )
    selected_indices = json.loads(completion.choices[0].message.content)['indices']
    return [entries[i] for i in selected_indices]

def write_local_briefing(top_articles):
    # Ensure the directory exists
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
        
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{OUTPUT_DIR}/Daily_Briefing_{date_str}.md"
    
    content = f"# 🌐 Strategic Intelligence Briefing: {date_str}\n\n"
    for article in top_articles:
        content += f"## {article['title']}\n- [Link]({article['link']})\n- {article['summary']}...\n\n"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"✅ Briefing saved locally to {filename}")

if __name__ == "__main__":
    raw_data = get_all_entries()
    if raw_data:
        top_signals = scout_relevance(raw_data)
        write_local_briefing(top_signals)