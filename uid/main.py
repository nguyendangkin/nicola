#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import re
import sys
import time
import shutil # Added for file operations
import argparse
import logging
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️  google.generativeai không được cài đặt. Chỉ chạy chế độ check.")

# ============= CONFIG =============
API_KEY = "AIzaSyD-qEbaosppOcabeXFZ1TLauEbGhduAVk8"   # 🔑 API key
MODEL = "gemini-1.5-flash"      # hoặc "gemini-1.5-pro"
RAW_DIR = "raw_file"            # thư mục chứa file gốc cần dịch
OUTPUT_DIR = "tran_vi"          # thư mục chứa file dịch
END_DONE_DIR = "end_done"       # thư mục chứa file đã dịch và kiểm tra thành công
DELAY = 2                       # thời gian chờ giữa các request
MAX_RETRIES = 10                 # Số lần thử lại tối đa cho các file có vấn đề
PROMPT = (
    "Việt hóa phần Text của file script này sang tiếng việt. "
    "Giữ nguyên cấu trúc file. "
    "Chỉ trả về văn bản dịch, không thêm giải thích."
)
# ===================================

class GameTranslationChecker:
    """Tool kiểm tra chất lượng bản dịch"""
    
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
        """So sánh 2 file content"""
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
                self.issues_found.append({
                    'file': original_file.name,
                    'type': 'error',
                    'message': result['error']
                })
                return False, result['error']
            
            if len(result['issues']) > 0:
                self.error_files += 1
                self.issues_found.append({
                    'file': original_file.name,
                    'type': 'issues',
                    'issues': result['issues'],
                    'changes': result['changes'],
                    'totalOriginal': result['totalOriginal'],
                    'totalTranslated': result['totalTranslated']
                })
                return False, f"{len(result['issues'])} vấn đề tìm thấy"
            else:
                self.ok_files += 1
                return True, f"OK - {len(result['changes'])} entries đã dịch"
                
        except Exception as e:
            self.error_files += 1
            self.issues_found.append({
                'file': original_file.name,
                'type': 'read_error',
                'message': str(e)
            })
            return False, f"Không thể đọc file: {str(e)}"
    
    def generate_report(self, output_file):
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
        
        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)
        
        return report_text


