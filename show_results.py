#!/usr/bin/env python3
"""
Display contradiction detection results in a readable format and generate markdown report
"""

import json
import os
from datetime import datetime
from colorama import init, Fore, Style

init()

def generate_markdown_report(data, output_file="contradictions_detailed_report.md"):
    """Generate a detailed markdown report from the results"""
    
    total = len(data.get('contradictions', []))
    
    with open(output_file, 'w', encoding='utf-8') as f:
        # Header
        f.write(f"# 📚 PDF 모순 검사 상세 보고서\n\n")
        f.write(f"**생성 일시**: {datetime.now().strftime('%Y년 %m월 %d일 %H:%M:%S')}\n\n")
        f.write(f"**검사 파일**: {', '.join(data.get('files', ['Unknown']))}\n\n")
        f.write(f"---\n\n")
        
        # Summary
        f.write(f"## 📊 요약\n\n")
        f.write(f"- **발견된 총 모순 개수**: {total}개\n")
        
        if total == 0:
            f.write("\n✅ 검사 결과 모순이 발견되지 않았습니다.\n")
            return
        
        # Type summary
        by_type = {}
        type_map = {
            'definition': '정의',
            'recommendation': '권장사항',
            'fact': '사실',
            'principle': '원칙'
        }
        
        for c in data['contradictions']:
            by_type.setdefault(c['type'], 0)
            by_type[c['type']] += 1
        
        f.write("\n### 유형별 분포\n\n")
        for t, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            type_kr = type_map.get(t, t)
            f.write(f"- **{type_kr}**: {count}개\n")
        
        f.write(f"\n---\n\n")
        
        # Detailed contradictions
        f.write(f"## 🔍 상세 모순 내용\n\n")
        
        # Group by chapter pairs
        chapter_pairs = {}
        for c in data['contradictions']:
            # Extract clean chapter names
            ch1_parts = c['doc1_id'].split('_')
            ch2_parts = c['doc2_id'].split('_')
            
            # Get main chapter and section info
            if len(ch1_parts) >= 3:
                ch1_main = ch1_parts[1].replace('.', '. ')
                ch1_section = ch1_parts[-2] if ch1_parts[-2].isdigit() else ""
                ch1 = f"{ch1_main}" + (f" (Section {ch1_section})" if ch1_section else "")
            else:
                ch1 = ' '.join(ch1_parts[1:-1])
                
            if len(ch2_parts) >= 3:
                ch2_main = ch2_parts[1].replace('.', '. ')
                ch2_section = ch2_parts[-2] if ch2_parts[-2].isdigit() else ""
                ch2 = f"{ch2_main}" + (f" (Section {ch2_section})" if ch2_section else "")
            else:
                ch2 = ' '.join(ch2_parts[1:-1])
            
            pair_key = f"{ch1} <-> {ch2}"
            if pair_key not in chapter_pairs:
                chapter_pairs[pair_key] = []
            chapter_pairs[pair_key].append(c)
        
        # Write each contradiction
        for pair, contradictions in chapter_pairs.items():
            f.write(f"### 📑 {pair}\n\n")
            f.write(f"*발견된 모순: {len(contradictions)}개*\n\n")
            
            for i, c in enumerate(contradictions, 1):
                type_kr = type_map.get(c['type'], c['type'])
                
                f.write(f"#### 모순 {i}\n\n")
                f.write(f"- **유형**: {type_kr}\n")
                f.write(f"- **신뢰도**: {c['confidence']:.2f}\n\n")
                
                f.write(f"**첫 번째 문서 발췌:**\n")
                f.write(f"> {c['doc1_excerpt']}\n\n")
                
                f.write(f"**두 번째 문서 발췌:**\n")
                f.write(f"> {c['doc2_excerpt']}\n\n")
                
                f.write(f"**분석:**\n")
                f.write(f"{c['explanation']}\n\n")
                
                f.write(f"---\n\n")
        
        # Footer
        f.write(f"## 🎯 결론\n\n")
        f.write(f"총 {total}개의 모순이 발견되었습니다. ")
        
        # Find highest confidence contradiction
        if data['contradictions']:
            highest_conf = max(data['contradictions'], key=lambda x: x['confidence'])
            f.write(f"가장 신뢰도가 높은 모순은 {highest_conf['confidence']:.2f}의 신뢰도를 보였습니다.\n\n")
        
        f.write(f"각 모순에 대해 추가적인 검토와 수정이 필요할 수 있습니다.\n")
    
    print(f"\n{Fore.GREEN}✅ 마크다운 보고서가 생성되었습니다: {output_file}{Style.RESET_ALL}")

