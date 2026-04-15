
import os
import time, fnmatch
import queue
from concurrent.futures import ThreadPoolExecutor
from threading import Lock

print_lock = Lock()
result_lock = Lock()
counter_lock = Lock()

# final counts from each thread
total_scanned = [0]

def worker(search_queue, target_file, found_paths):
    
    local_count = 0
    q_get = search_queue.get
    q_put = search_queue.put
    q_done = search_queue.task_done
    
    while True:
        try:
            directory = q_get(timeout=0.05)
        except queue.Empty:
            # Thread is finishing, add local count to global total ONE TIME
            with counter_lock:
                total_scanned[0] += local_count
            return

        local_count += 1  # Increment local integer 

        try:
            with os.scandir(directory) as entries:
                for entry in entries:
                    if entry.is_file():
                        if fnmatch.fnmatch(entry.name, target_file):
                            with result_lock:
                                found_paths.append(entry.path)
                            with print_lock:
                                print(f"[FOUND]: {entry.path}")
                    elif entry.is_dir():
                        q_put(entry.path)
        except (PermissionError, OSError):
            pass
        finally:
            q_done()

def multi_threaded_search(root_dir, target_file, max_workers=40):
    start_time = time.perf_counter()
    root_dir = os.path.normpath(root_dir)
    
    if not os.path.isdir(root_dir):
        print(f"Error: {root_dir} is not a valid directory.")
        return []

    search_queue = queue.Queue()
    search_queue.put(root_dir)
    found_paths = []
    total_scanned[0] = 0 # Reset counter

    print(f"\n--- Searching in {root_dir} ---\n")

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        for _ in range(max_workers):
            executor.submit(worker, search_queue, target_file, found_paths)

        search_queue.join()

    total_time = time.perf_counter() - start_time

    print("\n--- Search Complete ---")
    print(f"Time Taken: {total_time:.2f} seconds")
    print(f"Total Directories Scanned: {total_scanned[0]}") 
    print(f"Matches: {len(found_paths)}")

    return found_paths

# --- Execution ---
root_input = input("Enter root location: ").strip()
target_input = input("Enter filename to be searched: ").strip()

multi_threaded_search(root_input, target_input)