"""
Verdict Engine Module
Uses OpenRouter API (OpenAI-compatible) to compare claims against web evidence and produce verdicts.
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

    for model_name in FALLBACK_MODELS:
        for attempt in range(MAX_RETRIES):
            try:
                print(f"Verdict Engine: Trying model {model_name} (Attempt {attempt+1})")
                response = client.chat.completions.create(
                    model=model_name,
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=500,
                    temperature=0.1,
                )
                
                raw = response.choices[0].message.content
                
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
                
                # Check for hard account limits (do not retry or fallback)
                if "free-models-per-day" in error_str or "credits" in error_str.lower():
                    import re
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
                elif "404" in error_str:
                    break
                else:
                    break  # Other error, try next model
    
    # All models failed
    error_msg = str(e)
    import re
    match = re.search(r"'message':\s*'([^']+)'", error_msg)
    clean_msg = match.group(1) if match else error_msg
    
    return {
        "verdict": "ERROR",
        "confidence": "LOW",
        "explanation": f"API Error: {clean_msg}",
        "correct_fact": None,
        "sources": sources[:3]
    }
