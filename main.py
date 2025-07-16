import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import difflib
import os

class FileComparator:
    def __init__(self, root):
        self.root = root
        self.root.title("File Comparison Tool - Kiểm tra sự khác biệt giữa 2 file")
        self.root.geometry("1200x800")
        
        # Variables
        self.file1_path = tk.StringVar()
        self.file2_path = tk.StringVar()
        self.file1_content = ""
        self.file2_content = ""
        
        self.setup_ui()
        
    def setup_ui(self):
        # Main frame
        main_frame = ttk.Frame(self.root, padding="10")
        main_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Input selection frame
        input_frame = ttk.LabelFrame(main_frame, text="Nhập nội dung để so sánh", padding="5")
        input_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        # Input method selection
        method_frame = ttk.Frame(input_frame)
        method_frame.grid(row=0, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.input_method = tk.StringVar(value="text")
        ttk.Radiobutton(method_frame, text="Nhập text trực tiếp", variable=self.input_method, 
                       value="text", command=self.toggle_input_method).pack(side=tk.LEFT, padx=(0, 20))
        ttk.Radiobutton(method_frame, text="Chọn từ file", variable=self.input_method, 
                       value="file", command=self.toggle_input_method).pack(side=tk.LEFT)
        
        # File selection (initially hidden)
        self.file_frame = ttk.Frame(input_frame)
        self.file_frame.grid(row=1, column=0, columnspan=3, sticky=(tk.W, tk.E), pady=(0, 10))
        
        ttk.Label(self.file_frame, text="File gốc (Original):").grid(row=0, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(self.file_frame, textvariable=self.file1_path, width=60).grid(row=0, column=1, padx=(5, 5), pady=(0, 5))
        ttk.Button(self.file_frame, text="Chọn file", command=self.select_file1).grid(row=0, column=2, pady=(0, 5))
        
        ttk.Label(self.file_frame, text="File đã dịch (Translated):").grid(row=1, column=0, sticky=tk.W, pady=(0, 5))
        ttk.Entry(self.file_frame, textvariable=self.file2_path, width=60).grid(row=1, column=1, padx=(5, 5), pady=(0, 5))
        ttk.Button(self.file_frame, text="Chọn file", command=self.select_file2).grid(row=1, column=2, pady=(0, 5))
        
        # Text input areas
        self.text_frame = ttk.Frame(input_frame)
        self.text_frame.grid(row=2, column=0, columnspan=3, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Left text input
        left_input_frame = ttk.LabelFrame(self.text_frame, text="Nội dung gốc (Original)", padding="5")
        left_input_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        self.input_text1 = scrolledtext.ScrolledText(left_input_frame, wrap=tk.WORD, width=50, height=10)
        self.input_text1.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right text input
        right_input_frame = ttk.LabelFrame(self.text_frame, text="Nội dung đã dịch (Translated)", padding="5")
        right_input_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        self.input_text2 = scrolledtext.ScrolledText(right_input_frame, wrap=tk.WORD, width=50, height=10)
        self.input_text2.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Configure text frame grid
        self.text_frame.columnconfigure(0, weight=1)
        self.text_frame.columnconfigure(1, weight=1)
        self.text_frame.rowconfigure(0, weight=1)
        left_input_frame.columnconfigure(0, weight=1)
        left_input_frame.rowconfigure(0, weight=1)
        right_input_frame.columnconfigure(0, weight=1)
        right_input_frame.rowconfigure(0, weight=1)
        
        # Configure input frame grid
        input_frame.columnconfigure(0, weight=1)
        input_frame.rowconfigure(2, weight=1)
        
        # Initially show text input
        self.toggle_input_method()
        
        # Buttons frame
        button_frame = ttk.Frame(main_frame)
        button_frame.grid(row=1, column=0, columnspan=2, pady=(0, 10))
        
        ttk.Button(button_frame, text="So sánh", command=self.compare_content).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Xóa tất cả", command=self.clear_all).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Xóa kết quả", command=self.clear_results).pack(side=tk.LEFT, padx=(0, 5))
        ttk.Button(button_frame, text="Lưu kết quả", command=self.save_results).pack(side=tk.LEFT)
        
        # Results frame
        results_frame = ttk.LabelFrame(main_frame, text="Kết quả so sánh", padding="5")
        results_frame.grid(row=2, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S), pady=(0, 10))
        
        # Summary frame
        summary_frame = ttk.Frame(results_frame)
        summary_frame.grid(row=0, column=0, columnspan=2, sticky=(tk.W, tk.E), pady=(0, 10))
        
        self.summary_label = ttk.Label(summary_frame, text="Chưa thực hiện so sánh", font=("Arial", 10, "bold"))
        self.summary_label.pack()
        
        # Notebook for different views
        self.notebook = ttk.Notebook(results_frame)
        self.notebook.grid(row=1, column=0, columnspan=2, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Side-by-side view
        self.side_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.side_frame, text="So sánh song song")
        
        # Left panel (Original)
        left_frame = ttk.LabelFrame(self.side_frame, text="File gốc (Original)", padding="5")
        left_frame.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(0, 5))
        
        self.left_text = scrolledtext.ScrolledText(left_frame, wrap=tk.WORD, width=50, height=20)
        self.left_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Right panel (Translated)
        right_frame = ttk.LabelFrame(self.side_frame, text="File đã dịch (Translated)", padding="5")
        right_frame.grid(row=0, column=1, sticky=(tk.W, tk.E, tk.N, tk.S), padx=(5, 0))
        
        self.right_text = scrolledtext.ScrolledText(right_frame, wrap=tk.WORD, width=50, height=20)
        self.right_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S))
        
        # Unified diff view
        self.diff_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.diff_frame, text="Xem chi tiết khác biệt")
        
        self.diff_text = scrolledtext.ScrolledText(self.diff_frame, wrap=tk.WORD, height=25, font=("Courier", 10))
        self.diff_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Code changes view
        self.code_frame = ttk.Frame(self.notebook)
        self.notebook.add(self.code_frame, text="Thay đổi Code")
        
        self.code_text = scrolledtext.ScrolledText(self.code_frame, wrap=tk.WORD, height=25, font=("Courier", 10))
        self.code_text.grid(row=0, column=0, sticky=(tk.W, tk.E, tk.N, tk.S), padx=5, pady=5)
        
        # Configure colors for diff display
        self.diff_text.tag_config("added", background="#d4edda", foreground="#155724")
        self.diff_text.tag_config("removed", background="#f8d7da", foreground="#721c24")
        self.diff_text.tag_config("changed", background="#fff3cd", foreground="#856404")
        self.diff_text.tag_config("line_number", foreground="#6c757d")
        
        self.code_text.tag_config("code_change", background="#ffe6e6", foreground="#d63384")
        self.code_text.tag_config("safe_change", background="#e6ffe6", foreground="#28a745")
        
        # Configure grid weights
        self.root.columnconfigure(0, weight=1)
        self.root.rowconfigure(0, weight=1)
        main_frame.columnconfigure(0, weight=1)
        main_frame.rowconfigure(0, weight=1)  # Input frame
        main_frame.rowconfigure(2, weight=1)  # Results frame
        results_frame.columnconfigure(0, weight=1)
        results_frame.rowconfigure(1, weight=1)
        self.side_frame.columnconfigure(0, weight=1)
        self.side_frame.columnconfigure(1, weight=1)
        self.side_frame.rowconfigure(0, weight=1)
        left_frame.columnconfigure(0, weight=1)
        left_frame.rowconfigure(0, weight=1)
        right_frame.columnconfigure(0, weight=1)
        right_frame.rowconfigure(0, weight=1)
        self.diff_frame.columnconfigure(0, weight=1)
        self.diff_frame.rowconfigure(0, weight=1)
        self.code_frame.columnconfigure(0, weight=1)
        self.code_frame.rowconfigure(0, weight=1)
        
    def toggle_input_method(self):
        """Toggle between text input and file selection"""
        if self.input_method.get() == "text":
            self.file_frame.grid_remove()
            self.text_frame.grid()
        else:
            self.text_frame.grid_remove()
            self.file_frame.grid()
    
    def get_content(self):
        """Get content from either text input or files"""
        if self.input_method.get() == "text":
            content1 = self.input_text1.get(1.0, tk.END).strip()
            content2 = self.input_text2.get(1.0, tk.END).strip()
            return content1, content2
        else:
            if not self.file1_path.get() or not self.file2_path.get():
                return None, None
            content1 = self.read_file(self.file1_path.get())
            content2 = self.read_file(self.file2_path.get())
            return content1, content2
        
    def select_file1(self):
        filename = filedialog.askopenfilename(
            title="Chọn file gốc",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.file1_path.set(filename)
            
    def select_file2(self):
        filename = filedialog.askopenfilename(
            title="Chọn file đã dịch",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        if filename:
            self.file2_path.set(filename)
            
    def read_file(self, filepath):
        try:
            with open(filepath, 'r', encoding='utf-8') as f:
                return f.read()
        except UnicodeDecodeError:
            try:
                with open(filepath, 'r', encoding='latin-1') as f:
                    return f.read()
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")
                return None
        except Exception as e:
            messagebox.showerror("Lỗi", f"Không thể đọc file: {e}")
            return None
    def compare_content(self):
        """Compare content from either text input or files"""
        content1, content2 = self.get_content()
        
        if content1 is None or content2 is None:
            if self.input_method.get() == "file":
                messagebox.showwarning("Cảnh báo", "Vui lòng chọn cả hai file để so sánh")
            else:
                messagebox.showwarning("Cảnh báo", "Vui lòng nhập nội dung vào cả hai ô text")
            return
        
        if not content1 or not content2:
            messagebox.showwarning("Cảnh báo", "Nội dung không được để trống")
            return
            
        self.file1_content = content1
        self.file2_content = content2
        
        # Clear previous results
        self.clear_results()
        
        # Show content in side-by-side view
        self.left_text.insert(tk.END, self.file1_content)
        self.right_text.insert(tk.END, self.file2_content)
        
        # Generate diff
        self.generate_diff()
        
        # Analyze code changes
        self.analyze_code_changes()
        
        # Update summary
        self.update_summary()
        
    def clear_all(self):
        """Clear all input and results"""
        self.input_text1.delete(1.0, tk.END)
        self.input_text2.delete(1.0, tk.END)
        self.file1_path.set("")
        self.file2_path.set("")
        self.clear_results()
        
    def generate_diff(self):
        lines1 = self.file1_content.splitlines()
        lines2 = self.file2_content.splitlines()
        
        diff = difflib.unified_diff(
            lines1, lines2,
            fromfile="File gốc",
            tofile="File đã dịch",
            lineterm="",
            n=3
        )
        
        for line in diff:
            if line.startswith('---') or line.startswith('+++'):
                self.diff_text.insert(tk.END, line + '\n', "line_number")
            elif line.startswith('@@'):
                self.diff_text.insert(tk.END, line + '\n', "line_number")
            elif line.startswith('-'):
                self.diff_text.insert(tk.END, line + '\n', "removed")
            elif line.startswith('+'):
                self.diff_text.insert(tk.END, line + '\n', "added")
            else:
                self.diff_text.insert(tk.END, line + '\n')
                
    def analyze_code_changes(self):
        lines1 = self.file1_content.splitlines()
        lines2 = self.file2_content.splitlines()
        
        # Patterns that might indicate code changes
        code_patterns = [
            '<KEY_WAIT>', '<cf>', '<NO_INPUT>', 
            '{ACTOR}', '{HERO}', '{VALUE}',
            'IfGender_', 'IfSing_', 'IfSolo(',
            '<--->'
        ]
        
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        
        code_changes = []
        safe_changes = []
        
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag == 'replace':
                original_lines = lines1[i1:i2]
                translated_lines = lines2[j1:j2]
                
                for orig, trans in zip(original_lines, translated_lines):
                    # Check if any code pattern changed
                    code_changed = False
                    for pattern in code_patterns:
                        if pattern in orig or pattern in trans:
                            orig_count = orig.count(pattern)
                            trans_count = trans.count(pattern)
                            if orig_count != trans_count:
                                code_changed = True
                                break
                    
                    if code_changed:
                        code_changes.append((orig, trans))
                    else:
                        safe_changes.append((orig, trans))
                        
        # Display results
        if code_changes:
            self.code_text.insert(tk.END, "⚠️ CẢNH BÁO: Phát hiện thay đổi code có thể gây lỗi:\n\n", "code_change")
            for orig, trans in code_changes:
                self.code_text.insert(tk.END, f"GỐC: {orig}\n", "code_change")
                self.code_text.insert(tk.END, f"DỊCH: {trans}\n\n", "code_change")
        else:
            self.code_text.insert(tk.END, "✅ Không phát hiện thay đổi code nguy hiểm\n\n", "safe_change")
            
        if safe_changes:
            self.code_text.insert(tk.END, "📝 Các thay đổi an toàn (chỉ text):\n\n", "safe_change")
            for orig, trans in safe_changes[:10]:  # Show first 10 safe changes
                self.code_text.insert(tk.END, f"GỐC: {orig}\n", "safe_change")
                self.code_text.insert(tk.END, f"DỊCH: {trans}\n\n", "safe_change")
                
    def update_summary(self):
        lines1 = self.file1_content.splitlines()
        lines2 = self.file2_content.splitlines()
        
        matcher = difflib.SequenceMatcher(None, lines1, lines2)
        ratio = matcher.ratio()
        
        summary = f"Độ tương đồng: {ratio:.2%} | "
        summary += f"File gốc: {len(lines1)} dòng | "
        summary += f"File dịch: {len(lines2)} dòng | "
        
        # Count changes
        changes = 0
        for tag, i1, i2, j1, j2 in matcher.get_opcodes():
            if tag != 'equal':
                changes += 1
                
        summary += f"Số thay đổi: {changes}"
        
        self.summary_label.config(text=summary)
        
    def clear_results(self):
        self.left_text.delete(1.0, tk.END)
        self.right_text.delete(1.0, tk.END)
        self.diff_text.delete(1.0, tk.END)
        self.code_text.delete(1.0, tk.END)
        self.summary_label.config(text="Chưa thực hiện so sánh")
        
    def save_results(self):
        if not self.diff_text.get(1.0, tk.END).strip():
            messagebox.showwarning("Cảnh báo", "Chưa có kết quả so sánh để lưu")
            return
            
        filename = filedialog.asksaveasfilename(
            title="Lưu kết quả so sánh",
            defaultextension=".txt",
            filetypes=[("Text files", "*.txt"), ("All files", "*.*")]
        )
        
        if filename:
            try:
                with open(filename, 'w', encoding='utf-8') as f:
                    f.write("=== KẾT QUẢ SO SÁNH ===\n\n")
                    if self.input_method.get() == "file":
                        f.write(f"File gốc: {self.file1_path.get()}\n")
                        f.write(f"File dịch: {self.file2_path.get()}\n\n")
                    else:
                        f.write("Nguồn: Nhập trực tiếp từ text input\n\n")
                    f.write("=== CHI TIẾT KHÁC BIỆT ===\n")
                    f.write(self.diff_text.get(1.0, tk.END))
                    f.write("\n\n=== PHÂN TÍCH CODE ===\n")
                    f.write(self.code_text.get(1.0, tk.END))
                    
                messagebox.showinfo("Thành công", f"Đã lưu kết quả vào: {filename}")
            except Exception as e:
                messagebox.showerror("Lỗi", f"Không thể lưu file: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = FileComparator(root)
    root.mainloop()