class GameTranslator:
    """Tool dịch game script sử dụng Gemini API"""
    
    def __init__(self, api_key: str, model: str = "gemini-1.5-flash"):
        if not GENAI_AVAILABLE:
            raise ImportError("google.generativeai không được cài đặt")
        
        self.api_key = api_key
        self.model_name = model
        self.setup_gemini()
        self.setup_logging()
        
    def setup_gemini(self):
        """Cấu hình Gemini API"""
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(self.model_name)
        
    def setup_logging(self):
        """Cấu hình logging"""
        log_filename = f"translation_log_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info(f"🚀 Khởi tạo GameTranslator - Model: {self.model_name}")
        
    def translate_text(self, text: str, issues: Optional[List[Dict[str, Any]]] = None) -> str:
        """Gửi yêu cầu dịch sang Gemini API, có thể kèm theo các vấn đề cần sửa"""
        full_prompt = PROMPT
        if issues:
            issue_details = "\n".join([f"- SelfId: {issue.get('selfId', 'N/A')}, Vấn đ: {issue.get('message', 'N/A')}" for issue in issues])
            full_prompt += (
                "\n\nLưu ý: Bản dịch trước đó có các vấn đề sau. "
                "Hãy sửa các vấn đề này trong bản dịch mới, "
                "đảm bảo giữ nguyên cấu trúc file và các tag đặc biệt:\n"
                f"{issue_details}"
            )
        
        try:
            response = self.model.generate_content(f"{full_prompt}\n\n{text}")
            return response.text.strip()
        except Exception as e:
            self.logger.error(f"Lỗi dịch: {str(e)}")
            raise
    
    def find_txt_files(self, directory: Path) -> List[Path]:
        """Tìm tất cả file .txt trong thư mục"""
        if not directory.exists():
            self.logger.warning(f"⚠️  Thư mục không tồn tại: {directory}")
            return []
        
        txt_files = [f for f in directory.iterdir() if f.suffix == ".txt" and not f.stem.endswith("_vi")]
        return txt_files
    
    def translate_file(self, input_file: Path, output_dir: Path, issues: Optional[List[Dict[str, Any]]] = None) -> Tuple[bool, str]:
        """Dịch một file, có thể kèm theo các vấn đề cần sửa"""
        try:
            self.logger.info(f"→ Bắt đầu dịch: {input_file.name}")
            
            # Đọc file gốc
            with open(input_file, "r", encoding="utf-8", errors="replace") as f:
                content = f.read()
            
            # Dịch nội dung
            result = self.translate_text(content, issues) # Pass issues to translate_text
            
            # Ghi file dịch
            output_file = output_dir / (input_file.stem + "_vi" + input_file.suffix)
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(result)
            
            self.logger.info(f"  ✓ Đã dịch: {output_file.name}")
            return True, str(output_file)
            
        except Exception as e:
            error_msg = f"Lỗi dịch {input_file.name}: {str(e)}"
            self.logger.error(error_msg)
            return False, error_msg
    
    def run_translation(self, raw_dir: str = RAW_DIR, output_dir: str = OUTPUT_DIR, delay: int = DELAY, working_dir: str = ".") -> Dict[str, Any]:
        """Chạy quá trình dịch toàn bộ"""
        root = Path(working_dir).resolve()
        raw_path = root / raw_dir
        out_dir = root / output_dir
        
        # Tạo thư mục output nếu chưa có
        out_dir.mkdir(exist_ok=True)
        
        self.logger.info(f"🔍 Thư mục gốc: {root}")
        self.logger.info(f"📂 Thư mục raw: {raw_path}")
        self.logger.info(f"📁 Thư mục đích: {out_dir}")
        
        # Tìm file .txt trong thư mục raw
        txt_files = self.find_txt_files(raw_path)
        if not txt_files:
            self.logger.warning(f"❌ Không tìm thấy file .txt nào trong {raw_path}")
            return {
                'success': False,
                'total_files': 0,
                'translated_files': 0,
                'failed_files': 0,
                'translated_pairs': [],
                'raw_dir': str(raw_path),
                'output_dir': str(out_dir)
            }
        
        self.logger.info(f"📋 Tìm thấy {len(txt_files)} file cần dịch")
        
        # Dịch từng file
        translated_pairs = []
        failed_files = 0
        
        for file_path in txt_files:
            success, result = self.translate_file(file_path, out_dir)
            
            if success:
                translated_pairs.append((file_path, Path(result)))
            else:
                failed_files += 1
            
            # Delay giữa các request
            if delay > 0:
                time.sleep(delay)
        
        # Tổng kết
        translated_files = len(translated_pairs)
        total_files = len(txt_files)
        
        self.logger.info("=" * 60)
        self.logger.info("📊 KẾT QUẢ DỊCH:")
        self.logger.info(f"   Total: {total_files} files")
        self.logger.info(f"   ✅ Dịch thành công: {translated_files} files")
        self.logger.info(f"   ❌ Dịch thất bại: {failed_files} files")
        
        return {
            'success': failed_files == 0,
            'total_files': total_files,
            'translated_files': translated_files,
            'failed_files': failed_files,
            'translated_pairs': translated_pairs,
            'raw_dir': str(raw_path),
            'output_dir': str(out_dir)
        }


