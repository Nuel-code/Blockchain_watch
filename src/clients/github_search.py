from typing import Dict, List
from src.utils import request_json

GITHUB_API = "https://api.github.com/search/repositories"


def search_recent_crypto_repos() -> List[Dict]:
    """
    Finds recently created crypto/web3 repos.
    This is a strong early signal for real projects.
    """
    try:
        data = request_json(
            "GET",
            GITHUB_API,
            params={
                "q": "blockchain OR defi OR crypto OR web3 in:name,description",
                "sort": "updated",
                "order": "desc",
                "per_page": 20,
            },
        )
    except Exception:
        return []

    items = data.get("items", []) if isinstance(data, dict) else []

    results = []
    for repo in items:
        results.append(
            {
                "name": repo.get("name"),
                "full_name": repo.get("full_name"),
                "description": repo.get("description"),
                "url": repo.get("html_url"),
                "stars": repo.get("stargazers_count"),
                "created_at": repo.get("created_at"),
                "updated_at": repo.get("updated_at"),
                "source": "github",
            }
        )

    return results
