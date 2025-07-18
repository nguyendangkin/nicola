import os
import time
import google.generativeai as genai
from pathlib import Path

# ============= CONFIG =============
API_KEY = ""   # 🔑 Dán API key của bạn vào đây
MODEL = "gemini-1.5-flash"      # hoặc "gemini-1.5-pro" nếu cần chất lượng cao
OUTPUT_DIR = "tran_vi"          # thư mục chứa file dịch
DELAY = 2                       # thời gian chờ giữa các request
PROMPT = (
    "Việt hóa phần Text của file script này sang tiếng việt. "
    "Giữ nguyên cấu trúc file."
    "Chỉ trả về văn bản dịch, không thêm giải thích."
)
# ===================================

# Cấu hình Gemini
genai.configure(api_key=API_KEY)
model = genai.GenerativeModel(MODEL)

def translate_text(text: str) -> str:
    """Gửi yêu cầu dịch sang Gemini API"""
    response = model.generate_content(f"{PROMPT}\n\n{text}")
    return response.text.strip()

def main():
    root = Path(__file__).resolve().parent
    out_dir = root / OUTPUT_DIR
    out_dir.mkdir(exist_ok=True)

    txt_files = [f for f in root.iterdir() if f.suffix == ".txt"]
    if not txt_files:
        print("Không tìm thấy file .txt trong thư mục.")
        return

    print(f"Tìm thấy {len(txt_files)} file. Bắt đầu dịch...\n")

    for f in txt_files:
        print(f"→ Dịch: {f.name}")
        with open(f, "r", encoding="utf-8", errors="replace") as infile:
            content = infile.read()

        try:
            result = translate_text(content)
            out_path = out_dir / (f.stem + "_vi" + f.suffix)
            with open(out_path, "w", encoding="utf-8") as outfile:
                outfile.write(result)
            print(f"  ✓ Ghi: {out_path.name}")
        except Exception as e:
            print(f"  ✗ Lỗi: {e}")

        time.sleep(DELAY)

    print("\n✅ Hoàn tất dịch tất cả file.")

if __name__ == "__main__":
    main()
