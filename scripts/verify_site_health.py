import argparse
import asyncio
import datetime
import json
import os
import socket
import sys
from typing import Dict, List, Tuple, Any, Optional
from urllib.parse import urlparse

# Ensure project root is in sys.path
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BASE_DIR not in sys.path:
    sys.path.append(BASE_DIR)

DEFAULT_QUARANTINE_FILE = "quarantined_domains.json"

def extract_hostname(url_or_domain: str) -> str:
    """Safely extract the network hostname from a URL or raw domain string."""
    if not url_or_domain:
        return ""
    target = url_or_domain.strip()
    if "://" in target or target.startswith("//"):
        host = urlparse(target).netloc.lower()
    else:
        host = target.lower().split("/")[0]

    if ":" in host:
        host = host.split(":")[0]
    return host

def _dns_sync(hostname: str) -> Tuple[bool, str]:
    if not hostname:
        return False, "EMPTY_HOSTNAME"
    try:
        socket.getaddrinfo(hostname, None)
        return True, "OK"
    except socket.gaierror as e:
        return False, f"DNS_UNREACHABLE: {e}"
    except socket.timeout:
        return False, "DNS_TIMEOUT"
    except Exception as e:
        return False, f"DNS_ERROR: {e}"

async def probe_domain_health(url_or_domain: str, timeout: float = 5.0) -> Tuple[bool, str]:
    """Non-blocking DNS check with a strict timeout."""
    hostname = extract_hostname(url_or_domain)
    if not hostname:
        return False, "EMPTY_HOSTNAME"

    loop = asyncio.get_running_loop()
    try:
        is_alive, reason = await asyncio.wait_for(
            loop.run_in_executor(None, _dns_sync, hostname),
            timeout=timeout
        )
        return is_alive, reason
    except asyncio.TimeoutError:
        return False, "DNS_TIMEOUT: Timeout exceeded"
    except Exception as e:
        return False, f"PROBE_EXCEPTION: {e}"

async def audit_sources(
    sources: List[Dict[str, Any]],
    timeout: float = 5.0,
    concurrency: int = 25
) -> Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]:
    """Concurrently probe a list of sources and divide into healthy and dead lists."""
    semaphore = asyncio.Semaphore(concurrency)
    healthy: List[Dict[str, Any]] = []
    dead: List[Dict[str, Any]] = []

    async def check_one(item):
        url = item.get("url") or item.get("careers_url") or item.get("ats_url") or item.get("search_url") or ""
        hostname = extract_hostname(url)
        async with semaphore:
            is_alive, reason = await probe_domain_health(url, timeout=timeout)
            record = dict(item)
            record["domain"] = hostname
            record["probe_status"] = reason
            if is_alive:
                healthy.append(record)
            else:
                record["reason"] = reason
                dead.append(record)

    tasks = [check_one(s) for s in sources]
    await asyncio.gather(*tasks, return_exceptions=True)
    return healthy, dead

def quarantine_dead_domains(dead_sources: List[Dict[str, Any]], filepath: str = DEFAULT_QUARANTINE_FILE):
    """Save unreachable domains to the quarantine JSON file."""
    existing = []
    if os.path.exists(filepath):
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                existing = json.load(f)
            if not isinstance(existing, list):
                existing = []
        except Exception:
            existing = []

    seen = {item.get("domain", "") for item in existing}
    now_iso = datetime.datetime.now().isoformat()

    for item in dead_sources:
        dom = item.get("domain", "")
        if dom and dom not in seen:
            seen.add(dom)
            existing.append({
                "domain": dom,
                "name": item.get("name", "Unknown"),
                "url": item.get("url", ""),
                "reason": item.get("reason", "DNS_UNREACHABLE"),
                "quarantined_at": now_iso
            })

    temp_path = f"{filepath}.tmp"
    with open(temp_path, "w", encoding="utf-8") as f:
        json.dump(existing, f, indent=2)
    os.replace(temp_path, filepath)

