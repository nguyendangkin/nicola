import tkinter as tk
from tkinter import scrolledtext, messagebox, simpledialog
import re
from collections import Counter

# --- Regex ---
TAG_RE = re.compile(r"<([^>]+)>")
VAR_RE = re.compile(r"\{[^}]+\}")

# ----------------------------
# Extraction helpers
# ----------------------------
def normalize_tag(tag: str) -> str:
    """Bỏ tham số trong dấu ngoặc: IfGender_ACTOR(him,her,it) -> IfGender_ACTOR."""
    return tag.split("(", 1)[0].strip()

def extract_tags(text: str):
    """
    Trả về danh sách các tuple (tag_name, param_count).
    Ví dụ: '<IfGender_ACTOR(him,her,it)>' -> ('IfGender_ACTOR', 3)
    """
    tags = TAG_RE.findall(text)
    result = []
    for tag in tags:
        tag_name = normalize_tag(tag)
        # Đếm số lượng tham số nếu có dấu ngoặc
        if "(" in tag and ")" in tag:
            params = tag[tag.find("(")+1:tag.rfind(")")].strip()
            param_count = len([p for p in params.split(",") if p.strip()]) if params else 0
        else:
            param_count = 0
        result.append((tag_name, param_count))
    return result

def extract_vars(text: str):
    return VAR_RE.findall(text)

# ----------------------------
# Block splitting
# ----------------------------
def split_blocks(lines):
    """
    Return {key: [(global_idx, line_text), ...]}.
    Keys là dòng bắt đầu bằng 'Txt_' (strip).
    Các dòng nội dung theo sau đến key kế tiếp.
    """
    blocks = {}
    current_key = None
    for idx, raw in enumerate(lines):
        line = raw.rstrip("\n")
        stripped = line.strip()
        if stripped.startswith("Txt_"):
            current_key = stripped
            blocks[current_key] = []
        else:
            if current_key is not None:
                blocks[current_key].append((idx, line))
    return blocks

# ----------------------------
# Error structure
# ----------------------------
# Mỗi lỗi mình lưu dict:
# {
#   'msg': str hiển thị,
#   'key': str,
#   'block_line': int (1-based trong block) or None,
#   'orig_line': int (0-based global trong text widget),
#   'trans_line': int (0-based) or None nếu thiếu,
# }

def _add_error(result_list, msg, key, block_line, orig_line, trans_line):
    result_list.append({
        "msg": msg,
        "key": key,
        "block_line": block_line,
        "orig_line": orig_line,
        "trans_line": trans_line,
    })

