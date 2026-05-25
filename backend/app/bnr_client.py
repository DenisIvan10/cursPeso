from __future__ import annotations

import urllib.request
import xml.etree.ElementTree as ET
from typing import Any, Dict

from .config import settings
from .data_loader import get_latest_rate, upsert_processed_rate


def fetch_latest_bnr_rate(currency: str | None = None) -> Dict[str, Any]:
    target_currency = (currency or settings.app_currency).upper()
    request = urllib.request.Request(
        settings.bnr_xml_url,
        headers={"User-Agent": "cursPeso/1.0"},
    )
    with urllib.request.urlopen(request, timeout=20) as response:
        payload = response.read()

    root = ET.fromstring(payload)
    namespace = {"bnr": "http://www.bnr.ro/xsd"}
    cube = root.find(".//bnr:Cube", namespace)
    if cube is None:
        raise ValueError("BNR XML response does not contain a Cube node.")

    publishing_date = cube.attrib.get("date")
    for rate in cube.findall("bnr:Rate", namespace):
        if rate.attrib.get("currency", "").upper() == target_currency:
            return {
                "currency": target_currency,
                "date": publishing_date,
                "value": float(rate.text or "nan"),
                "source": settings.bnr_xml_url,
            }

    raise ValueError(f"Currency {target_currency} was not found in the BNR XML response.")


def validate_latest_local_rate() -> Dict[str, Any]:
    local = get_latest_rate()
    remote = fetch_latest_bnr_rate()
    matches = local["date"] == remote["date"] and abs(local["value"] - remote["value"]) < 1e-9
    return {
        "matches": matches,
        "local": local,
        "remote": remote,
    }


def scrape_latest_bnr_rate() -> Dict[str, Any]:
    remote = fetch_latest_bnr_rate()
    update_result = upsert_processed_rate(remote["date"], remote["value"])
    return {
        "currency": remote["currency"],
        "source": remote["source"],
        "remote": remote,
        **update_result,
    }