def load_all_project_targets() -> List[Dict[str, Any]]:
    """Gather all unique target URLs from base_companies.json and job_search_sites.json."""
    targets = []
    seen_urls = set()

    # 1. base_companies.json
    comp_file = os.path.join(BASE_DIR, "base_companies.json")
    if os.path.exists(comp_file):
        try:
            with open(comp_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            companies = data.get("companies", []) if isinstance(data, dict) else (data if isinstance(data, list) else [])
            for c in companies:
                url = c.get("careers_url") or c.get("ats_url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    targets.append({
                        "name": c.get("name", "Unknown Company"),
                        "url": url,
                        "source": "base_companies.json"
                    })
        except Exception as e:
            print(f"[!] Error reading base_companies.json: {e}")

    # 2. job_search_sites.json
    sites_file = os.path.join(BASE_DIR, "job_search_sites.json")
    if os.path.exists(sites_file):
        try:
            with open(sites_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            sites = data.get("job_search_sites", []) if isinstance(data, dict) else []
            for s in sites:
                url = s.get("url")
                if url and url not in seen_urls:
                    seen_urls.add(url)
                    targets.append({
                        "name": s.get("name", "Unknown Board"),
                        "url": url,
                        "source": "job_search_sites.json"
                    })
        except Exception as e:
            print(f"[!] Error reading job_search_sites.json: {e}")

    return targets

def prune_dead_companies_from_file(dead_domains: set, filepath: str = "base_companies.json"):
    """Remove dead companies from base_companies.json with a backup."""
    if not os.path.exists(filepath):
        return 0

    with open(filepath, "r", encoding="utf-8") as f:
        data = json.load(f)

    # Save backup
    bak_path = f"{filepath}.bak"
    with open(bak_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    is_dict = isinstance(data, dict)
    companies = data.get("companies", []) if is_dict else data

    retained = []
    pruned_count = 0

    for c in companies:
        url = c.get("careers_url") or c.get("ats_url") or ""
        host = extract_hostname(url)
        if host in dead_domains:
            pruned_count += 1
        else:
            retained.append(c)

    if is_dict:
        data["companies"] = retained
    else:
        data = retained

    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4)

    return pruned_count

async def main():
    parser = argparse.ArgumentParser(
        description="Verify DNS and Endpoint Health across TalentScout targets to eliminate DNS / Unreachable failures."
    )
    parser.add_argument("--audit-only", action="store_true", default=True, help="Scan and quarantine dead domains without modifying company files (default)")
    parser.add_argument("--prune-dead-domains", action="store_true", help="Prune verified dead domains from base_companies.json (creates .bak)")
    parser.add_argument("--timeout", type=float, default=5.0, help="DNS probe timeout in seconds (default: 5.0)")
    parser.add_argument("--concurrency", type=int, default=30, help="Max concurrent DNS probes (default: 30)")
    parser.add_argument("--quarantine-file", default=DEFAULT_QUARANTINE_FILE, help="Destination quarantine JSON file")

    args = parser.parse_args()

    targets = load_all_project_targets()
    print(f"[*] Loaded {len(targets)} unique target endpoints across TalentScout.")
    print(f"[*] Auditing domain health (timeout: {args.timeout}s, concurrency: {args.concurrency})...")

    healthy, dead = await audit_sources(targets, timeout=args.timeout, concurrency=args.concurrency)

    print("\n" + "=" * 70)
    print("                    ENDPOINT HEALTH AUDIT SUMMARY")
    print("=" * 70)
    print(f"  [+] Healthy / Resolvable Domains: {len(healthy)}")
    print(f"  [!] Unreachable / Dead Domains:   {len(dead)}")
    print("-" * 70)

    if dead:
        print("  Sample Dead Domains Discovered:")
        for d in dead[:10]:
            print(f"    * {d['name'][:24]:25} | {d['domain']:30} | {d['reason'][:30]}")
        if len(dead) > 10:
            print(f"    ... and {len(dead) - 10} more.")

        quarantine_dead_domains(dead, filepath=args.quarantine_file)
        print(f"\n[*] Saved {len(dead)} dead domains to {args.quarantine_file}")

    if args.prune_dead_domains and dead:
        dead_domain_set = {d["domain"] for d in dead if d.get("domain")}
        comp_path = os.path.join(BASE_DIR, "base_companies.json")
        pruned = prune_dead_companies_from_file(dead_domain_set, comp_path)
        print(f"[*] Pruned {pruned} dead company entries from base_companies.json (backup at {comp_path}.bak)")

    print("=" * 70)

if __name__ == "__main__":
    asyncio.run(main())
