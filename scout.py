import os
import json
import feedparser
from groq import Groq
from google.cloud import storage
from datetime import datetime

# --- CONFIGURATION ---
# Refine these themes to tune your "Signal-to-Noise" filter
RESEARCH_THEMES = "AI Policy, US-China tech competition, Semi-conductor supply chains, AI Governance"
GROQ_MODEL = "llama-3.3-70b-versatile"

def get_all_entries():
    """Reads feeds.json and pulls the latest entries from each RSS feed."""
    with open('feeds.json') as f:
        config = json.load(f)
    
    all_entries = []
    for url in config['feeds']:
        try:
            feed = feedparser.parse(url)
            # Take the 5 most recent items from each source
            for entry in feed.entries[:5]: 
                all_entries.append({
                    "title": entry.title,
                    "link": entry.link,
                    "summary": entry.get('summary', '')[:500] # Snippet for context
                })
        except Exception as e:
            print(f"Error parsing {url}: {e}")
    return all_entries

def scout_relevance(entries):
    """Uses Groq's high-speed LPU to identify the top 5 strategic signals."""
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))
    
    # Build the manifest for the LLM
    manifest = "\n".join([f"- INDEX {i}: {e['title']}" for i, e in enumerate(entries)])
    
    prompt = f"""
    You are a Strategic Research Scout. Review these article titles and identify the TOP 5 
    most relevant to the following themes: {RESEARCH_THEMES}.
    
    Return ONLY a JSON object with the key "indices" containing a list of integers.
    Articles to review:
    {manifest}
    """
    
    completion = client.chat.completions.create(
        messages=[{"role": "user", "content": prompt}],
        model=GROQ_MODEL,
        response_format={"type": "json_object"}
    )
    
    selected_indices = json.loads(completion.choices[0].message.content)['indices']
    return [entries[i] for i in selected_indices]

def upload_briefing_to_vault(top_articles):
    """Formats the briefing and pushes it to the 'ai-daily' folder in GCS."""
    # Auth via Service Account JSON stored in GitHub Secrets
    storage_client = storage.Client.from_service_account_info(
        json.loads(os.environ.get("GCP_SA_KEY"))
    )
    bucket = storage_client.bucket(os.environ.get("GCS_BUCKET_NAME"))
    
    # Construct the Markdown content
    date_str = datetime.now().strftime("%Y-%m-%d")
    content = f"# 🌐 Strategic Intelligence Briefing: {date_str}\n\n"
    content += "The Scout has identified the following high-priority signals for your AI policy research:\n\n---\n\n"
    
    for article in top_articles:
        content += f"## {article['title']}\n"
        content += f"- **Link:** [{article['link']}]({article['link']})\n"
        content += f"- **Scout Context:** {article['summary']}...\n\n"
    
    # Define the destination path in your vault
    blob_name = f"ai-daily/Daily_Briefing_{date_str}.md"
    blob = bucket.blob(blob_name)
    
    # Upload as a Markdown file
    blob.upload_from_string(content, content_type='text/markdown')
    print(f"✅ Success: Briefing pushed to GCS vault at: {blob_name}")

if __name__ == "__main__":
    print("Starting Scouting Mission...")
    raw_data = get_all_entries()
    
    if not raw_data:
        print("No data found in feeds. Exiting.")
    else:
        print(f"Scanned {len(raw_data)} articles. Filtering for relevance...")
        top_signals = scout_relevance(raw_data)
        upload_briefing_to_vault(top_signals)