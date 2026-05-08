"""Runtime behavior for probing nodes through the Clash controller."""

from __future__ import annotations

import concurrent.futures
import json
import os
import shutil
import statistics
import subprocess
import time
from dataclasses import dataclass, field
from typing import Any
from urllib import parse

from autoprobe_config import SKIP_NODES, US_MARKERS


@dataclass
class Probe:
    """Per-URL probe statistics for one node."""

    url: str
    attempts: int = 0
    successes: int = 0
    statuses: list[str] = field(default_factory=list)
    latencies: list[float] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)


@dataclass
class NodeResult:
    """Aggregated probe outcome for a candidate node."""

    name: str
    delay_ms: int | None = None
    probes: dict[str, Probe] = field(default_factory=dict)

    @property
    def success_count(self) -> int:
        return sum(probe.successes for probe in self.probes.values())

    @property
    def attempt_count(self) -> int:
        return sum(probe.attempts for probe in self.probes.values())

    @property
    def success_rate(self) -> float:
        return 0.0 if self.attempt_count == 0 else self.success_count / self.attempt_count

    @property
    def avg_latency(self) -> float:
        latencies = [latency for probe in self.probes.values() for latency in probe.latencies]
        return float("inf") if not latencies else statistics.fmean(latencies)


class ClashClient:
    """Minimal Clash API client implemented on top of curl for portability."""

    def __init__(self, controller: str, secret: str | None, controller_unix: str | None = None) -> None:
        self.controller = controller.rstrip("/")
        self.secret = secret
        self.controller_unix = controller_unix or None

    def _request(self, method: str, path: str, payload: dict[str, Any] | None = None) -> Any:
        url = f"{self.controller}{path}"
        cmd = [
            "curl",
            "-sS",
            "--max-time",
            "10",
            "-X",
            method,
            "-w",
            "\n%{http_code}",
            url,
        ]
        if self.controller_unix:
            cmd[1:1] = ["--unix-socket", self.controller_unix]
        if self.secret:
            cmd.extend(["-H", f"Authorization: Bearer {self.secret}"])
        if payload is not None:
            cmd.extend(["-H", "Content-Type: application/json", "--data-binary", json.dumps(payload)])

        proc = subprocess.run(cmd, capture_output=True, text=True)
        if proc.returncode != 0:
            error_text = proc.stderr.strip() or f"curl exit {proc.returncode}"
            raise RuntimeError(f"{method} {path} failed: {error_text}")

        body, _, status_text = proc.stdout.rpartition("\n")
        try:
            status = int(status_text.strip())
        except ValueError as exc:
            raise RuntimeError(f"{method} {path} failed: could not parse HTTP status from curl output") from exc
        if status >= 400:
            raise RuntimeError(f"{method} {path} failed: {status} {body.strip()}")
        if not body.strip():
            return None
        try:
            return json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"{method} {path} failed: non-JSON response: {body[:200]!r}") from exc

    def get_selector(self, selector: str) -> dict[str, Any]:
        encoded = parse.quote(selector, safe="")
        return self._request("GET", f"/proxies/{encoded}")

    def set_selector(self, selector: str, node: str) -> None:
        encoded = parse.quote(selector, safe="")
        self._request("PUT", f"/proxies/{encoded}", {"name": node})

    def get_proxy_delay(self, node: str, url: str, timeout_ms: int) -> int | None:
        encoded = parse.quote(node, safe="")
        query = parse.urlencode({"url": url, "timeout": str(timeout_ms)})
        try:
            data = self._request("GET", f"/proxies/{encoded}/delay?{query}")
        except RuntimeError:
            return None
        if isinstance(data, dict):
            delay = data.get("delay")
            return delay if isinstance(delay, int) and delay >= 0 else None
        return None


def ensure_curl() -> None:
    """Fail early when the only external dependency is missing."""
    if shutil.which("curl") is None:
        raise SystemExit("curl not found in PATH")


def run_probe(proxy: str, url: str, timeout: int) -> tuple[bool, str, float, str]:
    """Probe one URL through the active selector and return status, latency, and errors."""
    cmd = [
        "curl",
        "-I",
        "--max-time",
        str(timeout),
        "--proxy",
        proxy,
        "-o",
        os.devnull,
        "-sS",
        "-w",
        "%{http_code} %{time_total}",
        url,
    ]
    started = time.monotonic()
    proc = subprocess.run(cmd, capture_output=True, text=True)
    elapsed = time.monotonic() - started
    if proc.returncode == 0:
        parts = proc.stdout.strip().split()
        status = parts[0] if parts else "000"
        latency = float(parts[1]) if len(parts) > 1 else elapsed
        return status != "000", status, latency, ""
    return False, "000", elapsed, (proc.stderr.strip() or f"curl exit {proc.returncode}")


