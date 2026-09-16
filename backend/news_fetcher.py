import os
import requests
import json
from dotenv import load_dotenv

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

def get_recent_news(company_name: str) -> str:
    """
    Fetches the past 30 days of news for a given company using the Serper API.
    Returns a formatted string of the top news headlines and snippets.
    """
    if not SERPER_API_KEY or SERPER_API_KEY == "your_serper_api_key_here":
        return f"Error: Serper API key not configured. Could not fetch news for {company_name}."

    url = "https://google.serper.dev/news"
    
    # "qdr:m" limits the search to the past month (30 days)
    payload = json.dumps({
        "q": f"{company_name} stock OR company news",
        "tbs": "qdr:m",
        "num": 10  # fetch top 10 articles
    })
    
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        
        news_items = data.get("news", [])
        if not news_items:
            return f"No recent news found for {company_name}."
            
        formatted_news = []
        for i, item in enumerate(news_items, 1):
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            date = item.get("date", "Unknown date")
            formatted_news.append(f"{i}. [{date}] {title} - {snippet}")
            
        return "\n".join(formatted_news)
        
    except Exception as e:
        return f"Error fetching news for {company_name}: {str(e)}"

def get_recent_news_structured(company_name: str, num_articles: int = 10) -> list:
    """
    Fetches the past 30 days of news for a given company and returns a list of dictionaries:
    [{'title': ..., 'snippet': ..., 'date': ..., 'link': ..., 'source': ...}]
    """
    if not SERPER_API_KEY or SERPER_API_KEY == "your_serper_api_key_here":
        return []

    url = "https://google.serper.dev/news"
    payload = json.dumps({
        "q": f"{company_name} stock OR company news",
        "tbs": "qdr:m",
        "num": num_articles
    })
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        news_items = data.get("news", [])
        structured = []
        for item in news_items:
            structured.append({
                "title": item.get("title", ""),
                "snippet": item.get("snippet", ""),
                "date": item.get("date", "Recent"),
                "link": item.get("link", "#"),
                "source": item.get("source", "Financial News")
            })
        return structured
    except Exception as e:
        print(f"Error fetching structured news for {company_name}: {e}")
        return []

def get_news_for_date(company_name: str, target_date) -> str:
    """
    Fetches news for a specific historical date.
    """
    if not SERPER_API_KEY or SERPER_API_KEY == "your_serper_api_key_here":
        return f"Error: Serper API key not configured."

    url = "https://google.serper.dev/news"
    
    # Format date for Google tbs parameter (MM/DD/YYYY)
    date_str = target_date.strftime("%m/%d/%Y")
    
    payload = json.dumps({
        "q": f"{company_name} stock OR company news",
        "tbs": f"cdr:1,cd_min:{date_str},cd_max:{date_str}",
        "num": 5  # fetch top 5 articles per day
    })
    
    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=payload)
        response.raise_for_status()
        data = response.json()
        
        news_items = data.get("news", [])
        if not news_items:
            return f"No news found for {company_name} on {target_date.strftime('%Y-%m-%d')}."
            
        formatted_news = []
        for i, item in enumerate(news_items, 1):
            title = item.get("title", "")
            snippet = item.get("snippet", "")
            formatted_news.append(f"{i}. {title} - {snippet}")
            
        return "\n".join(formatted_news)
        
    except Exception as e:
        return f"Error fetching news for {company_name}: {str(e)}"

if __name__ == "__main__":
    # Test script
    print(get_recent_news("SAP"))
