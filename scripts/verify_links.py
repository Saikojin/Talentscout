import csv
import requests

def verify_links(csv_path):
    print(f"Verifying links in: {csv_path}")
    links_to_check = []
    
    try:
        with open(csv_path, mode='r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                if 'URL' in row and row['URL']:
                    links_to_check.append(row['URL'])
    except Exception as e:
        print(f"Error reading CSV: {e}")
        return

    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
    }

    print(f"{'URL':<60} | {'Status':<10} | {'Redirected?'}")
    print("-" * 90)

    for url in links_to_check:
        try:
            # We use allow_redirects=False to strictly catch the first response code
            # However, some sites might do a 301 to a canonical URL (http -> https, or www -> non-www) which is "valid"
            # But the user said "If they redirect whatsoever, I would presume they are not valid roles."
            # So we will report strictly.
            response = requests.get(url, headers=headers, allow_redirects=False, timeout=10)
            
            is_redirect = response.status_code in [301, 302, 303, 307, 308]
            status_display = str(response.status_code)
            
            # If it's a redirect, let's see where it goes
            redirect_info = ""
            if is_redirect:
                redirect_info = f"-> {response.headers.get('Location', 'unknown')}"
            
            print(f"{url[:58]:<60} | {status_display:<10} | {is_redirect} {redirect_info}")
            
        except requests.Exceptions.RequestException as e:
             print(f"{url[:58]:<60} | Error      | {e}")
        except Exception as e:
            print(f"{url[:58]:<60} | Error      | {e}")

if __name__ == "__main__":
    verify_links("d:/DevWorkspace/TalentScout/logs/application_history.csv")
