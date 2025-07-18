#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import sys
import time
import shutil
import logging
import argparse
from datetime import datetime
from pathlib import Path
from typing import List, Tuple, Dict, Any, Optional

# ===================== CONFIG =====================
API_KEY = "AIzaSyD-qEbaosppOcabeXFZ1TLauEbGhduAVk8"
MODEL = "gemini-1.5-flash"
RAW_DIR = "raw_file"
OUTPUT_DIR = "tran_vi"
END_DONE_DIR = "end_done"
DELAY = 2
MAX_RETRIES = 5
PROMPT = "Việt hóa nội dung Text trong file script này sang tiếng Việt, giữ nguyên cấu trúc, chỉ trả về nội dung dịch."
# ==================================================

try:
    import google.generativeai as genai
    GENAI_AVAILABLE = True
except ImportError:
    GENAI_AVAILABLE = False
    print("⚠️ Chưa cài google.generativeai. Chỉ chạy chế độ kiểm tra.")

# ===================== CHECK MODULE GIỮ NGUYÊN =====================


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
                    original_tags = re.findall(
                        r'<[^>]+>', original_entry['text'])
                    translated_tags = re.findall(
                        r'<[^>]+>', translated_entry['text'])
                    original_special_tags = re.findall(
                        r'\{[^}]+\}', original_entry['text'])
                    translated_special_tags = re.findall(
                        r'\{[^}]+\}', translated_entry['text'])

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

                    game_tags_original = re.findall(
                        r'<(KEY_WAIT|NO_INPUT|cf)>', original_entry['text'])
                    game_tags_translated = re.findall(
                        r'<(KEY_WAIT|NO_INPUT|cf)>', translated_entry['text'])

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
        report.append(
            f"Thời gian: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
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
                    report.append(
                        f"   ❌ Không đọc được file: {item['message']}")
                elif item['type'] == 'issues':
                    report.append(
                        f"   📊 Entries: {item['totalOriginal']} → {item['totalTranslated']}")
                    report.append(f"   ⚠️  Vấn đề: {len(item['issues'])}")
                    report.append(f"   ✅ Đã dịch: {len(item['changes'])}")

                    for issue in item['issues']:
                        report.append(
                            f"      - {issue['selfId']}: {issue['message']}")

        report_text = '\n'.join(report)

        with open(output_file, 'w', encoding='utf-8') as f:
            f.write(report_text)

        return report_text

# ===================== END CHECK MODULE ============================


class GameTranslator:
    """Dịch file game bằng Gemini API (đơn giản hóa)"""

    def __init__(self, api_key: str, model: str = MODEL):
        if not GENAI_AVAILABLE:
            raise ImportError("google.generativeai chưa được cài đặt")

        genai.configure(api_key=api_key)
        self.model = genai.GenerativeModel(model)

        # Logging
        logging.basicConfig(level=logging.INFO,
                            format="%(asctime)s - %(levelname)s - %(message)s",
                            handlers=[
                                logging.FileHandler(
                                    f"translation_{datetime.now():%Y%m%d_%H%M}.log", encoding="utf-8"),
                                logging.StreamHandler()
                            ])
        self.log = logging.getLogger("Translator")
        self.log.info(f"Khởi tạo dịch với model: {model}")

    def translate_text(self, original_text: str, previous_translation: str = None, issues: List[Dict[str, Any]] = None) -> str:
        """Tạo prompt dịch hoặc sửa lỗi"""
        if previous_translation and issues:
            issues_list = "\n".join(
                [f"- {i.get('selfId', '')}: {i.get('message', '')}" for i in issues])
            prompt = f"Sửa bản dịch dưới đây theo các vấn đề liệt kê. Giữ nguyên cấu trúc, tag:\n\nVẤN ĐỀ:\n{issues_list}\n\nBẢN DỊCH CŨ:\n{previous_translation}\n\nGỐC:\n{original_text}"
        else:
            prompt = f"{PROMPT}\n\n{original_text}"

        response = self.model.generate_content(prompt)
        return response.text.strip()

    def translate_file(self, input_file: Path, output_dir: Path, issues=None) -> Tuple[bool, str]:
        try:
            original_text = input_file.read_text(encoding="utf-8")
            output_file = output_dir / f"{input_file.stem}_vi.txt"
            prev_translation = output_file.read_text(
                encoding="utf-8") if issues and output_file.exists() else None

            translated_text = self.translate_text(
                original_text, prev_translation, issues)
            output_file.write_text(translated_text, encoding="utf-8")

            self.log.info(f"✓ Dịch xong: {input_file.name}")
            return True, str(output_file)
        except Exception as e:
            self.log.error(f"Lỗi dịch {input_file.name}: {e}")
            return False, str(e)

    def batch_translate(self, input_dir: Path, output_dir: Path, delay: int = DELAY) -> List[Tuple[Path, Path]]:
        output_dir.mkdir(exist_ok=True)
        files = [f for f in input_dir.glob(
            "*.txt") if not f.name.endswith("_vi.txt")]
        if not files:
            self.log.warning(f"Không có file nào trong {input_dir}")
            return []

        self.log.info(f"Phát hiện {len(files)} file cần dịch")
        pairs = []
        for f in files:
            success, result = self.translate_file(f, output_dir)
            if success:
                pairs.append((f, Path(result)))
            time.sleep(delay)
        return pairs


class GameTranslationTool:
    """Quy trình tổng hợp dịch + kiểm tra"""

    def __init__(self, api_key=None, model=MODEL):
        self.checker = GameTranslationChecker()
        self.translator = GameTranslator(api_key, model) if api_key else None
        self.log = logging.getLogger("Main")

    def translate_and_check(self, raw_dir=RAW_DIR, out_dir=OUTPUT_DIR, delay=DELAY):
        raw_path, out_path, done_path = Path(
            raw_dir), Path(out_dir), Path(END_DONE_DIR)
        done_path.mkdir(exist_ok=True)

        # Dịch
        if self.translator:
            pairs = self.translator.batch_translate(raw_path, out_path, delay)
        else:
            self.log.info("Chỉ kiểm tra vì không có API key.")
            pairs = [(f, out_path / f"{f.stem}_vi.txt") for f in raw_path.glob(
                "*.txt") if (out_path / f"{f.stem}_vi.txt").exists()]

        if not pairs:
            self.log.error("Không có file nào để kiểm tra.")
            return False

        # Kiểm tra + retry
        retry = 0
        while pairs and retry < MAX_RETRIES:
            self.log.info(f"--- Lần {retry+1}/{MAX_RETRIES} ---")
            next_round = []
            for orig, tran in pairs:
                ok, msg = self.checker.check_file_pair(orig, tran)
                if ok:
                    shutil.move(orig, done_path / orig.name)
                    shutil.move(tran, done_path / tran.name)
                    self.log.info(f"OK {orig.name}")
                else:
                    self.log.warning(f"Lỗi {orig.name}: {msg}")
                    if self.translator:
                        issues = next(
                            (i.get('issues') for i in self.checker.issues_found if i['file'] == orig.name), None)
                        success, result = self.translator.translate_file(
                            orig, out_path, issues)
                        if success:
                            next_round.append((orig, Path(result)))
            pairs = next_round
            retry += 1

        return len(pairs) == 0

    def check_only(self, raw_dir=RAW_DIR, out_dir=OUTPUT_DIR):
        raw_path, out_path = Path(raw_dir), Path(out_dir)
        pairs = [(f, out_path / f"{f.stem}_vi.txt") for f in raw_path.glob(
            "*.txt") if (out_path / f"{f.stem}_vi.txt").exists()]
        if not pairs:
            self.log.error("Không có cặp file nào để kiểm tra.")
            return False
        for orig, tran in pairs:
            ok, msg = self.checker.check_file_pair(orig, tran)
            self.log.info(f"{'OK' if ok else 'Lỗi'} {orig.name}: {msg}")
        return True


def main():
    parser = argparse.ArgumentParser(description="Game Translation Tool")
    parser.add_argument('--check-only', action='store_true',
                        help='Chỉ kiểm tra, không dịch')
    parser.add_argument('-k', '--api-key', default=API_KEY,
                        help='API key cho Gemini')
    parser.add_argument('-r', '--raw', default=RAW_DIR, help='Thư mục gốc')
    parser.add_argument('-o', '--out', default=OUTPUT_DIR, help='Thư mục dịch')
    parser.add_argument('--delay', type=int, default=DELAY,
                        help='Delay giữa các request')
    args = parser.parse_args()

    tool = GameTranslationTool(
        api_key=None if args.check_only else args.api_key)
    success = tool.check_only(args.raw, args.out) if args.check_only else tool.translate_and_check(
        args.raw, args.out, args.delay)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
