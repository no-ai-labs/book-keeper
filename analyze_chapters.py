#!/usr/bin/env python3
"""
Analyze extracted chapter information
"""

import json
import os
from collections import defaultdict

def analyze_chapters():
    """Analyze chapter extraction patterns"""
    
    result_file = "contradictions_interim.json"
    if not os.path.exists(result_file):
        print("No results file found.")
        return
    
    with open(result_file, 'r', encoding='utf-8') as f:
        data = json.load(f)
    
    # Extract unique chapter IDs
    chapter_ids = set()
    for c in data['contradictions']:
        chapter_ids.add(c['chapter1_id'])
        chapter_ids.add(c['chapter2_id'])
    
    print("Unique Chapter IDs found:")
    print("="*80)
    
    # Parse and display chapter information
    chapter_info = defaultdict(list)
    
    for cid in sorted(chapter_ids):
        parts = cid.split('_')
        if len(parts) >= 3:
            pdf_name = parts[0]
            chapter_title = '_'.join(parts[1:-1])  # Everything except first and last
            hash_id = parts[-1]
            
            chapter_info[pdf_name].append({
                'title': chapter_title,
                'hash': hash_id,
                'full_id': cid
            })
            
            print(f"\nID: {cid}")
            print(f"  PDF: {pdf_name}")
            print(f"  Chapter: {chapter_title}")
            print(f"  Hash: {hash_id}")
    
    print("\n" + "="*80)
    print("Summary by PDF:")
    print("="*80)
    
    for pdf, chapters in chapter_info.items():
        print(f"\n{pdf}:")
        unique_titles = set(ch['title'] for ch in chapters)
        for title in sorted(unique_titles):
            count = sum(1 for ch in chapters if ch['title'] == title)
            print(f"  - {title} ({count} section(s))")

if __name__ == "__main__":
    analyze_chapters() 