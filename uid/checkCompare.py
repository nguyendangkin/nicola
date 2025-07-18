#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import argparse
from datetime import datetime
from pathlib import Path


class GameTranslationChecker:
    def __init__(self):
        self.total_files = 0
        self.ok_files = 0
        self.error_files = 0
        self.issues_found = []
        
    def parse_game_file(self, content):
        """Parse game file content - giống hệt logic JavaScript"""
        lines = content.split('\n')
        entries = []
        
        for i in range(len(lines)):
            line = lines[i].strip()
            if line.startswith('SelfId='):
                self_id = line[7:]  # substring(7)
                text_line = ""
                
                for j in range(i + 1, len(lines)):
                    if lines[j].strip().startswith('Text='):
                        text_line = lines[j].strip()[5:]  # substring(5)
                        break
                    if lines[j].strip().startswith('SelfId='):
                        break
                
                entries.append({
                    'selfId': self_id,
                    'text': text_line,
                    'lineNumber': i + 1
                })
        
        return entries
    
    def compare_files(self, original_content, translated_content):
        """So sánh 2 file content - giống hệt logic JavaScript"""
        try:
            original_entries = self.parse_game_file(original_content)
            translated_entries = self.parse_game_file(translated_content)
            
            issues = []
            changes = []
            
            original_ids = set(e['selfId'] for e in original_entries)
            translated_ids = set(e['selfId'] for e in translated_entries)
            
            # Find missing SelfIds
            for id in original_ids:
                if id not in translated_ids:
                    issues.append({
                        'type': 'missing',
                        'selfId': id,
                        'message': f'SelfId "{id}" bị thiếu trong bản dịch'
                    })
            
            # Find extra SelfIds
            for id in translated_ids:
                if id not in original_ids:
                    issues.append({
                        'type': 'extra',
                        'selfId': id,
                        'message': f'SelfId "{id}" được thêm vào bản dịch (không có trong gốc)'
                    })
            
            # Compare existing entries
            original_map = {e['selfId']: e for e in original_entries}
            translated_map = {e['selfId']: e for e in translated_entries}
            
            for id, original_entry in original_map.items():
                translated_entry = translated_map.get(id)
                if translated_entry:
                    # Check if SelfId was modified
                    if original_entry['selfId'] != translated_entry['selfId']:
                        issues.append({
                            'type': 'modified_id',
                            'selfId': id,
                            'message': f'SelfId bị thay đổi từ "{original_entry["selfId"]}" thành "{translated_entry["selfId"]}"'
                        })
                    
                    # Check for text changes
                    if original_entry['text'] != translated_entry['text']:
                        changes.append({
                            'selfId': id,
                            'original': original_entry['text'],
                            'translated': translated_entry['text']
                        })
                    
                    # Check for tag modifications
                    original_tags = re.findall(r'<[^>]+>', original_entry['text'])
                    translated_tags = re.findall(r'<[^>]+>', translated_entry['text'])
                    original_special_tags = re.findall(r'\{[^}]+\}', original_entry['text'])
                    translated_special_tags = re.findall(r'\{[^}]+\}', translated_entry['text'])
                    
                    if len(original_tags) != len(translated_tags):
                        issues.append({
                            'type': 'tag_count',
                            'selfId': id,
                            'message': f'Số lượng tag HTML thay đổi: {len(original_tags)} → {len(translated_tags)}'
                        })
                    
                    if len(original_special_tags) != len(translated_special_tags):
                        issues.append({
                            'type': 'special_tag_count',
                            'selfId': id,
                            'message': f'Số lượng special tag thay đổi: {len(original_special_tags)} → {len(translated_special_tags)}'
                        })
                    
                    game_tags_original = re.findall(r'<(KEY_WAIT|NO_INPUT|cf)>', original_entry['text'])
                    game_tags_translated = re.findall(r'<(KEY_WAIT|NO_INPUT|cf)>', translated_entry['text'])
                    
                    if len(game_tags_original) != len(game_tags_translated):
                        issues.append({
                            'type': 'game_tag',
                            'selfId': id,
                            'message': f'Game tag bị thay đổi: {", ".join([f"<{tag}>" for tag in game_tags_original])}'
                        })
            
            return {
                'issues': issues,
                'changes': changes,
                'totalOriginal': len(original_entries),
                'totalTranslated': len(translated_entries)
            }
            
        except Exception as error:
            return {
                'error': f'Lỗi: {str(error)}',
                'issues': [],
                'changes': []
            }
    
    def find_translation_pairs(self, directory):
        """Tìm các cặp file gốc và bản dịch"""
        directory = Path(directory)
        pairs = []
        
        # Tìm tất cả file .txt
        txt_files = list(directory.glob('*.txt'))
        
        for file in txt_files:
            if file.stem.endswith('_vi'):
                continue  # Skip translated files
            
            # Tìm file dịch tương ứng
            original_file = file
            translated_file = directory / f"{file.stem}_vi.txt"
            
            if translated_file.exists():
                pairs.append((original_file, translated_file))
        
        return pairs
    
    def check_file_pair(self, original_file, translated_file):
        """Check một cặp file"""
        try:
            # Đọc file gốc
            with open(original_file, 'r', encoding='utf-8') as f:
                original_content = f.read()
            
            # Đọc file dịch
            with open(translated_file, 'r', encoding='utf-8') as f:
                translated_content = f.read()
            
            # So sánh
            result = self.compare_files(original_content, translated_content)
            
            self.total_files += 1
            
            if 'error' in result:
                self.error_files += 1
                print(f"❌ ERRO: {original_file.name}")
                print(f"   {result['error']}")
                self.issues_found.append({
                    'file': original_file.name,
                    'type': 'error',
                    'message': result['error']
                })
                return False
            
            if len(result['issues']) > 0:
                self.error_files += 1
                print(f"⚠️  ISSUES: {original_file.name}")
                print(f"   Entries: {result['totalOriginal']} → {result['totalTranslated']}")
                print(f"   Vấn đề: {len(result['issues'])}, Đã dịch: {len(result['changes'])}")
                
                for issue in result['issues']:
                    print(f"   - {issue['selfId']}: {issue['message']}")
                
                self.issues_found.append({
                    'file': original_file.name,
                    'type': 'issues',
                    'issues': result['issues'],
                    'changes': result['changes'],
                    'totalOriginal': result['totalOriginal'],
                    'totalTranslated': result['totalTranslated']
                })
                return False
            else:
                self.ok_files += 1
                print(f"✅ OK: {original_file.name}")
                print(f"   Entries: {result['totalOriginal']} → {result['totalTranslated']}")
                print(f"   Đã dịch: {len(result['changes'])} entries")
                return True
                
        except Exception as e:
            self.error_files += 1
            print(f"❌ ERROR: {original_file.name}")
            print(f"   Không thể đọc file: {str(e)}")
            self.issues_found.append({
                'file': original_file.name,
                'type': 'read_error',
                'message': str(e)
            })
            return False
    
    def generate_report(self, output_file=None):
        """Tạo báo cáo chi tiết"""
        report = []
        report.append("=" * 80)
        report.append("GAME TRANSLATION CHECKER REPORT")
        report.append("=" * 80)
        report.append(f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append(f"Tổng files: {self.total_files}")
        report.append(f"Files OK: {self.ok_files}")
        report.append(f"Files có vấn đề: {self.error_files}")
        report.append("")
        
        if self.issues_found:
            report.append("CHI TIẾT CÁC VẤN ĐỀ:")
            report.append("-" * 40)
            
            for item in self.issues_found:
                report.append(f"\n📁 File: {item['file']}")
                
                if item['type'] == 'error':
                    report.append(f"   ❌ Lỗi: {item['message']}")
                elif item['type'] == 'read_error':
                    report.append(f"   ❌ Không đọc được file: {item['message']}")
                elif item['type'] == 'issues':
                    report.append(f"   📊 Entries: {item['totalOriginal']} → {item['totalTranslated']}")
                    report.append(f"   ⚠️  Vấn đề: {len(item['issues'])}")
                    report.append(f"   ✅ Đã dịch: {len(item['changes'])}")
                    
                    for issue in item['issues']:
                        report.append(f"      - {issue['selfId']}: {issue['message']}")
        
        report_text = '\n'.join(report)
        
        if output_file:
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(report_text)
            print(f"\n📄 Báo cáo đã được lưu: {output_file}")
        
        return report_text
    
    def run(self, directory, output_file=None, verbose=False):
        """Chạy tool check"""
        directory = Path(directory)
        
        if not directory.exists():
            print(f"❌ Thư mục không tồn tại: {directory}")
            return False
        
        print(f"🔍 Đang quét thư mục: {directory}")
        
        # Tìm các cặp file
        pairs = self.find_translation_pairs(directory)
        
        if not pairs:
            print("❌ Không tìm thấy cặp file nào (pattern: abc.txt + abc_vi.txt)")
            return False
        
        print(f"📋 Tìm thấy {len(pairs)} cặp file để kiểm tra")
        print("=" * 60)
        
        # Check từng cặp file
        for original_file, translated_file in pairs:
            if verbose:
                print(f"\n🔄 Checking: {original_file.name} <-> {translated_file.name}")
            
            self.check_file_pair(original_file, translated_file)
        
        # Tổng kết
        print("\n" + "=" * 60)
        print("📊 TỔNG KẾT:")
        print(f"   Total: {self.total_files} files")
        print(f"   ✅ OK: {self.ok_files} files")
        print(f"   ⚠️  Issues: {self.error_files} files")
        
        if self.error_files > 0:
            print(f"\n⚠️  {self.error_files} files có vấn đề cần xử lý!")
        else:
            print("\n🎉 Tất cả files đều OK!")
        
        # Tạo báo cáo
        if output_file or self.error_files > 0:
            if not output_file:
                output_file = f"translation_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            
            self.generate_report(output_file)
        
        return self.error_files == 0


def main():
    parser = argparse.ArgumentParser(
        description="Game Translation Checker - Batch mode",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Cách sử dụng:
  python checkCompare.py                      # Check thư mục hiện tại
  python checkCompare.py /path/to/directory   # Check thư mục cụ thể
  python checkCompare.py -o report.txt        # Check thư mục hiện tại, lưu báo cáo
  python checkCompare.py -v                   # Check với log chi tiết
  
Cấu trúc file:
  abc.txt        (file gốc)
  abc_vi.txt     (file dịch)
  def.txt        (file gốc)
  def_vi.txt     (file dịch)
        """
    )
    
    parser.add_argument('directory', 
                       nargs='?',
                       default='.',
                       help='Thư mục chứa các file cần check (mặc định: thư mục hiện tại)')
    parser.add_argument('-o', '--output', 
                       help='File báo cáo output (tự động tạo nếu có lỗi)')
    parser.add_argument('-v', '--verbose', 
                       action='store_true',
                       help='Hiển thị log chi tiết')
    
    args = parser.parse_args()
    
    checker = GameTranslationChecker()
    
    try:
        success = checker.run(args.directory, args.output, args.verbose)
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Dừng bởi người dùng")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Lỗi không mong muốn: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()