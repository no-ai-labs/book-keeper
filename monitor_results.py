#!/usr/bin/env python3
"""
Real-time monitoring of contradiction detection results
"""

import json
import time
import os
from datetime import datetime
from colorama import init, Fore, Style

init()

def monitor_results():
    """Monitor the results files in real-time"""
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}")
    print(f"{Fore.CYAN}Book Keeper - Results Monitor{Style.RESET_ALL}")
    print(f"{Fore.CYAN}{'='*60}{Style.RESET_ALL}\n")
    print("Press Ctrl+C to stop monitoring\n")
    
    last_size = 0
    
    try:
        while True:
            # Check if JSON file exists and has content
            if os.path.exists("contradictions.json"):
                try:
                    with open("contradictions.json", "r", encoding="utf-8") as f:
                        data = json.load(f)
                    
                    current_size = len(data.get("contradictions", []))
                    
                    if current_size > last_size:
                        print(f"\n{Fore.GREEN}[{datetime.now().strftime('%H:%M:%S')}] Found {current_size} contradiction(s) so far!{Style.RESET_ALL}")
                        
                        # Show latest contradictions
                        for idx, c in enumerate(data["contradictions"][last_size:], last_size + 1):
                            print(f"\n{Fore.YELLOW}Contradiction #{idx}:{Style.RESET_ALL}")
                            
                            # Extract chapter info from IDs
                            ch1_parts = c['chapter1_id'].split('_')[1:-1]
                            ch2_parts = c['chapter2_id'].split('_')[1:-1]
                            ch1_display = ' '.join(ch1_parts)
                            ch2_display = ' '.join(ch2_parts)
                            
                            print(f"  Chapters: {Fore.CYAN}{ch1_display}{Style.RESET_ALL} vs {Fore.CYAN}{ch2_display}{Style.RESET_ALL}")
                            print(f"  Type: {c['type']}")
                            print(f"  Confidence: {c['confidence']:.2f}")
                            print(f"  {Fore.RED}Explanation: {c['explanation'][:150]}...{Style.RESET_ALL}")
                        
                        last_size = current_size
                    
                except (json.JSONDecodeError, KeyError):
                    # File is being written, try again
                    pass
            
            # Also check markdown file size
            if os.path.exists("contradictions_report.md"):
                md_size = os.path.getsize("contradictions_report.md")
                if md_size > 200:  # More than just header
                    print(f"\r{Fore.CYAN}Markdown report size: {md_size} bytes{Style.RESET_ALL}", end="", flush=True)
            
            time.sleep(2)  # Check every 2 seconds
            
    except KeyboardInterrupt:
        print(f"\n\n{Fore.YELLOW}Monitoring stopped.{Style.RESET_ALL}")
        
        # Show final summary if file exists
        if os.path.exists("contradictions.json"):
            try:
                with open("contradictions.json", "r", encoding="utf-8") as f:
                    data = json.load(f)
                
                print(f"\n{Fore.GREEN}Final Results:{Style.RESET_ALL}")
                print(f"Total contradictions found: {len(data.get('contradictions', []))}")
                
                # Group by type
                by_type = {}
                for c in data.get("contradictions", []):
                    by_type.setdefault(c["type"], 0)
                    by_type[c["type"]] += 1
                
                print("\nBy Type:")
                for t, count in by_type.items():
                    print(f"  - {t}: {count}")
                    
            except:
                pass

if __name__ == "__main__":
    monitor_results() 