class GameTranslationTool:
    """Tool tích hợp dịch + kiểm tra"""
    
    def __init__(self, api_key: str = None, model: str = MODEL):
        self.api_key = api_key
        self.model = model
        self.translator = None
        self.checker = GameTranslationChecker()
        
        # Setup logging
        self.setup_logging()
        
        # Khởi tạo translator nếu có API key
        if api_key and GENAI_AVAILABLE:
            try:
                self.translator = GameTranslator(api_key, model)
                self.logger.info("✅ Translator đã sẵn sàng")
            except Exception as e:
                self.logger.error(f"❌ Không thể khởi tạo translator: {str(e)}")
        else:
            self.logger.warning("⚠️  Chỉ chạy chế độ check (không có API key hoặc genai)")
    
    def setup_logging(self):
        """Cấu hình logging chung"""
        log_filename = f"game_translation_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler()
            ]
        )
        self.logger = logging.getLogger(__name__)
        self.logger.info("🚀 Khởi tạo GameTranslationTool")

    def _move_file_pair(self, original_file: Path, translated_file: Path, end_done_dir: Path):
        """Di chuyển cặp file gốc và file dịch sang thư mục end_done"""
        end_done_dir.mkdir(parents=True, exist_ok=True)
        try:
            shutil.move(str(original_file), end_done_dir / original_file.name)
            shutil.move(str(translated_file), end_done_dir / translated_file.name)
            self.logger.info(f"✅ Đã chuyển {original_file.name} và {translated_file.name} vào {end_done_dir.name}")
            return True
        except Exception as e:
            self.logger.error(f"❌ Lỗi khi di chuyển file {original_file.name} và {translated_file.name}: {str(e)}")
            return False
    
    def translate_and_check(self, working_dir: str = ".", raw_dir: str = RAW_DIR, output_dir: str = OUTPUT_DIR, delay: int = DELAY) -> bool:
        """Dịch và kiểm tra tự động"""
        self.logger.info("🎯 BẮT ĐẦU QUY TRÌNH DỊCH + KIỂM TRA")
        
        root = Path(working_dir).resolve()
        raw_path = root / raw_dir
        out_path = root / output_dir
        end_done_path = root / END_DONE_DIR # Define end_done_path

        # Ensure output and end_done directories exist
        out_path.mkdir(exist_ok=True)
        end_done_path.mkdir(exist_ok=True)

        initial_translated_pairs = []
        if self.translator:
            self.logger.info("📝 BƯỚC 1: DỊCH CÁC FILE")
            translation_result = self.translator.run_translation(raw_dir, output_dir, delay, working_dir)
            
            if not translation_result['success'] and translation_result['total_files'] > 0:
                self.logger.error("❌ Quá trình dịch ban đầu thất bại cho một số file.")
                # Continue to check what was translated, even if some failed
            
            initial_translated_pairs = translation_result['translated_pairs']
            raw_path = Path(translation_result['raw_dir'])
            out_path = Path(translation_result['output_dir'])
        else:
            self.logger.info("⚠️  Bỏ qua bước dịch - chỉ chạy kiểm tra")
            # Tìm các cặp file có sẵn
            for original_file in raw_path.glob("*.txt"):
                if original_file.stem.endswith("_vi"):
                    continue
                translated_file = out_path / (original_file.stem + "_vi.txt")
                if translated_file.exists():
                    initial_translated_pairs.append((original_file, translated_file))
        
        if not initial_translated_pairs:
            self.logger.error("❌ Không tìm thấy cặp file nào để kiểm tra")
            return False
        
        # Bước 2: Kiểm tra và xử lý vòng lặp
        self.logger.info("🔍 BƯỚC 2: KIỂM TRA CHẤT LƯỢNG VÀ XỬ LÝ VẤN Đ��")
        
        current_pairs_to_check = list(initial_translated_pairs)
        problematic_files_info = {}
        retry_count = 0
        overall_success = True

        while current_pairs_to_check and retry_count < MAX_RETRIES:
            self.logger.info(f"--- Lần kiểm tra/dịch lại thứ {retry_count + 1}/{MAX_RETRIES} ---")
            next_pairs_to_check = []
            self.checker = GameTranslationChecker() # Reset checker for each retry loop

            for original_file, translated_file in current_pairs_to_check:
                # Get issues from previous attempt if available
                issues_for_retranslation = problematic_files_info.get(original_file.name, {}).get('issues', None)

                # If this is a retry and translator is available, re-translate
                if retry_count > 0 and self.translator:
                    self.logger.info(f"🔄 Dịch lại file: {original_file.name} (lần {retry_count + 1})")
                    success_retran, new_translated_path_str = self.translator.translate_file(original_file, out_path, issues=issues_for_retranslation)
                    if success_retran:
                        translated_file = Path(new_translated_path_str)
                    else:
                        self.logger.error(f"❌ Dịch lại file {original_file.name} thất bại. Bỏ qua kiểm tra lần này.")
                        problematic_files_info[original_file.name] = {'issues': [{'type': 'retranslation_failed', 'message': 'Dịch lại thất bại'}]}
                        next_pairs_to_check.append((original_file, translated_file)) # Keep in problematic list
                        continue # Skip check if re-translation failed

                success, message = self.checker.check_file_pair(original_file, translated_file)
                
                if success:
                    self.logger.info(f"✅ {original_file.name}: {message}")
                    self._move_file_pair(original_file, translated_file, end_done_path)
                    # Remove from problematic_files_info if it was there
                    if original_file.name in problematic_files_info:
                        del problematic_files_info[original_file.name]
                else:
                    self.logger.warning(f"⚠️  {original_file.name}: {message}")
                    overall_success = False
                    next_pairs_to_check.append((original_file, translated_file))
                    # Store issues for next re-translation attempt
                    file_issues = next((item for item in self.checker.issues_found if item.get('file') == original_file.name), None)
                    if file_issues:
                        problematic_files_info[original_file.name] = file_issues

            current_pairs_to_check = next_pairs_to_check
            if current_pairs_to_check:
                self.logger.info(f"➡️  Còn {len(current_pairs_to_check)} file có vấn đề. Thử lại...")
            retry_count += 1

        # Final summary after all retries
        self.logger.info("=" * 60)
        self.logger.info("📊 TỔNG KẾT CUỐI CÙNG:")
        self.logger.info(f"   Total files processed: {self.checker.total_files}")
        self.logger.info(f"   ✅ OK and moved: {self.checker.ok_files} files")
        self.logger.info(f"   ⚠️  Still problematic: {len(problematic_files_info)} files")
        
        if problematic_files_info:
            self.logger.warning("❌ CÁC FILES SAU VẪN CÓ VẤN ĐỀ SAU NHIỀU LẦN THỬ LẠI:")
            for file_name, info in problematic_files_info.items():
                self.logger.warning(f"   - {file_name}: {info.get('message', 'Chi tiết trong báo cáo')}")
                if 'issues' in info:
                    for issue in info['issues']:
                        self.logger.warning(f"     -> {issue.get('selfId', 'N/A')}: {issue.get('message', 'N/A')}")
            overall_success = False
            
            # Generate a final report for remaining issues
            report_file = f"final_problem_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            # Temporarily set checker's issues_found to only problematic ones for report generation
            original_issues_found = self.checker.issues_found
            self.checker.issues_found = list(problematic_files_info.values())
            self.checker.generate_report(report_file)
            self.checker.issues_found = original_issues_found # Restore
            self.logger.info(f"📄 Báo cáo chi tiết các vấn đề còn lại: {report_file}")

        if overall_success:
            self.logger.info("🎉 TẤT CẢ FILES DỊCH THÀNH CÔNG VÀ KHÔNG CÓ VẤN ĐỀ SAU CÁC LẦN THỬ LẠI!")
        else:
            self.logger.warning("⚠️  MỘT SỐ FILES CÓ VẤN ĐỀ CẦN XEM XÉT SAU CÁC LẦN THỬ LẠI!")
        
        return overall_success
    
    def check_only(self, working_dir: str = ".", raw_dir: str = RAW_DIR, output_dir: str = OUTPUT_DIR) -> bool:
        """Chỉ chạy kiểm tra (không dịch)"""
        self.logger.info("🔍 CHẠY CHẾ ĐỘ KIỂM TRA")
        
        root = Path(working_dir).resolve()
        raw_path = root / raw_dir
        out_path = root / output_dir
        
        self.logger.info(f"🔍 Thư mục gốc: {root}")
        self.logger.info(f"📂 Thư mục raw: {raw_path}")
        self.logger.info(f"📁 Thư mục translated: {out_path}")
        
        # Tìm các cặp file
        pairs = []
        for original_file in raw_path.glob("*.txt"):
            if original_file.stem.endswith("_vi"):
                continue
            translated_file = out_path / (original_file.stem + "_vi.txt")
            if translated_file.exists():
                pairs.append((original_file, translated_file))
        
        if not pairs:
            self.logger.error(f"❌ Không tìm thấy cặp file nào để kiểm tra")
            self.logger.error(f"   Cấu trúc mong đợi:")
            self.logger.error(f"   {raw_path}/abc.txt -> {out_path}/abc_vi.txt")
            return False
        
        self.logger.info(f"📋 Tìm thấy {len(pairs)} cặp file")
        
        # Kiểm tra từng cặp
        all_ok = True
        for original_file, translated_file in pairs:
            success, message = self.checker.check_file_pair(original_file, translated_file)
            
            if success:
                self.logger.info(f"✅ {original_file.name}: {message}")
            else:
                self.logger.warning(f"⚠️  {original_file.name}: {message}")
                all_ok = False
        
        # Tổng kết
        self.logger.info("=" * 60)
        self.logger.info("📊 KẾT QUẢ KIỂM TRA:")
        self.logger.info(f"   Total: {self.checker.total_files} files")
        self.logger.info(f"   ✅ OK: {self.checker.ok_files} files")
        self.logger.info(f"   ⚠️  Issues: {self.checker.error_files} files")
        
        # Tạo báo cáo nếu có vấn đề
        if self.checker.error_files > 0:
            report_file = f"check_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.txt"
            self.checker.generate_report(report_file)
            self.logger.info(f"📄 Báo cáo chi tiết: {report_file}")
        
        return all_ok


