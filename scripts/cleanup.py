import os
import glob

def clean_logs(logs_dir="logs"):
    """
    Cleans up temporary files in the logs directory, such as screenshots 
    and general JSON dumps, while preserving essential maps like skill_map.json 
    and the final scour_results.json.
    """
    if not os.path.exists(logs_dir):
        return
        
    print("\n[*] Running Pre-Scour Cleanup...")
    
    # Files to keep no matter what
    KEEP_FILES = {
        "skill_map.json",
        "scour_results.json"
    }
    
    deleted_count = 0
    
    # 1. Clean all Highlight Screenshots (from crawler_learner)
    screenshots = glob.glob(os.path.join(logs_dir, "highlight_*.png"))
    for file_path in screenshots:
        try:
            os.remove(file_path)
            deleted_count += 1
        except Exception as e:
            print(f"  [!] Failed to delete {file_path}: {e}")
            
    # 2. Clean general files not in KEEP_FILES
    for filename in os.listdir(logs_dir):
        if filename in KEEP_FILES:
            continue
            
        file_path = os.path.join(logs_dir, filename)
        if os.path.isfile(file_path) and not filename.startswith("highlight_"):
            try:
                os.remove(file_path)
                deleted_count += 1
            except Exception as e:
                print(f"  [!] Failed to delete {file_path}: {e}")
                
    if deleted_count > 0:
        print(f"[*] Cleanup complete. Removed {deleted_count} temporary files.\n")
    else:
        print("[*] Cleanup complete. No temporary files found.\n")
