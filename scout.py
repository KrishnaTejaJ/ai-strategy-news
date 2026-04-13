import os
import json
import feedparser
from groq import Groq
from google.cloud import storage

# 1. Configuration - Set your strategic filters here
RESEARCH_THEMES = "AI Policy, US-China tech competition, Semi-conductor supply chains, AI Governance"
GROQ_CLIENT = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def get_all_entries():
    with open('feeds.json') as f:
        config = json.load(f)
    
    all_entries = []
    for url in config['feeds']:
        feed = feedparser.parse(url)
        # Grab top 5 most recent from each source
        for entry in feed.entries[:5]: 
            all_entries.append({
                "title": entry.title,
                "link": entry.link,
                "summary": entry.get('summary', '')[:500] 
            })
    return all_entries

def scout_relevance(entries):
    manifest = "\n".join([f"- INDEX {i}: {e['title']}" for i, e in enumerate(entries)])
    
    prompt = f"""
    You are a Strategic Research Scout. Review these article titles. 
    Identify the TOP 5 most relevant to: {RESEARCH_THEMES}.
    Return ONLY a JSON object with the key "indices" and a list of integers.
    Articles:
    {manifest}
    """
    
    completion = GROQ_CLIENT.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model="llama-3.3-70b-versatile", # High-speed Groq model
        response_format={"type": "json_object"}
    )
    
    selected_indices = json.loads(completion.choices[0].message.content)['indices']
    return [entries[i] for i in selected_indices]

if __name__ == "__main__":
    raw_entries = get_all_entries()
    top_5 = scout_relevance(raw_entries)
    
    # Save the 'Signal' for Stage 2 or push directly to GCS
    print(f"Scout complete. Identified {len(top_5)} high-value targets.")
    with open('top_5_articles.json', 'w') as f:
        json.dump(top_5, f)