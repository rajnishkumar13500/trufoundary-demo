import sys
import time
import json
import random
import argparse
import statistics
import concurrent.futures
import httpx

def run_load_test(base_url: str = "http://localhost:8000", total_requests: int = 100, concurrency: int = 10):
    print(f"[*] Starting Load Test on {base_url} (requests={total_requests}, concurrency={concurrency})...")

    # Fetch initial metrics
    client = httpx.Client(timeout=30.0)
    try:
        health = client.get(f"{base_url}/health").json()
        print(f"[*] Target service status: {health.get('status')} | DB: {health.get('database')}")
    except Exception as e:
        print(f"[!] Target service is unreachable at {base_url}: {e}")
        sys.exit(1)

    latencies = []
    errors = 0
    start_time = time.perf_counter()

    def make_request(req_id: int):
        user_id = random.randint(1, 20)
        url = f"{base_url}/orders?user_id={user_id}&limit=50"
        t0 = time.perf_counter()
        try:
            r = client.get(url)
            dur = (time.perf_counter() - t0) * 1000
            if r.status_code == 200:
                return (dur, True)
            else:
                return (dur, False)
        except Exception:
            return ((time.perf_counter() - t0) * 1000, False)

    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as executor:
        futures = [executor.submit(make_request, i) for i in range(total_requests)]
        for f in concurrent.futures.as_completed(futures):
            dur, success = f.result()
            latencies.append(dur)
            if not success:
                errors += 1

    total_duration = time.perf_counter() - start_time
    client.close()

    # Calculate percentiles
    sorted_lat = sorted(latencies)
    def pct(p):
        if not sorted_lat:
            return 0.0
        idx = int((len(sorted_lat) - 1) * (p / 100.0))
        return round(sorted_lat[idx], 2)

    p50 = pct(50)
    p90 = pct(90)
    p95 = pct(95)
    p99 = pct(99)
    avg_lat = round(statistics.mean(latencies), 2) if latencies else 0.0
    throughput = round(total_requests / total_duration, 2)
    error_rate = round(errors / total_requests, 4) if total_requests else 0.0

    report = {
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "total_requests": total_requests,
        "concurrency": concurrency,
        "duration_seconds": round(total_duration, 2),
        "throughput_rps": throughput,
        "error_count": errors,
        "error_rate": error_rate,
        "latency_avg_ms": avg_lat,
        "latency_p50_ms": p50,
        "latency_p90_ms": p90,
        "latency_p95_ms": p95,
        "latency_p99_ms": p99,
        "min_latency_ms": round(sorted_lat[0], 2) if sorted_lat else 0.0,
        "max_latency_ms": round(sorted_lat[-1], 2) if sorted_lat else 0.0
    }

    print("\n" + "=" * 50)
    print(" LOAD TEST EVIDENCE REPORT ")
    print("=" * 50)
    print(f" Requests:      {total_requests} (concurrency={concurrency})")
    print(f" Duration:      {round(total_duration, 2)} s")
    print(f" Throughput:    {throughput} req/s")
    print(f" Errors:        {errors} ({round(error_rate * 100, 2)}%)")
    print(f" Latency p50:   {p50} ms")
    print(f" Latency p95:   {p95} ms")
    print(f" Latency p99:   {p99} ms")
    print("=" * 50 + "\n")

    return report

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="ActionShield Load Testing Harness")
    parser.add_argument("--url", default="http://localhost:8000", help="Base URL of target API")
    parser.add_argument("-n", "--requests", type=int, default=100, help="Total requests")
    parser.add_argument("-c", "--concurrency", type=int, default=10, help="Concurrency level")
    parser.add_argument("--output", default=None, help="Path to write JSON evidence output")

    args = parser.parse_args()
    res = run_load_test(base_url=args.url, total_requests=args.requests, concurrency=args.concurrency)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(res, f, indent=2)
        print(f"[OK] Report saved to {args.output}")
