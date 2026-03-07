import time
import multiprocessing

def cpu_stress():
    t_end = time.time() + 300
    while time.time() < t_end:
        pass

if __name__ == '__main__':
    cores = multiprocessing.cpu_count()
    print(f"Detected {cores} CPU cores. Starting Multi-Core Chaos for 5 minutes...")
    processes = []
    for i in range(cores):
        p = multiprocessing.Process(target=cpu_stress)
        p.start()
        processes.append(p)
    for p in processes:
        p.join()
    print("Chaos ended. CPUs returning to normal.")