# ----------------------------
# Compare routines
# ----------------------------
def compare_block(key, o_block, t_block, errors):
    """
    Compare two blocks (list of tuples (global_idx, line_text)).
    Append structured errors to `errors`.
    """
    len_o = len(o_block)
    len_t = len(t_block)

    if len_o != len_t:
        if len_o > len_t:
            _add_error(
                errors,
                f"[{key}] Thiếu {len_o - len_t} dòng trong bản dịch (gốc: {len_o}, dịch: {len_t}).",
                key, None, None, None
            )
        else:
            _add_error(
                errors,
                f"[{key}] Dư {len_t - len_o} dòng trong bản dịch (gốc: {len_o}, dịch: {len_t}).",
                key, None, None, None
            )

    max_len = max(len_o, len_t)
    for idx in range(max_len):
        block_line_num = idx + 1
        if idx < len_o:
            o_global_idx, o_text = o_block[idx]
            o_stripped = o_text.strip()
        else:
            # gốc hết; dịch dư -> đã cảnh báo ở trên; bỏ qua chi tiết.
            continue

        if idx < len_t:
            t_global_idx, t_text = t_block[idx]
            t_stripped = t_text.strip()
        else:
            # Thiếu dòng dịch
            snippet = o_stripped[:60]
            _add_error(
                errors,
                f"[{key}, dòng {block_line_num}] Thiếu dòng dịch. Gốc: {snippet}",
                key, block_line_num, o_global_idx, None
            )
            continue

        # gốc có nội dung mà dịch trống
        if o_stripped and not t_stripped:
            _add_error(
                errors,
                f"[{key}, dòng {block_line_num}] Dòng dịch trống nhưng gốc có nội dung.",
                key, block_line_num, o_global_idx, t_global_idx
            )
            continue

        # Tag / var compare
        o_tags = Counter(extract_tags(o_stripped))
        t_tags = Counter(extract_tags(t_stripped))
        o_vars = Counter(extract_vars(o_stripped))
        t_vars = Counter(extract_vars(t_stripped))

        miss_tags = list((o_tags - t_tags).elements())
        miss_vars = list((o_vars - t_vars).elements())
        extra_tags = list((t_tags - o_tags).elements())
        extra_vars = list((t_vars - o_vars).elements())

        # Kiểm tra số lượng tham số cho các tag giống nhau
        tag_param_errors = []
        for (tag_name, o_count) in o_tags:
            if (tag_name, o_count) in t_tags:
                t_count = next(count for t_name, count in t_tags if t_name == tag_name)
                if o_count != t_count:
                    tag_param_errors.append(f"Tag {tag_name}: Gốc có {o_count} tham số, dịch có {t_count} tham số")

        if miss_tags or miss_vars or extra_tags or extra_vars or tag_param_errors:
            parts = [f"[{key}, dòng {block_line_num}]"]
            if miss_tags:
                parts.append("Thiếu tag: " + ", ".join(t[0] for t in miss_tags))
            if miss_vars:
                parts.append("Thiếu biến: " + ", ".join(miss_vars))
            if extra_tags:
                parts.append("Dư tag: " + ", ".join(t[0] for t in extra_tags))
            if extra_vars:
                parts.append("Dư biến: " + ", ".join(extra_vars))
            if tag_param_errors:
                parts.extend(tag_param_errors)
            _add_error(
                errors,
                "  ".join(parts),
                key, block_line_num, o_global_idx, t_global_idx
            )

def compare_plain(o_lines, t_lines, errors):
    """So sánh toàn văn khi không có key Txt_"""
    o_block = list(enumerate(o_lines))
    t_block = list(enumerate(t_lines))
    compare_block("TOÀN VĂN", o_block, t_block, errors)


# ----------------------------
# Highlight helpers
# ----------------------------
ERROR_TAG_PREFIX = "ERR_"
ERROR_TAG_TRANS_PREFIX = "ERRT_"

def clear_highlights():
    # remove all tags we've added
    for tag in txt_original.tag_names():
        if tag.startswith(ERROR_TAG_PREFIX):
            txt_original.tag_delete(tag)
    for tag in txt_translated.tag_names():
        if tag.startswith(ERROR_TAG_TRANS_PREFIX):
            txt_translated.tag_delete(tag)

def highlight_line(widget, tag, line_index, bgcolor):
    """
    Highlight 0-based line_index in given Text widget.
    """
    # widget lines start at 1.0
    start = f"{line_index + 1}.0"
    end = f"{line_index + 1}.0 lineend"
    widget.tag_add(tag, start, end)
    widget.tag_config(tag, background=bgcolor)

def jump_to_line(widget, line_index):
    widget.see(f"{line_index + 1}.0")
    # also put insert cursor there (optional)
    widget.mark_set("insert", f"{line_index + 1}.0")
    widget.focus_set()

# We'll keep a list of error data after each check so click handlers can use it.
error_data = []