def choose_candidates(selector_info: dict[str, Any], explicit_nodes: list[str], top: int) -> list[str]:
    """Pick candidate nodes, preferring US-marked names when no explicit shortlist is provided."""
    if explicit_nodes:
        return explicit_nodes
    nodes = [name for name in selector_info.get("all", []) if name not in SKIP_NODES]
    prioritized = sorted(
        nodes,
        key=lambda name: (0 if any(marker in name for marker in US_MARKERS) else 1, name),
    )
    return prioritized if top <= 0 else prioritized[:top]


def test_node(
    client: ClashClient,
    selector: str,
    node: str,
    urls: list[str],
    attempts: int,
    timeout: int,
    proxy: str,
    switch_delay: float,
    request_delay: float,
) -> NodeResult:
    """Run the serial validation phase for one node while the shared selector points to it."""
    client.set_selector(selector, node)
    time.sleep(switch_delay)

    result = NodeResult(name=node)
    for url in urls:
        probe = Probe(url=url)
        result.probes[url] = probe
        for _ in range(attempts):
            probe.attempts += 1
            ok, status, latency, err = run_probe(proxy, url, timeout)
            probe.statuses.append(status)
            if ok:
                probe.successes += 1
                probe.latencies.append(latency)
            elif err:
                probe.errors.append(err)
            time.sleep(request_delay)
    return result


def print_result(result: NodeResult) -> None:
    """Render a compact per-node probe summary."""
    avg = "n/a" if result.avg_latency == float("inf") else f"{result.avg_latency:.2f}s"
    delay = "n/a" if result.delay_ms is None else f"{result.delay_ms}ms"
    print(f"{result.name}: precheck {delay}, success {result.success_count}/{result.attempt_count}, avg latency {avg}")
    for url, probe in result.probes.items():
        probe_avg = "n/a" if not probe.latencies else f"{statistics.fmean(probe.latencies):.2f}s"
        suffix = f" last_error={probe.errors[-1]}" if probe.errors else ""
        print(
            f"  {url}: {probe.successes}/{probe.attempts} success, "
            f"statuses={','.join(probe.statuses)}, avg={probe_avg}{suffix}"
        )


def precheck_node(client: ClashClient, node: str, url: str, timeout_ms: int) -> tuple[str, int | None]:
    """Wrapper used by the thread pool during the delay precheck phase."""
    return node, client.get_proxy_delay(node, url, timeout_ms)


def build_finalists(
    client: ClashClient,
    candidates: list[str],
    delay_url: str,
    delay_timeout_ms: int,
    precheck_workers: int,
    finalists_count: int,
) -> tuple[list[str], dict[str, int | None]]:
    """Expand precheck batches until enough passing nodes are found."""
    delay_map: dict[str, int | None] = {}
    selected: list[str] = []
    cursor = 0
    batch_size = max(finalists_count, precheck_workers, 1)

    while cursor < len(candidates) and len(selected) < finalists_count:
        batch = candidates[cursor : cursor + batch_size]
        cursor += len(batch)
        with concurrent.futures.ThreadPoolExecutor(max_workers=max(1, precheck_workers)) as executor:
            futures = [
                executor.submit(precheck_node, client, node, delay_url, delay_timeout_ms)
                for node in batch
            ]
            batch_results = [future.result() for future in concurrent.futures.as_completed(futures)]

        ranked_batch = sorted(
            batch_results,
            key=lambda item: (item[1] is None, item[1] if item[1] is not None else 10**9, item[0]),
        )
        for node, delay in ranked_batch:
            delay_map[node] = delay
            delay_text = "failed" if delay is None else f"{delay}ms"
            print(f"  {node}: {delay_text}")
            if delay is not None and node not in selected and len(selected) < finalists_count:
                selected.append(node)

        if len(selected) < finalists_count and cursor < len(candidates):
            print(f"  Not enough passing nodes yet, expanding precheck to more candidates ({len(selected)}/{finalists_count}).")

    return selected, delay_map
