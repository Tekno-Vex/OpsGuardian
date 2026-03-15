import time

print("Starting Memory Chaos — allocating RAM until 90% used...")
data = []
while True:
    with open('/proc/meminfo') as f:
        lines = f.readlines()
    mem_total = int([l for l in lines if 'MemTotal' in l][0].split()[1])
    mem_avail = int([l for l in lines if 'MemAvailable' in l][0].split()[1])
    current = ((mem_total - mem_avail) / mem_total) * 100
    print(f"Memory used: {current:.1f}%")
    if current >= 90:
        print("Target reached! Holding for 8 minutes...")
        time.sleep(480)
        break
    data.append(b'x' * 10**6)
    time.sleep(0.1)
print("Memory Chaos complete.")