from typing import Any, Dict, List, Optional

from src.config import CHAIN_TO_ETHERSCAN_ID, ETHERSCAN_API_KEY
from src.utils import request_json


ETHERSCAN_V2_URL = "https://api.etherscan.io/v2/api"


def _empty_result() -> Dict[str, Any]:
    return {
        "status": "0",
        "message": "NO_API_KEY_OR_ERROR",
        "result": [],
    }


def has_etherscan_key() -> bool:
    return bool(ETHERSCAN_API_KEY)


def etherscan_get(chain: str, params: Dict[str, Any], retries: int = 1) -> Dict[str, Any]:
    """
    Shared Etherscan v2 request helper.

    chain:
      - ethereum
      - base

    Uses Etherscan v2 chainid mapping from config.
    """
    if not ETHERSCAN_API_KEY:
        return _empty_result()

    chainid = CHAIN_TO_ETHERSCAN_ID.get(chain)
    if not chainid:
        return _empty_result()

    final_params = {
        "chainid": chainid,
        "apikey": ETHERSCAN_API_KEY,
        **params,
    }

    try:
        data = request_json(
            "GET",
            ETHERSCAN_V2_URL,
            params=final_params,
            timeout=25,
            retries=retries,
            sleep_seconds=1.2,
        )
        return data if isinstance(data, dict) else _empty_result()
    except Exception:
        return _empty_result()


def get_block_by_timestamp(chain: str, unix_timestamp: int, closest: str = "before") -> Optional[int]:
    """
    Convert timestamp to nearest block number.

    closest:
      - before
      - after
    """
    data = etherscan_get(
        chain,
        {
            "module": "block",
            "action": "getblocknobytime",
            "timestamp": unix_timestamp,
            "closest": closest,
        },
    )

    result = data.get("result")
    try:
        return int(result)
    except Exception:
        return None


def get_normal_txs_by_address(
    chain: str,
    address: str,
    startblock: int = 0,
    endblock: int = 99999999,
    page: int = 1,
    offset: int = 100,
    sort: str = "asc",
) -> List[Dict[str, Any]]:
    data = etherscan_get(
        chain,
        {
            "module": "account",
            "action": "txlist",
            "address": address,
            "startblock": startblock,
            "endblock": endblock,
            "page": page,
            "offset": offset,
            "sort": sort,
        },
    )

    result = data.get("result", [])
    return result if isinstance(result, list) else []


def get_token_transfers(
    chain: str,
    contract_address: str,
    startblock: int = 0,
    endblock: int = 99999999,
    page: int = 1,
    offset: int = 100,
    sort: str = "asc",
) -> List[Dict[str, Any]]:
    data = etherscan_get(
        chain,
        {
            "module": "account",
            "action": "tokentx",
            "contractaddress": contract_address,
            "startblock": startblock,
            "endblock": endblock,
            "page": page,
            "offset": offset,
            "sort": sort,
        },
    )

    result = data.get("result", [])
    return result if isinstance(result, list) else []


def get_contract_source(chain: str, address: str) -> Dict[str, Any]:
    """
    Returns Etherscan source-code metadata.

    Useful fields usually include:
      - SourceCode
      - ABI
      - ContractName
      - CompilerVersion
      - Proxy
      - Implementation
    """
    data = etherscan_get(
        chain,
        {
            "module": "contract",
            "action": "getsourcecode",
            "address": address,
        },
    )

    result = data.get("result", [])
    if isinstance(result, list) and result:
        return result[0] if isinstance(result[0], dict) else {}

    return {}


def get_contract_abi(chain: str, address: str) -> Optional[str]:
    data = etherscan_get(
        chain,
        {
            "module": "contract",
            "action": "getabi",
            "address": address,
        },
    )

    result = data.get("result")
    if isinstance(result, str) and result and result != "Contract source code not verified":
        return result

    return None


def get_token_info(chain: str, address: str) -> Dict[str, Any]:
    """
    Token info may be unavailable or rate-limited depending on Etherscan plan.
    Fail soft.
    """
    data = etherscan_get(
        chain,
        {
            "module": "token",
            "action": "tokeninfo",
            "contractaddress": address,
        },
        retries=0,
    )

    result = data.get("result", [])
    if isinstance(result, list) and result:
        return result[0] if isinstance(result[0], dict) else {}

    return {}


def get_contract_creation(chain: str, addresses: List[str]) -> List[Dict[str, Any]]:
    """
    Etherscan has contract creation lookup for known contract addresses.
    This is enrichment, not broad discovery.
    """
    clean = [a for a in addresses if a]
    if not clean:
        return []

    data = etherscan_get(
        chain,
        {
            "module": "contract",
            "action": "getcontractcreation",
            "contractaddresses": ",".join(clean[:5]),
        },
        retries=0,
    )

    result = data.get("result", [])
    return result if isinstance(result, list) else []


def search_contract_creations_from_known_factory(
    chain: str,
    factory_address: str,
    startblock: int,
    endblock: int,
    offset: int = 100,
) -> List[Dict[str, Any]]:
    """
    Factory-based discovery.

    This does NOT scan the whole chain. It scans known factories/launch surfaces.
    That is intentional for MVP quality and GitHub Actions survival.
    """
    txs = get_normal_txs_by_address(
        chain=chain,
        address=factory_address,
        startblock=startblock,
        endblock=endblock,
        page=1,
        offset=offset,
        sort="asc",
    )

    out = []
    for tx in txs:
        if tx.get("isError") == "1":
            continue

        out.append(
            {
                "source": "etherscan_factory_scan",
                "chain": chain,
                "factory_address": factory_address,
                "creation_tx": tx.get("hash"),
                "creator": tx.get("from"),
                "to": tx.get("to"),
                "contract_address": tx.get("contractAddress") or None,
                "timestamp": tx.get("timeStamp"),
                "block_number": tx.get("blockNumber"),
                "raw": tx,
            }
        )

    return out
