"""
Claim Finder Module
Uses OpenRouter API (OpenAI-compatible) to extract verifiable factual claims from text.
Includes model fallback and retry logic for rate limits.
"""

from openai import OpenAI
import json
import re
import time

# Currently available free models on OpenRouter (June 2026) — tried in order
FALLBACK_MODELS = [
    "google/gemma-4-31b-it:free",
    "google/gemma-4-26b-a4b-it:free",
    "meta-llama/llama-3.3-70b-instruct:free",
    "qwen/qwen3-coder:free",
]

MAX_RETRIES = 3  # Per model


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
        timeout=60.0,
        default_headers={
            "HTTP-Referer": "https://github.com/Ravi-108/GEO-FACTCHECK",
            "X-Title": "GEO Fact-Check Agent",
        }
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

    first_error = None
    for model_name in FALLBACK_MODELS:
        for attempt in range(MAX_RETRIES):
            try:
                print(f"[ClaimFinder] Trying model: {model_name} (Attempt {attempt+1})")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=2000,
                    temperature=0.1,
                )
                
                if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
                    print(f"[ClaimFinder] Empty response from {model_name}, trying next...")
                    break  # Try next model
                
                raw = response.choices[0].message.content
                print(f"[ClaimFinder] Got response from {model_name}, length={len(raw)}")
                
                # Try to extract JSON from the response (handle markdown code blocks)
                json_match = re.search(r'\[.*\]', raw, re.DOTALL)
                if json_match:
                    return json.loads(json_match.group())
                
                return json.loads(raw)
            
            except Exception as e:
                error_str = str(e)
                print(f"[ClaimFinder] Error with {model_name} (attempt {attempt+1}): {error_str[:200]}")
                
                if first_error is None:
                    first_error = e
                
                # Check for hard account limits (do not retry or fallback)
                if "free-models-per-day" in error_str or "credits" in error_str.lower():
                    raise Exception(f"Account limit reached: {error_str}")
                
                # If rate limited (429), wait and retry same model
                if "429" in error_str:
                    time.sleep(5 * (attempt + 1))
                    continue
                # If model not found (404), skip to next model immediately
                elif "404" in error_str or "endpoints" in error_str.lower():
                    print(f"[ClaimFinder] Model {model_name} not found, trying next...")
                    break
                else:
                    print(f"[ClaimFinder] Unexpected error, trying next model...")
                    break  # Other error, try next model
    
    # All models failed
    raise Exception(f"All models failed. Primary error: {first_error}")