# ----------------------------
# Find & Replace functionality
# ----------------------------
class FindReplaceDialog:
    def __init__(self, parent, text_widget):
        self.parent = parent
        self.text_widget = text_widget
        self.dialog = None
        self.find_text = ""
        self.replace_text = ""
        self.last_pos = "1.0"
        
    def show(self):
        if self.dialog:
            self.dialog.lift()
            return
            
        self.dialog = tk.Toplevel(self.parent)
        self.dialog.title("Tìm & Thay thế")
        self.dialog.geometry("400x200")
        self.dialog.resizable(False, False)
        
        # Find entry
        tk.Label(self.dialog, text="Tìm:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.find_entry = tk.Entry(self.dialog, width=30)
        self.find_entry.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self.find_entry.insert(0, self.find_text)
        
        # Replace entry
        tk.Label(self.dialog, text="Thay thế:").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.replace_entry = tk.Entry(self.dialog, width=30)
        self.replace_entry.grid(row=1, column=1, padx=5, pady=5, sticky="ew")
        self.replace_entry.insert(0, self.replace_text)
        
        # Buttons frame
        btn_frame = tk.Frame(self.dialog)
        btn_frame.grid(row=2, column=0, columnspan=2, pady=10)
        
        tk.Button(btn_frame, text="Tìm tiếp", command=self.find_next).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Thay thế", command=self.replace_current).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Thay thế tất cả", command=self.replace_all).pack(side=tk.LEFT, padx=5)
        tk.Button(btn_frame, text="Đóng", command=self.close).pack(side=tk.LEFT, padx=5)
        
        # Make dialog modal
        self.dialog.transient(self.parent)
        self.dialog.grab_set()
        self.find_entry.focus_set()
        
        # Bind events
        self.find_entry.bind('<Return>', lambda e: self.find_next())
        self.replace_entry.bind('<Return>', lambda e: self.replace_current())
        self.dialog.protocol("WM_DELETE_WINDOW", self.close)
        
    def find_next(self):
        self.find_text = self.find_entry.get()
        if not self.find_text:
            return
            
        # Clear previous selection and highlight
        self.text_widget.tag_remove("sel", "1.0", tk.END)
        self.text_widget.tag_remove("find_highlight", "1.0", tk.END)
        
        # Search from current position
        pos = self.text_widget.search(self.find_text, self.last_pos, tk.END)
        if pos:
            # Calculate end position
            end_pos = f"{pos}+{len(self.find_text)}c"
            
            # Select found text
            self.text_widget.tag_add("sel", pos, end_pos)
            
            # Add highlight with yellow background
            self.text_widget.tag_add("find_highlight", pos, end_pos)
            self.text_widget.tag_config("find_highlight", background="#ffff00", foreground="#000000")
            
            # Jump to found text and focus
            self.text_widget.mark_set("insert", pos)
            self.text_widget.see(pos)
            self.text_widget.focus_set()
            
            # Update last position for next search
            self.last_pos = end_pos
        else:
            # Search from beginning
            pos = self.text_widget.search(self.find_text, "1.0", tk.END)
            if pos:
                end_pos = f"{pos}+{len(self.find_text)}c"
                
                # Select found text
                self.text_widget.tag_add("sel", pos, end_pos)
                
                # Add highlight with yellow background
                self.text_widget.tag_add("find_highlight", pos, end_pos)
                self.text_widget.tag_config("find_highlight", background="#ffff00", foreground="#000000")
                
                # Jump to found text and focus
                self.text_widget.mark_set("insert", pos)
                self.text_widget.see(pos)
                self.text_widget.focus_set()
                
                self.last_pos = end_pos
            else:
                messagebox.showinfo("Không tìm thấy", f"Không tìm thấy: {self.find_text}")
                self.last_pos = "1.0"
    
    def replace_current(self):
        self.find_text = self.find_entry.get()
        self.replace_text = self.replace_entry.get()
        
        if not self.find_text:
            return
            
        # Check if there's a selection
        try:
            sel_start = self.text_widget.index("sel.first")
            sel_end = self.text_widget.index("sel.last")
            selected_text = self.text_widget.get(sel_start, sel_end)
            
            if selected_text == self.find_text:
                # Clear highlight before replacing
                self.text_widget.tag_remove("find_highlight", "1.0", tk.END)
                
                self.text_widget.delete(sel_start, sel_end)
                self.text_widget.insert(sel_start, self.replace_text)
                self.last_pos = f"{sel_start}+{len(self.replace_text)}c"
                # Find next occurrence
                self.find_next()
            else:
                # No matching selection, just find next
                self.find_next()
        except tk.TclError:
            # No selection, just find next
            self.find_next()
    
    def replace_all(self):
        self.find_text = self.find_entry.get()
        self.replace_text = self.replace_entry.get()
        
        if not self.find_text:
            return
            
        # Clear highlights
        self.text_widget.tag_remove("find_highlight", "1.0", tk.END)
        
        content = self.text_widget.get("1.0", tk.END)
        count = content.count(self.find_text)
        
        if count > 0:
            new_content = content.replace(self.find_text, self.replace_text)
            self.text_widget.delete("1.0", tk.END)
            self.text_widget.insert("1.0", new_content)
            messagebox.showinfo("Thay thế hoàn tất", f"Đã thay thế {count} lần xuất hiện")
        else:
            messagebox.showinfo("Không tìm thấy", f"Không tìm thấy: {self.find_text}")
        
        self.last_pos = "1.0"
    
    def close(self):
        # Clear highlights when closing
        self.text_widget.tag_remove("find_highlight", "1.0", tk.END)
        self.dialog.destroy()
        self.dialog = None

