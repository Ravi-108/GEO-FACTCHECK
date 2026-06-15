"""
Verdict Engine Module
Uses OpenRouter API (OpenAI-compatible) to compare claims against web evidence and produce verdicts.
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


def get_verdict(claim: str, evidence: list[dict], client: OpenAI) -> dict:
    """
    Use an LLM via OpenRouter to compare a claim against web evidence and produce a verdict.
    Tries multiple free models as fallback if one fails.
    
    Args:
        claim: The factual claim to judge.
        evidence: List of dicts with 'content' and 'url' keys from web search.
        client: An initialized OpenAI client configured for OpenRouter.
    
    Returns:
        A dict with 'verdict', 'confidence', 'explanation', 'correct_fact', and 'sources' keys.
    """
    # Format evidence with sources
    evidence_text = ""
    sources = []
    for i, e in enumerate(evidence[:4], 1):
        evidence_text += f"\n[Source {i}]: {e.get('title', 'Unknown')}\n{e.get('content', '')}\nURL: {e.get('url', '')}\n"
        if e.get('url'):
            sources.append(e['url'])
    
    prompt = f"""You are an expert fact-checker. Your job is to compare a claim against web evidence and determine its accuracy.

CLAIM: "{claim}"

WEB EVIDENCE:
{evidence_text}

Evaluate the claim and classify it as:
- **VERIFIED**: The claim is accurate and matches the web evidence.
- **INACCURATE**: The claim contains outdated information, wrong numbers, or partial errors. The core idea may be right but specific details are wrong.
- **FALSE**: No evidence supports the claim, or evidence directly contradicts it.

Also assess your confidence:
- **HIGH**: Multiple sources confirm your verdict.
- **MEDIUM**: Some evidence supports your verdict but it's not conclusive.
- **LOW**: Limited evidence available.

Return ONLY valid JSON with no markdown formatting, no code blocks, no additional text:
{{"verdict": "VERIFIED|INACCURATE|FALSE", "confidence": "HIGH|MEDIUM|LOW", "explanation": "One clear sentence explaining why", "correct_fact": "The accurate information if the claim is wrong, or null if verified"}}"""

    first_error = None
    for model_name in FALLBACK_MODELS:
        for attempt in range(MAX_RETRIES):
            try:
                print(f"[VerdictEngine] Trying model {model_name} (Attempt {attempt+1})")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.1,
                )
                
                if not response.choices or not response.choices[0].message or not response.choices[0].message.content:
                    print(f"[VerdictEngine] Empty response from {model_name}, trying next...")
                    break  # Try next model
                
                raw = response.choices[0].message.content
                print(f"[VerdictEngine] Got response from {model_name}, length={len(raw)}")
                
                # Try to extract JSON from the response
                json_match = re.search(r'\{.*\}', raw, re.DOTALL)
                if json_match:
                    result = json.loads(json_match.group())
                else:
                    result = json.loads(raw)
                
                result['sources'] = sources[:3]
                return result
            
            except Exception as e:
                error_str = str(e)
                print(f"[VerdictEngine] Error with {model_name} (attempt {attempt+1}): {error_str[:200]}")
                
                if first_error is None:
                    first_error = e
                
                # Check for hard account limits (do not retry or fallback)
                if "free-models-per-day" in error_str or "credits" in error_str.lower():
                    match = re.search(r"'message':\s*'([^']+)'", error_str)
                    clean_msg = match.group(1) if match else error_str
                    return {
                        "verdict": "ERROR",
                        "confidence": "LOW",
                        "explanation": f"API Error: {clean_msg}",
                        "correct_fact": None,
                        "sources": sources[:3]
                    }
                
                # If rate limited (429), wait and retry same model
                if "429" in error_str:
                    time.sleep(5 * (attempt + 1))
                    continue
                # If model not found (404), skip to next model immediately
                elif "404" in error_str or "endpoints" in error_str.lower():
                    print(f"[VerdictEngine] Model {model_name} not found, trying next...")
                    break
                else:
                    print(f"[VerdictEngine] Unexpected error, trying next model...")
                    break  # Other error, try next model
    
    # All models failed
    error_msg = str(first_error)
    match = re.search(r"'message':\s*'([^']+)'", error_msg)
    clean_msg = match.group(1) if match else error_msg
    
    return {
        "verdict": "ERROR",
        "confidence": "LOW",
        "explanation": f"API Error: {clean_msg}",
        "correct_fact": None,
        "sources": sources[:3]
    }
