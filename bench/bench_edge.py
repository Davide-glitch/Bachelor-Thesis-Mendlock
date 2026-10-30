"""Hardware benchmark: Workstation in-memory ctypes vs. ARM64 Raspberry Pi Edge Daemon."""
from __future__ import annotations

import argparse
import json
import socket
import time

from mendlock import native_bridge


def query_edge_daemon(host: str, port: int, cmd: str, s1: str, s2: str) -> dict:
    payload = f"{cmd}\t{s1}\t{s2}\n".encode("utf-8")
    t0 = time.perf_counter()
    with socket.create_connection((host, port), timeout=3.0) as sock:
        sock.sendall(payload)
        data = sock.recv(4096).decode("utf-8").strip()
    rtt_ms = (time.perf_counter() - t0) * 1000.0
    res = json.loads(data)
    res["rtt_ms"] = rtt_ms
    return res


def run_edge_benchmark(host: str, port: int, iterations: int = 100) -> None:
    s1 = "Place the corporate order and confirm payment"
    s2 = "Place Order Preview"

    # 1. Local Workstation In-Memory (ctypes)
    local_times_us = []
    if native_bridge.HAVE_NATIVE:
        for _ in range(iterations):
            t0 = time.perf_counter()
            _ = native_bridge.native_trigram_cosine(s1, s2)
            local_times_us.append((time.perf_counter() - t0) * 1e6)

    # 2. Remote / Edge Daemon over TCP
    edge_compute_us = []
    edge_rtt_ms = []
    temps = []

    for _ in range(iterations):
        res = query_edge_daemon(host, port, "TRIGRAM", s1, s2)
        edge_compute_us.append(float(res["compute_us"]))
        edge_rtt_ms.append(float(res["rtt_ms"]))
        if res.get("cpu_temp_c", -1.0) > 0:
            temps.append(float(res["cpu_temp_c"]))

    mean_local_us = sum(local_times_us) / max(len(local_times_us), 1)
    mean_edge_us = sum(edge_compute_us) / len(edge_compute_us)
    mean_rtt_ms = sum(edge_rtt_ms) / len(edge_rtt_ms)
    mean_temp = sum(temps) / len(temps) if temps else -1.0

    print("\n# Mendlock Edge vs. Workstation Hardware Benchmark")
    print(f"Target Edge Node: `{host}:{port}` ({iterations} iterations)\n")
    print("| Metric | Workstation (In-Memory ctypes) | Edge Node (ARM64 TCP Daemon) |")
    print("|---|---|---|")
    print(f"| Pure Compute Latency (mean) | {mean_local_us:.2f} us | {mean_edge_us:.2f} us |")
    print(f"| End-to-End RTT Latency (mean) | {mean_local_us / 1000.0:.4f} ms | {mean_rtt_ms:.2f} ms |")
    print(f"| Throughput (evaluations/sec) | {1e6 / max(mean_local_us, 1e-3):.0f} ops/s | {1000.0 / max(mean_rtt_ms, 1e-3):.0f} ops/s |")
    print(f"| Device Thermal Telemetry | N/A | {f'{mean_temp:.1f} C' if mean_temp > 0 else 'N/A (Non-Linux/VM)'} |")


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description="Benchmark Mendlock C++ Edge Daemon")
    ap.add_argument("--host", default="127.0.0.1", help="IP address of the Raspberry Pi or local daemon")
    ap.add_argument("--port", type=int, default=9090, help="TCP port of mendlock_edge_daemon")
    ap.add_argument("--iters", type=int, default=100, help="Number of benchmark requests")
    args = ap.parse_args()
    run_edge_benchmark(args.host, args.port, args.iters)