# ----------------------------
# Copy log functionality
# ----------------------------
def copy_error_log():
    """Copy all error messages to clipboard"""
    if not error_data:
        root.clipboard_clear()
        root.clipboard_append("OK! Không phát hiện thiếu dòng/tag/biến.")
        messagebox.showinfo("Đã copy", "Đã copy log lỗi vào clipboard!")
        return
    
    # Create formatted error log
    log_text = "=== LOG LỖI DỊCH THUẬT ===\n\n"
    for i, error in enumerate(error_data, 1):
        log_text += f"{i}. {error['msg']}\n"
    
    log_text += f"\n=== TỔNG CỘNG: {len(error_data)} LỖI ==="
    
    # Copy to clipboard
    root.clipboard_clear()
    root.clipboard_append(log_text)
    messagebox.showinfo("Đã copy", f"Đã copy {len(error_data)} lỗi vào clipboard!")

# ----------------------------
# Setup text widget with unlimited undo/redo
# ----------------------------
def setup_text_widget(widget):
    """Setup unlimited undo/redo and find/replace for text widget"""
    # Enable undo with unlimited stack (maxundo=0 means unlimited)
    widget.config(undo=True, maxundo=0)
    
    # Create find/replace dialog instance
    find_dialog = FindReplaceDialog(root, widget)
    
    # Bind keyboard shortcuts with error handling
    def safe_undo(event):
        try:
            widget.edit_undo()
        except tk.TclError:
            # Silently ignore if nothing to undo
            pass
        return "break"  # Prevent default behavior
    
    def safe_redo(event):
        try:
            widget.edit_redo()
        except tk.TclError:
            # Silently ignore if nothing to redo
            pass
        return "break"  # Prevent default behavior
    
    widget.bind('<Control-z>', safe_undo)
    widget.bind('<Control-y>', safe_redo)
    
    # Bind Ctrl+H and prevent default behavior (backspace)
    def open_find_dialog(event):
        find_dialog.show()
        return "break"  # Prevent default behavior
    
    widget.bind('<Control-h>', open_find_dialog)
    widget.bind('<Control-H>', open_find_dialog)  # Uppercase H
    
    return find_dialog

# ----------------------------
# Main check callback
# ----------------------------
def check_translation():
    global error_data
    error_data = []

    original_text = txt_original.get("1.0", tk.END).rstrip("\n")
    translated_text = txt_translated.get("1.0", tk.END).rstrip("\n")

    if not original_text or not translated_text:
        messagebox.showwarning("Thiếu dữ liệu", "Hãy nhập cả hai nội dung để kiểm tra.")
        return

    orig_lines = original_text.splitlines()
    trans_lines = translated_text.splitlines()

    orig_blocks = split_blocks(orig_lines)
    trans_blocks = split_blocks(trans_lines)

    # collect errors
    if not orig_blocks and not trans_blocks:
        compare_plain(orig_lines, trans_lines, error_data)
    else:
        # missing / extra keys
        for key in orig_blocks:
            if key not in trans_blocks:
                _add_error(error_data, f"[Thiếu key] {key}", key, None, None, None)
        for key in trans_blocks:
            if key not in orig_blocks:
                _add_error(error_data, f"[Key dư] {key}", key, None, None, None)

        # compare shared keys
        for key, o_block in orig_blocks.items():
            if key not in trans_blocks:
                continue
            t_block = trans_blocks[key]
            compare_block(key, o_block, t_block, error_data)

    # Update error list UI
    refresh_error_list_ui()

    # Apply highlights
    apply_highlights()