def show_results():
    """Display the contradiction results"""
    
    # Check for interim results first, then final results
    result_file = None
    if os.path.exists("contradictions_interim.json"):
        result_file = "contradictions_interim.json"
        print(f"{Fore.YELLOW}Showing interim results (processing may still be ongoing)...{Style.RESET_ALL}\n")
    elif os.path.exists("contradictions.json"):
        result_file = "contradictions.json"
        print(f"{Fore.GREEN}Showing final results...{Style.RESET_ALL}\n")
    else:
        print(f"{Fore.RED}No results found. Please run the PDF checker first.{Style.RESET_ALL}")
        return
    
    try:
        with open(result_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
        
        # Generate markdown report
        generate_markdown_report(data)
        
        total = len(data.get('contradictions', []))
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}발견된 총 모순 개수: {total}개{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}\n")
        
        if total == 0:
            print("No contradictions detected.")
            return
        
        # Group by chapter pairs
        chapter_pairs = {}
        for c in data['contradictions']:
            # Extract clean chapter names
            ch1_parts = c['doc1_id'].split('_')
            ch2_parts = c['doc2_id'].split('_')
            
            # Get main chapter and section info
            if len(ch1_parts) >= 3:
                ch1_main = ch1_parts[1].replace('.', '. ')
                ch1_section = ch1_parts[-2] if ch1_parts[-2].isdigit() else ""
                ch1 = f"{ch1_main}" + (f" (Section {ch1_section})" if ch1_section else "")
            else:
                ch1 = ' '.join(ch1_parts[1:-1])
                
            if len(ch2_parts) >= 3:
                ch2_main = ch2_parts[1].replace('.', '. ')
                ch2_section = ch2_parts[-2] if ch2_parts[-2].isdigit() else ""
                ch2 = f"{ch2_main}" + (f" (Section {ch2_section})" if ch2_section else "")
            else:
                ch2 = ' '.join(ch2_parts[1:-1])
            
            pair_key = f"{ch1} <-> {ch2}"
            if pair_key not in chapter_pairs:
                chapter_pairs[pair_key] = []
            chapter_pairs[pair_key].append(c)
        
        # Display by chapter pairs
        for pair, contradictions in chapter_pairs.items():
            print(f"\n{Fore.YELLOW}═══ {pair} ({len(contradictions)} contradiction(s)) ═══{Style.RESET_ALL}\n")
            
            for i, c in enumerate(contradictions, 1):
                # Type mapping to Korean
                type_map = {
                    'definition': '정의',
                    'recommendation': '권장사항',
                    'fact': '사실',
                    'principle': '원칙'
                }
                type_kr = type_map.get(c['type'], c['type'])
                
                print(f"{Fore.GREEN}모순 {i}:{Style.RESET_ALL}")
                print(f"  유형: {Fore.MAGENTA}{type_kr} ({c['type']}){Style.RESET_ALL}")
                print(f"  신뢰도: {Fore.CYAN}{c['confidence']:.2f}{Style.RESET_ALL}")
                print(f"\n  {Fore.WHITE}첫 번째 문서 발췌:{Style.RESET_ALL}")
                print(f"  \"{c['doc1_excerpt'][:200]}...\"")
                print(f"\n  {Fore.WHITE}두 번째 문서 발췌:{Style.RESET_ALL}")
                print(f"  \"{c['doc2_excerpt'][:200]}...\"")
                print(f"\n  {Fore.RED}설명:{Style.RESET_ALL}")
                print(f"  {c['explanation']}")
                print(f"\n  {'-'*70}\n")
        
        # Summary by type
        print(f"\n{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        print(f"{Fore.CYAN}유형별 요약:{Style.RESET_ALL}")
        print(f"{Fore.CYAN}{'='*80}{Style.RESET_ALL}")
        
        by_type = {}
        type_map = {
            'definition': '정의',
            'recommendation': '권장사항',
            'fact': '사실',
            'principle': '원칙'
        }
        
        for c in data['contradictions']:
            by_type.setdefault(c['type'], 0)
            by_type[c['type']] += 1
        
        for t, count in sorted(by_type.items(), key=lambda x: x[1], reverse=True):
            type_kr = type_map.get(t, t)
            print(f"  {type_kr}: {count}개")
            
    except json.JSONDecodeError:
        print(f"{Fore.RED}Error reading JSON file. It may be corrupted or being written.{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}Error: {e}{Style.RESET_ALL}")

if __name__ == "__main__":
    show_results() 