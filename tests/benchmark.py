"""
Benchmark script for Redis Global Search Taskbar
Tests latency (p50/p95/p99) and result-type distribution
"""

import time
import requests
import statistics
from typing import List, Dict
from collections import Counter

# Test queries covering different intents and types
TEST_QUERIES = [
    # Routes - Banking actions
    "pix",
    "pagar boleto",
    "fatura cartao",
    "extrato",
    "transferir dinheiro",
    "investimentos",
    "emprestimo",
    "recarga celular",
    "seguro",
    "limite cartao",
    
    # SKUs - Marketplace products
    "iphone",
    "samsung galaxy",
    "notebook",
    "airpods",
    "smart tv",
    "playstation",
    "tenis nike",
    "cafeteira",
    "geladeira",
    "camera gopro",
    
    # Products - Banking products
    "conta digital",
    "cdb",
    "tesouro direto",
    "cartao black",
    "previdencia",
    
    # Mixed/Ambiguous
    "comprar",
    "investir",
    "pagar",
    "seguro vida",
    "cashback"
]

API_URL = "http://localhost:8000/search"

def run_benchmark(queries: List[str] = TEST_QUERIES, iterations: int = 3):
    """
    Run benchmark tests
    
    Args:
        queries: List of test queries
        iterations: Number of times to run each query
    
    Returns:
        Dict with benchmark results
    """
    print("🚀 Starting Redis Global Search Taskbar Benchmark")
    print(f"📊 Testing {len(queries)} queries × {iterations} iterations = {len(queries) * iterations} total requests")
    print("=" * 70)
    
    latencies = []
    result_types = []
    intents = []
    total_results = []
    
    for i, query in enumerate(queries, 1):
        print(f"\n[{i}/{len(queries)}] Testing: '{query}'")
        
        for iteration in range(iterations):
            try:
                start_time = time.time()
                response = requests.get(API_URL, params={'q': query, 'limit': 10})
                end_time = time.time()
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Record metrics
                    client_latency = (end_time - start_time) * 1000  # Convert to ms
                    server_latency = data.get('latency_ms', 0)
                    total_latency = client_latency
                    
                    latencies.append(total_latency)
                    intents.append(data.get('intent', 'unknown'))
                    total_results.append(data.get('total', 0))
                    
                    # Record result types
                    for result in data.get('results', []):
                        result_types.append(result.get('type', 'unknown'))
                    
                    print(f"  ✓ Iteration {iteration + 1}: {total_latency:.1f}ms (server: {server_latency}ms) | {data.get('total', 0)} results | intent: {data.get('intent', 'unknown')}")
                else:
                    print(f"  ✗ Iteration {iteration + 1}: HTTP {response.status_code}")
                    
            except Exception as e:
                print(f"  ✗ Iteration {iteration + 1}: Error - {e}")
    
    # Calculate statistics
    print("\n" + "=" * 70)
    print("📈 BENCHMARK RESULTS")
    print("=" * 70)
    
    if latencies:
        print(f"\n⏱️  LATENCY (Total: Client + Server)")
        print(f"   Mean:  {statistics.mean(latencies):.2f}ms")
        print(f"   Median (p50): {statistics.median(latencies):.2f}ms")
        print(f"   p95:   {percentile(latencies, 95):.2f}ms")
        print(f"   p99:   {percentile(latencies, 99):.2f}ms")
        print(f"   Min:   {min(latencies):.2f}ms")
        print(f"   Max:   {max(latencies):.2f}ms")
    
    if result_types:
        print(f"\n📊 RESULT TYPE DISTRIBUTION")
        type_counts = Counter(result_types)
        total_count = sum(type_counts.values())
        for result_type, count in type_counts.most_common():
            percentage = (count / total_count) * 100
            print(f"   {result_type:10s}: {count:4d} ({percentage:5.1f}%)")
    
    if intents:
        print(f"\n🎯 INTENT DISTRIBUTION")
        intent_counts = Counter(intents)
        total_count = sum(intent_counts.values())
        for intent, count in intent_counts.most_common():
            percentage = (count / total_count) * 100
            print(f"   {intent:10s}: {count:4d} ({percentage:5.1f}%)")
    
    if total_results:
        print(f"\n🔍 RESULTS PER QUERY")
        print(f"   Mean:   {statistics.mean(total_results):.1f}")
        print(f"   Median: {statistics.median(total_results):.1f}")
        print(f"   Min:    {min(total_results)}")
        print(f"   Max:    {max(total_results)}")
    
    print("\n" + "=" * 70)
    print("✅ Benchmark complete!")
    
    return {
        'latencies': latencies,
        'result_types': result_types,
        'intents': intents,
        'total_results': total_results
    }

def percentile(data: List[float], p: float) -> float:
    """Calculate percentile"""
    sorted_data = sorted(data)
    index = (len(sorted_data) - 1) * (p / 100)
    floor = int(index)
    ceil = floor + 1
    
    if ceil >= len(sorted_data):
        return sorted_data[floor]
    
    # Linear interpolation
    return sorted_data[floor] + (sorted_data[ceil] - sorted_data[floor]) * (index - floor)

if __name__ == "__main__":
    try:
        # Check if server is running
        response = requests.get("http://localhost:8000/health", timeout=2)
        if response.status_code != 200:
            print("❌ Server is not healthy. Please start the server first.")
            exit(1)
    except:
        print("❌ Cannot connect to server. Please start the server first:")
        print("   python main.py")
        exit(1)
    
    # Run benchmark
    run_benchmark()