def main():
    parser = argparse.ArgumentParser(
        description="Game Translation Tool - Dịch và kiểm tra tự động",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Cách sử dụng:
  python game_translation.py                     # Dịch + kiểm tra (raw_file -> tran_vi)
  python game_translation.py --check-only       # Chỉ kiểm tra (raw_file <-> tran_vi)
  python game_translation.py -d /path/to/dir    # Thư mục làm việc khác
  python game_translation.py -r input_files     # Thư mục raw khác
  python game_translation.py -o output_files    # Thư mục output khác
  python game_translation.py -k YOUR_API_KEY    # API key từ command line
  python game_translation.py --delay 3          # Delay 3 giây giữa các request

Cấu trúc thư mục:
  working_dir/
  ├── raw_file/           # File gốc cần dịch
  │   ├── abc.txt
  │   └── def.txt
  ├── tran_vi/            # File dịch (tự động tạo)
  │   ├── abc_vi.txt
  │   └── def_vi.txt
  └── game_translation.py
        """
    )
    
    parser.add_argument('-d', '--directory', 
                       default='.',
                       help='Thư mục làm việc chính (mặc định: thư mục hiện tại)')
    parser.add_argument('-r', '--raw-dir', 
                       default=RAW_DIR,
                       help=f'Thư mục chứa file gốc (mặc định: {RAW_DIR})')
    parser.add_argument('-o', '--output', 
                       default=OUTPUT_DIR,
                       help=f'Thư mục đích (mặc định: {OUTPUT_DIR})')
    parser.add_argument('-k', '--api-key', 
                       default=API_KEY,
                       help='API key cho Gemini')
    parser.add_argument('-m', '--model', 
                       default=MODEL,
                       help=f'Model Gemini (mặc định: {MODEL})')
    parser.add_argument('--delay', 
                       type=int, 
                       default=DELAY,
                       help=f'Delay giữa các request (giây, mặc định: {DELAY})')
    parser.add_argument('--check-only', 
                       action='store_true',
                       help='Chỉ chạy kiểm tra, không dịch')
    
    args = parser.parse_args()
    
    # Khởi tạo tool
    tool = GameTranslationTool(
        api_key=args.api_key if not args.check_only else None,
        model=args.model
    )
    
    try:
        if args.check_only:
            success = tool.check_only(args.directory, args.raw_dir, args.output)
        else:
            success = tool.translate_and_check(args.directory, args.raw_dir, args.output, args.delay)
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Dừng bởi người dùng")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Lỗi không mong muốn: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()