"""
Claim Finder Module
Uses OpenRouter API (OpenAI-compatible) to extract verifiable factual claims from text.
Includes model fallback and retry logic for rate limits.
"""

from openai import OpenAI
import json
import re
import time

# Verified free models on OpenRouter — tried in order until one works
FALLBACK_MODELS = [
    "google/gemini-2.0-pro-exp-02-05:free",
    "google/gemma-2-9b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "meta-llama/llama-3.1-8b-instruct:free",
    "mistralai/mistral-7b-instruct:free",
    "qwen/qwen-2.5-72b-instruct:free",
    "nousresearch/hermes-3-llama-3.1-405b:free",
    "microsoft/phi-3-mini-128k-instruct:free",
    "openchat/openchat-7b:free",
    "cognitivecomputations/dolphin-mixtral-8x7b:free"
]

MAX_RETRIES = 2  # Per model


def extract_claims(text: str, api_key: str) -> list[dict]:
    """
    Use an LLM via OpenRouter to identify verifiable factual claims from the given text.
    Tries multiple free models as fallback if one fails.
    
    Args:
        text: The extracted text from a PDF document.
        api_key: OpenRouter API key.
    
    Returns:
        A list of dicts, each with 'claim' and 'type' keys.
    """
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        timeout=15.0,
    )
    
    # Truncate to avoid token limits while keeping enough context
    truncated_text = text[:8000]
    
    prompt = f"""You are a precise fact-extraction engine. Analyze the text below and extract every verifiable factual claim.

Focus on these types of claims:
- **Statistics & percentages** (e.g., "revenue grew by 40%")
- **Dates & timelines** (e.g., "founded in 2015")
- **Financial figures** (e.g., "$2.5 billion valuation")
- **Technical specifications** (e.g., "processes 10,000 requests per second")
- **Named entity facts** (e.g., "headquartered in San Francisco")
- **Comparative claims** (e.g., "fastest growing in the category")

Rules:
1. Extract ONLY factual, verifiable claims — not opinions or subjective statements.
2. Each claim should be self-contained and understandable without the surrounding text.
3. Be thorough — extract ALL verifiable claims you can find.
4. Return ONLY a valid JSON array with no additional text, markdown, or explanation.

Return format:
[
  {{"claim": "exact factual claim text", "type": "statistic|date|financial|technical|entity|comparative"}},
  ...
]

TEXT TO ANALYZE:
{truncated_text}"""

    last_error = None
    for model_name in FALLBACK_MODELS:
        for attempt in range(MAX_RETRIES):
            try:
                print(f"Trying model: {model_name} (Attempt {attempt+1})")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.1,
                )
                
                raw = response.choices[0].message.content
                
                # Try to extract JSON from the response (handle markdown code blocks)
                json_match = re.search(r'\[.*\]', raw, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                
                return json.loads(raw)
            
            except Exception as e:
                last_error = e
                error_str = str(e)
                # If rate limited (429), wait and retry same model
                if "429" in error_str:
                    time.sleep(5 * (attempt + 1))
                    continue
                # If model not found (404), skip to next model immediately
                elif "404" in error_str:
                    break
                else:
                    break  # Other error, try next model
    
    # All models failed
    raise Exception(f"All models failed. Last error: {last_error}")
