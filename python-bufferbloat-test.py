#!/usr/bin/env uv run
import socket
import time
import threading
import requests
from statistics import mean, stdev

# Configuration:
# Ping time will be measured using TCP connect on HTTPS port 443. Specify hosts and ping interval in seconds:
PING_HOSTS = ('1.1.1.1', '1.0.0.1', '8.8.8.8', '8.8.4.4', '9.9.9.9', '149.112.112.112')
PING_INTERVAL = 0.1
# Network interface will be loaded by downloading large files from these URLs:
DOWNLOAD_URLS = (
    'https://nbg1-speed.hetzner.com/10GB.bin',
    'https://github.com/szalony9szymek/large/releases/download/free/large',
    'https://download.thinkbroadband.com/5GB.zip',
)
# Specify duration in seconds of each phase (unloaded and loaded pings):
DURATION = 60
# Number of parallel download connections:
PARALLEL_DOWNLOADS = 6

def tcp_ping(host, port, timeout=0.5):
    start = time.time()
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return (time.time() - start) * 1000  # ms
    except Exception:
        return None

def ping_worker(hosts, duration, interval, stop_event, results):
    rtts = []
    start = time.time()
    host_nr = 0
    while (time.time() - start) < duration and not stop_event.is_set():
        rtt = tcp_ping(hosts[host_nr], 443)
        host_nr = (host_nr + 1) % len(hosts)
        if rtt is not None:
            rtts.append(rtt)
        time.sleep(interval)
    results.extend(rtts)

def download_worker(url, duration, stop_event, result):
    start = time.time()
    total_bytes = 0
    try:
        with requests.get(url, stream=True, timeout=10) as r:
            r.raise_for_status()
            for chunk in r.iter_content(chunk_size=64*1024):
                if stop_event.is_set() or (time.time() - start) >= duration:
                    break
                total_bytes += len(chunk)
    except Exception as e:
        print(f"[WARN] Download error: {e}")
    result['bytes'] = total_bytes
    result['elapsed'] = time.time() - start

def percentile(data, q):
    sorted_data = sorted(data)
    rank = q / 100.0 * (len(sorted_data) - 1)
    
    # Handle edge case:
    if rank >= len(sorted_data) - 1:
        return sorted_data[int(rank)]
    
    # Linear interpolation:
    lower_value = sorted_data[int(rank)]
    upper_value = sorted_data[int(rank) + 1]
    return lower_value + (rank - int(rank)) * (upper_value - lower_value)

def jitter(rtts):
    result = 0
    for i in range(len(rtts) - 1):
        result += abs(rtts[i+1] - rtts[i])
    result /= (len(rtts) - 1)
    return result

def calculate_ping_stats(rtts):
    if not rtts:
        print("Error: Could not reach any host.")
        exit(1)
    return {
        'min': min(rtts),
        '25%': percentile(rtts, 25),
        '50%': percentile(rtts, 50),
        'mean': mean(rtts),
        '75%': percentile(rtts, 75),
        '95%': percentile(rtts, 95),
        'max': max(rtts),
        'std': stdev(rtts),
        'jit': jitter(rtts),
    }

def print_download_stats(results_list):
    bytes = sum(res.get('bytes', 0) for res in results_list)
    elapsed = max((res.get('elapsed', 1) for res in results_list)) 
    download_speed = bytes * 8 / elapsed  # in bits/second
    print(f"Average download speed: {download_speed/1e6:.1f} Mbps")

def run_latency_test(loaded=False):
    stop_event = threading.Event()
    rtts = []

    threads = []
    t_ping = threading.Thread(target=ping_worker, args=(PING_HOSTS, DURATION, PING_INTERVAL, stop_event, rtts))
    threads.append(t_ping)
    t_ping.start()

    download_results_list = []
    if loaded:
        for i in range(PARALLEL_DOWNLOADS):
            # Each thread gets its own dictionary in the shared list to update
            download_result = {}
            download_results_list.append(download_result)
            t_dl = threading.Thread(target=download_worker, args=(DOWNLOAD_URLS[i % len(DOWNLOAD_URLS)], DURATION, stop_event, download_result))
            threads.append(t_dl)
            t_dl.start()

    time.sleep(DURATION)
    stop_event.set()
    for t in threads:
        t.join()

    return rtts, download_results_list

def main():
    rtts1, _ = run_latency_test(loaded=False)
    stats1 = calculate_ping_stats(rtts1)
    print('                       ', *[f'{s:>6}' for s in ('min', '25%', 'median', 'mean', '75%', '95%', 'max', 'std', 'jit')])
    print('Unloaded latency in ms:', *[f'{stats1[s]:6.0f}' for s in ('min', '25%', '50%', 'mean', '75%', '95%', 'max', 'std', 'jit')])

    rtts2, dl_res = run_latency_test(loaded=True)
    stats2 = calculate_ping_stats(rtts2)
    print('Loaded latency in ms:  ', *[f'{stats2[s]:6.0f}' for s in ('min', '25%', '50%', 'mean', '75%', '95%', 'max', 'std', 'jit')])
    print('Difference in ms:      ', *[f'{round(stats2[s])-round(stats1[s]):+6}' for s in ('min', '25%', '50%', 'mean', '75%', '95%', 'max', 'std', 'jit')])
    print_download_stats(dl_res)

if __name__ == '__main__':
    main()
