# Hướng Dẫn Hoàn Thành Lab Day 12 (Chuẩn Từng Bước)

Sau khi đọc toàn bộ tài liệu từ các thư mục (01 đến 06), dưới đây là lộ trình chính xác nhất để bạn hoàn thành bài Lab này đúng như yêu cầu của giảng viên.

> [!IMPORTANT]
> Các bạn của bạn nói ĐÚNG! Bạn **BẮT BUỘC phải cài đặt Docker Desktop** trên máy tính để chạy test và kiểm tra lỗi ở các bước thực hành (đặc biệt là lệnh `docker compose up` và file `check_production_ready.py`).

---

## 🟢 PHẦN 1: Học & Trả Lời Câu Hỏi (Thư mục 01 - 05)

Mục đích của 5 thư mục đầu tiên là để bạn **đọc code, chạy thử lệnh, và so sánh** sự khác biệt giữa code "Kiểu Localhost" (Develop) và code "Chuẩn Production". 

**Cách làm:**
1. Di chuyển vào từng thư mục (từ 01 đến 05).
2. Đọc file `README.md` trong từng thư mục đó.
3. Chạy các lệnh kiểm thử (như `docker build`, `curl`) được hướng dẫn trong file README để xem app hoạt động ra sao.
4. Trả lời các câu hỏi thảo luận ở cuối mỗi file README. 
*(Mình đã giúp bạn tổng hợp sẵn đáp án của 5 thư mục này vào file `Solution.md` ở thư mục gốc rồi, bạn chỉ cần đọc để hiểu).*

---

## 🔵 PHẦN 2: Hoàn Thiện Project Cuối Môn (Thư mục 06)

Đây là bước quan trọng nhất để nộp bài. Bạn phải cấu hình thư mục `06-lab-complete` sao cho nó đạt chuẩn Production 100%.

**Các bước thực hiện trên máy bạn:**

1. **Chuẩn bị file môi trường (.env)**
   - Mở thư mục `06-lab-complete`.
   - Copy nội dung file `.env.example` sang một file mới tên là `.env`.
   - Điền một đoạn mã ngẫu nhiên vào `AGENT_API_KEY` (Ví dụ: `my-super-secret-key`).

2. **Chạy Docker Compose (Test Local)**
   - Bật phần mềm Docker Desktop trên máy bạn lên.
   - Mở Terminal tại thư mục `06-lab-complete` và chạy lệnh:
     ```bash
     docker compose up --build
     ```
   - Docker sẽ tự động tải Python, tải Redis và khởi chạy Agent của chúng ta.

3. **Chấm điểm Local (Rất quan trọng!)**
   - Mở một tab Terminal khác (vẫn ở thư mục `06-lab-complete`).
   - Chạy script chấm điểm tự động của giảng viên:
     ```bash
     python check_production_ready.py
     ```
   - Script này sẽ check xem Dockerfile có đạt chuẩn không, API có chạy tốt không, Rate limit và Redis có hoạt động không. **Chỉ khi script này pass hết (màu xanh), bạn mới nên mang đi Deploy.**
   *(Lưu ý: Mình đã viết sẵn code trong thư mục 06 cho bạn đạt chuẩn rồi, bạn chỉ việc chạy để tận hưởng kết quả).*

---

## 🟣 PHẦN 3: Đưa lên Cloud (Deploy)

Sau khi code đã chạy hoàn hảo trên máy tính của bạn (nhờ Docker), bước cuối cùng là đẩy nó lên Cloud để lấy URL nộp cho giảng viên.

Bạn có 2 lựa chọn (chọn 1 trong 2):

### Lựa chọn A: Dùng Render.com (Khuyên dùng)
1. Commit toàn bộ project của bạn và đẩy lên **GitHub**.
2. Đăng nhập [Render.com](https://render.com), chọn **New > Blueprint**.
3. Kết nối với repo GitHub của bạn. Render sẽ tự đọc file `render.yaml` (mình đã cập nhật sẵn cho bạn) và tự động tạo cả Web Service lẫn Redis Database hoàn toàn miễn phí.
4. Lấy API URL sau khi Web "Live".

### Lựa chọn B: Dùng Railway (Theo hướng dẫn của Lab)
1. Tải và cài đặt Railway CLI (`npm i -g @railway/cli`).
2. Mở terminal ở thư mục `06-lab-complete`, gõ `railway login`.
3. Gõ `railway init` để tạo project mới.
4. Gán biến môi trường: `railway variables set AGENT_API_KEY=key-cua-ban`.
5. Gõ `railway up` để đẩy code lên.
6. Gõ `railway domain` để lấy đường link URL.

---

### 📝 Tổng kết file nộp bài:
Khi nộp bài, bạn chỉ cần nộp 2 thứ:
1. File **`Solution.md`** (đã có sẵn).
2. Đường link **API URL** (Lấy được sau khi thực hiện xong Phần 3).