def refresh_error_list_ui():
    lb_errors.delete(0, tk.END)
    if not error_data:
        lb_errors.insert(tk.END, "OK! Không phát hiện thiếu dòng/tag/biến.")
    else:
        for e in error_data:
            lb_errors.insert(tk.END, e["msg"])

def apply_highlights():
    clear_highlights()
    for idx, e in enumerate(error_data):
        if e["orig_line"] is not None:
            tag = f"{ERROR_TAG_PREFIX}{idx}"
            highlight_line(txt_original, tag, e["orig_line"], "#fff5b1")  # vàng nhạt
        if e["trans_line"] is not None:
            tag = f"{ERROR_TAG_TRANS_PREFIX}{idx}"
            highlight_line(txt_translated, tag, e["trans_line"], "#ffd6d6")  # hồng nhạt

# ----------------------------
# Click handler
# ----------------------------
def on_error_select(event):
    # which row?
    sel = lb_errors.curselection()
    if not sel:
        return
    idx = sel[0]
    if idx >= len(error_data):
        return  # maybe the OK line
    e = error_data[idx]

    if e["orig_line"] is not None:
        jump_to_line(txt_original, e["orig_line"])
    if e["trans_line"] is not None:
        jump_to_line(txt_translated, e["trans_line"])
    else:
        # thiếu dòng dịch -> cuộn cuối
        end_line = int(float(txt_translated.index("end-1c"))) - 1
        jump_to_line(txt_translated, max(end_line, 0))

def on_error_keypress(event):
    """Handle Ctrl+C on error listbox"""
    if event.state & 0x4 and event.keysym == 'c':  # Ctrl+C
        copy_error_log()

# ---------------- UI ----------------
root = tk.Tk()
root.title("So sánh Tag & Biến từng dòng - Enhanced")

# Columns expand
root.grid_columnconfigure(0, weight=1)
root.grid_columnconfigure(1, weight=1)
root.grid_rowconfigure(1, weight=1)

tk.Label(root, text="Bản gốc:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
tk.Label(root, text="Bản dịch:").grid(row=0, column=1, padx=10, pady=5, sticky="w")

txt_original = scrolledtext.ScrolledText(root, width=60, height=25, wrap="none")
txt_original.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
txt_translated = scrolledtext.ScrolledText(root, width=60, height=25, wrap="none")
txt_translated.grid(row=1, column=1, padx=10, pady=5, sticky="nsew")

# Setup text widgets with enhanced features
find_dialog_orig = setup_text_widget(txt_original)
find_dialog_trans = setup_text_widget(txt_translated)

# Buttons frame
btn_frame = tk.Frame(root)
btn_frame.grid(row=2, column=0, columnspan=2, pady=10)

btn_check = tk.Button(btn_frame, text="Kiểm tra", command=check_translation)
btn_check.pack(side=tk.LEFT, padx=5)

btn_copy = tk.Button(btn_frame, text="Copy Log Lỗi", command=copy_error_log)
btn_copy.pack(side=tk.LEFT, padx=5)

# Error list frame with label
error_frame = tk.Frame(root)
error_frame.grid(row=3, column=0, columnspan=2, padx=10, pady=(0,10), sticky="nsew")
root.grid_rowconfigure(3, weight=1)

tk.Label(error_frame, text="Danh sách lỗi (Click để nhảy đến dòng, Ctrl+C để copy):").pack(anchor="w")

# Danh sách lỗi click-được
lb_errors = tk.Listbox(error_frame, width=120, height=8)
lb_errors.pack(fill="both", expand=True)
lb_errors.bind("<<ListboxSelect>>", on_error_select)
lb_errors.bind("<KeyPress>", on_error_keypress)

# Status bar
status_frame = tk.Frame(root)
status_frame.grid(row=4, column=0, columnspan=2, sticky="ew", padx=10, pady=5)
status_label = tk.Label(status_frame, text="Sẵn sàng. Phím tắt: Ctrl+Z (Undo), Ctrl+Y (Redo), Ctrl+H (Find/Replace) - Undo/Redo không giới hạn", 
                       anchor="w", fg="gray")
status_label.pack(fill="x")

root.mainloop()