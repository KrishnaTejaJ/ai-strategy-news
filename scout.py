import os
import json
import re
import feedparser
from groq import Groq
from datetime import datetime

# --- CONFIGURATION ---
RESEARCH_THEMES = "AI Policy, US-China tech competition, Semi-conductor supply chains, AI Governance"
GROQ_MODEL = "llama-3.3-70b-versatile"
OUTPUT_DIR = "ai-daily"

def clean_html(raw_html):
    """Strip HTML tags and CMS boilerplate from RSS summaries."""
    clean = re.sub(r'<[^>]+>', '', raw_html)
    # Remove common CMS junk
    clean = re.sub(r'The post .* appeared first on .*\.?', '', clean)
    clean = re.sub(r'\s+', ' ', clean).strip()
    return clean

def get_all_entries():
    with open('feeds.json') as f:
        config = json.load(f)
    all_entries = []
    for url in config['feeds']:
        try:
            feed = feedparser.parse(url)
            source_name = feed.feed.get('title', url)
            for entry in feed.entries[:5]:
                raw_summary = entry.get('summary', '') or entry.get('description', '')
                all_entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "source": source_name,
                    "published": entry.get('published', ''),
                    "summary": clean_html(raw_summary)[:800]
                })
        except Exception as e:
            print(f"Error parsing {url}: {e}")
    return all_entries

def scout_relevance(entries):
    """Stage 1: Filter - pick the top 5 most relevant articles."""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    manifest = "\n".join([
        f"- INDEX {i}: [{e['source']}] {e['title']}" 
        for i, e in enumerate(entries)
    ])
    
    prompt = f"""You are a strategic research scout focused on: {RESEARCH_THEMES}.

Review these articles and select the TOP 5 most relevant. Prioritize:
1. Primary sources and original analysis over news aggregation
2. Policy developments and regulatory shifts
3. Technical capability assessments and supply chain updates
4. Strategic competition dynamics

Return ONLY a JSON object with key "indices" containing a list of 5 integers.

Articles:
{manifest}"""
    
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=GROQ_MODEL,
        response_format={"type": "json_object"}
    )
    selected_indices = json.loads(completion.choices[0].message.content)['indices']
    return [entries[i] for i in selected_indices]

def analyze_briefing(top_articles):
    """Stage 2: Analyze - generate a real briefing with context."""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    articles_text = ""
    for i, a in enumerate(top_articles):
        articles_text += f"""
ARTICLE {i+1}:
Title: {a['title']}
Source: {a['source']}
Summary: {a['summary']}
---"""
    
    prompt = f"""You are a senior strategic analyst writing a daily intelligence briefing 
for a researcher focused on: {RESEARCH_THEMES}.

For each article below, write:
1. A one-line "So What" — why this matters to the research themes above
2. A 2-3 sentence analysis explaining the significance, any second-order effects, 
   or connections to broader trends
3. One "Watch For" — what to monitor as a follow-up

Be direct and analytical. No filler. Write like a think tank analyst, not a journalist.

{articles_text}

Return your analysis as a JSON object with key "analyses" containing a list of objects, 
each with keys: "title", "so_what", "analysis", "watch_for"."""
    
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=GROQ_MODEL,
        response_format={"type": "json_object"},
        max_tokens=2000
    )
    return json.loads(completion.choices[0].message.content)['analyses']

def write_local_briefing(top_articles, analyses):
    if not os.path.exists(OUTPUT_DIR):
        os.makedirs(OUTPUT_DIR)
    
    date_str = datetime.now().strftime("%Y-%m-%d")
    filename = f"{OUTPUT_DIR}/Daily_Briefing_{date_str}.md"
    
    content = f"# Strategic Intelligence Briefing: {date_str}\n\n"
    content += f"**Themes:** {RESEARCH_THEMES}\n\n---\n\n"
    
    for i, (article, analysis) in enumerate(zip(top_articles, analyses)):
        content += f"## {i+1}. {article['title']}\n"
        content += f"**Source:** {article['source']}  \n"
        content += f"**Link:** [{article['title']}]({article['link']})  \n\n"
        content += f"**So What:** {analysis.get('so_what', 'N/A')}\n\n"
        content += f"{analysis.get('analysis', 'N/A')}\n\n"
        content += f"**Watch For:** {analysis.get('watch_for', 'N/A')}\n\n"
        content += "---\n\n"
    
    # Add a section for your own notes
    content += "## My Takes\n\n"
    content += "- \n\n"
    content += "## Connections\n\n"
    content += "- \n"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Briefing saved to {filename}")

if __name__ == "__main__":
    print("Starting scout...")
    raw_data = get_all_entries()
    if not raw_data:
        print("No data from feeds. Exiting.")
    else:
        print(f"Scanned {len(raw_data)} articles. Filtering...")
        top_signals = scout_relevance(raw_data)
        print(f"Selected {len(top_signals)} articles. Analyzing...")
        analyses = analyze_briefing(top_signals)
        write_local_briefing(top_signals, analyses)
        print("Done.")