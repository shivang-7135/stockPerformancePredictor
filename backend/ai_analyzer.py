import os
import json
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")

# Set up the OpenAI client to point to OpenRouter
client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=OPENROUTER_API_KEY,
)

# You can change this to any preferred model available on OpenRouter
MODEL_ID = "google/gemini-3.8-flash"

def analyze_stock_sentiment(company_name: str, news_text: str):
    """
    Basic sentiment analysis (kept for the overview backtest).
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        return {
            "sentiment": "Neutral",
            "reasoning": "OpenRouter API key not configured.",
            "prediction": "Unknown"
        }

    prompt = f"""
    You are an expert financial analyst AI.
    Analyze the following recent news for the European stock/company: {company_name}.
    
    News Context:
    {news_text}
    
    Based on the news:
    1. What is the overall sentiment? (Bullish, Bearish, or Neutral)
    2. What specific news events are acting as triggers?
    3. Predict the stock's short-term price movement (Up, Down, Stable).
    
    Respond STRICTLY in the following JSON format:
    {{
        "sentiment": "Bullish|Bearish|Neutral",
        "reasoning": "A concise 2-3 sentence explanation of the specific news triggers.",
        "prediction": "Up|Down|Stable"
    }}
    """

    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": "You are a helpful financial AI assistant that responds in strict JSON format."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        result_content = response.choices[0].message.content
        result_json = json.loads(result_content)
        return result_json
        
    except Exception as e:
        print(f"Error calling OpenRouter for {company_name}: {e}")
        return {
            "sentiment": "Error",
            "reasoning": f"Failed to analyze. Error: {str(e)}",
            "prediction": "Unknown"
        }


def analyze_with_learning(company_name: str, date_str: str, news_text: str, mistake_log: list):
    """
    Self-correcting prediction. Takes a log of past mistakes and feeds them
    into the prompt so the model can recalibrate its reasoning for the next day.
    
    mistake_log is a list of dicts like:
    [
        {
            "date": "2026-08-15",
            "predicted": "Up",
            "actual": "Down",
            "news_summary": "...",
            "reasoning": "..."
        },
        ...
    ]
    """
    if not OPENROUTER_API_KEY or OPENROUTER_API_KEY == "your_openrouter_api_key_here":
        return {
            "sentiment": "Neutral",
            "reasoning": "OpenRouter API key not configured.",
            "prediction": "Unknown",
            "confidence": 50
        }

    # Build the self-correction context
    correction_block = ""
    if mistake_log:
        correction_block = "\n\n--- IMPORTANT: PAST PREDICTION MISTAKES (Learn from these!) ---\n"
        correction_block += "You previously made the following incorrect predictions. Study WHY you were wrong and adjust your reasoning accordingly.\n\n"
        for m in mistake_log[-5:]:  # Last 5 mistakes to keep prompt manageable
            correction_block += f"Date: {m['date']}\n"
            correction_block += f"  Your prediction: {m['predicted']} | Actual result: {m['actual']}\n"
            correction_block += f"  News you saw: {m['news_summary'][:200]}\n"
            correction_block += f"  Your reasoning was: {m['reasoning']}\n"
            correction_block += f"  LESSON: Your analysis was flawed. The market reacted differently than you expected.\n\n"
        correction_block += "--- END OF PAST MISTAKES. Use these lessons to improve your prediction below. ---\n"

    prompt = f"""
You are an expert European stock market financial analyst AI.
Today's date is: {date_str}
Company: {company_name}

Today's News:
{news_text}
{correction_block}

Based on today's news and any lessons from your past mistakes above:
1. What is the sentiment? (Bullish, Bearish, or Neutral)
2. What specific news events are acting as triggers for price movement?
3. Predict whether this stock will close HIGHER (Up) or LOWER (Down) than it opened today.
4. How confident are you in this prediction? (0-100)

Think carefully. If you've been wrong before on similar news patterns, adjust your approach.

Respond STRICTLY in the following JSON format:
{{
    "sentiment": "Bullish|Bearish|Neutral",
    "reasoning": "A concise 2-3 sentence explanation of the specific news triggers and why you believe the stock will move this way.",
    "prediction": "Up|Down",
    "confidence": 75,
    "lesson_applied": "What lesson from past mistakes (if any) influenced this prediction."
}}
"""

    try:
        response = client.chat.completions.create(
            model=MODEL_ID,
            messages=[
                {"role": "system", "content": "You are a self-improving financial analyst AI. You learn from past prediction mistakes to make better future predictions. Respond in strict JSON."},
                {"role": "user", "content": prompt}
            ],
            response_format={"type": "json_object"},
            max_tokens=1000
        )
        
        result_content = response.choices[0].message.content
        result_json = json.loads(result_content)
        return result_json
        
    except Exception as e:
        print(f"Error calling OpenRouter for {company_name} on {date_str}: {e}")
        return {
            "sentiment": "Error",
            "reasoning": f"Failed to analyze. Error: {str(e)}",
            "prediction": "Unknown",
            "confidence": 0,
            "lesson_applied": "N/A"
        }


if __name__ == "__main__":
    sample_news = "1. [Today] SAP announces record cloud revenue growth, beating all analyst expectations."
    print(json.dumps(analyze_stock_sentiment("SAP", sample_news), indent=2))
