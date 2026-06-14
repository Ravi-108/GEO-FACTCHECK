"""
Web Verifier Module
Uses Tavily API to search the web and find evidence for/against claims.
"""

from tavily import TavilyClient


def search_claim(claim: str, api_key: str) -> list[dict]:
    """
    Search the web for evidence related to a specific claim.
    
    Args:
        claim: The factual claim to verify.
        api_key: Tavily API key.
    
    Returns:
        A list of dicts with 'content' and 'url' keys from search results.
    """
    client = TavilyClient(api_key=api_key)
    
    try:
        results = client.search(
            query=f"verify fact: {claim}",
            search_depth="advanced",
            max_results=5,
        )
        
        evidence = []
        for r in results.get("results", []):
            evidence.append({
                "content": r.get("content", ""),
                "url": r.get("url", ""),
                "title": r.get("title", "")
            })
        
        return evidence
    
    except Exception as e:
        return [{"content": f"Search error: {str(e)}", "url": "", "title": "Error"}]
