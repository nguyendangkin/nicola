# So sánh Tag & Biến trong File Dịch (Tkinter GUI)

Ứng dụng này giúp kiểm tra **tính nhất quán giữa file gốc và file dịch** trong các dự án Việt hóa game hoặc phần mềm có sử dụng **tag** (ví dụ: `<KEY_WAIT>`, `<IfGender_WORD(him,her,they)>`) và **biến** (ví dụ: `{HERO}`), được trích ra từ tool UE4localizationsTool.v2.7 (export kiểu: noname).

---

## ✅ Giới thiệu

Trong các bản dịch, việc thiếu hoặc dịch sai các tag và biến đặc biệt có thể gây lỗi nghiêm trọng trong game hoặc phần mềm. Công cụ này hỗ trợ kiểm tra tự động, phát hiện:

-   Thiếu/Dư **tag**.
-   Thiếu/Dư **biến**.
-   Sai **tham số** trong tag.
-   Thiếu/Dư dòng hoặc key (`Txt_...`).

Ngoài ra, nếu file chỉ là văn bản bình thường (các định dạng khác ngoài `Txt_`), công cụ vẫn hoạt động bằng cách so sánh từng dòng như bình thường.

---

## 🛠 Vấn đề cần giải quyết

-   Dịch bằng AI, đôi khi chúng lại bỏ xót các "key code", việc này khiến chúng ta trở nên "thốn - lo âu, thấp thỏm và hoài nghi" vô cùng. Việc tìm kiếm từng dòng text và chỉnh sửa khiến ta hơi cực, xong việc tìm với khối lượng lớn lại càng cực hơn.
-   Việc kiểm tra thủ công rất tốn thời gian và dễ bỏ sót.
-   Hoặc đôi khi các dịch giả thường bỏ sót tag hay biến.

Công cụ này giải quyết bằng cách **so sánh từng dòng**, hiển thị rõ ràng lỗi và gợi ý chỉnh sửa.

---

## 🚀 Hướng dẫn sử dụng

1. **Tải tool**:

    - Vào thư mục `dist/` và tải file `.exe` về máy.
    - Chạy file `.exe` (không cần cài Python).

2. **Cách dùng**:

    - Mở ứng dụng.
    - Bên trái: dán nội dung file gốc.
    - Bên phải: dán nội dung bản dịch.
    - Nhấn nút **Kiểm tra**.

3. **Kết quả hiển thị**:

    - Danh sách lỗi ở phía dưới.
    - Click vào lỗi để nhảy đến dòng liên quan.
    - Highlight màu:

        - Vàng nhạt: dòng gốc.
        - Hồng nhạt: dòng dịch.

4. **Tính năng bổ sung**:

    - **Undo/Redo không giới hạn**: Ctrl+Z / Ctrl+Y.
    - **Tìm & Thay thế**: Ctrl+H.
    - **Copy log lỗi**: Nút "Copy Log Lỗi" để gửi AI cùng xem xét và chỉnh sửa lại.

---

## 📌 Lưu ý

-   Đảm bảo **nội dung hai bên tương ứng dòng với dòng** để kết quả chính xác.
