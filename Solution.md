# Solution - Day 12 Lab: Đưa Agent Lên Cloud

## Part 1: Localhost vs Production

### Exercise 1.1: Các anti-patterns trong code develop (app.py)
5 vấn đề chính thường gặp:
1. **Hardcode API Key / Secrets:** Lưu trực tiếp `AGENT_API_KEY` trong mã nguồn, dễ bị lộ khi đẩy lên GitHub.
2. **Cố định cấu hình (Hardcoded Port/Host):** Port và Host bị gán cứng, khó thay đổi linh hoạt khi chuyển môi trường.
3. **Bật Debug Mode trong Production:** Có thể làm rò rỉ thông tin nhạy cảm qua traceback lỗi.
4. **Không có Health Check:** Orchestrator (Docker/Kubernetes) không biết ứng dụng sống hay chết để khởi động lại.
5. **Không xử lý Graceful Shutdown:** Ứng dụng tắt đột ngột, làm gián đoạn các request đang xử lý dở.

### Exercise 1.3: So sánh Basic vs Advanced

| Feature | Basic | Advanced | Tại sao quan trọng? |
|---------|-------|----------|---------------------|
| Config | Hardcode | Env vars (`.env`) | Bảo mật secrets, dễ dàng cấu hình riêng cho từng môi trường (dev, staging, prod) mà không cần sửa code. |
| Health check | Không có | Có (`/health`) | Hệ thống (Load Balancer, Container Orchestrator) tự động biết trạng thái app để điều phối traffic hoặc tự restart khi app treo. |
| Logging | `print()` | JSON Structured | Dễ dàng parse, tìm kiếm và phân tích log trên các hệ thống giám sát tập trung (như ELK, Datadog). |
| Shutdown | Đột ngột | Graceful | Cho phép ứng dụng hoàn thành nốt các request đang dang dở và đóng kết nối DB an toàn trước khi thoát, tránh mất data. |

---

## Part 2: Docker Containerization

### Exercise 2.1: Dockerfile cơ bản
1. **Base image là gì?** `python:3.11-slim` (hoặc bản tương tự), là image Linux nhỏ gọn chứa sẵn Python, giúp giảm kích thước.
2. **Working directory là gì?** Là thư mục mặc định trong container nơi các lệnh được thực thi (ví dụ: `/app`).
3. **Tại sao COPY requirements.txt trước?** Để tận dụng Docker cache. Nếu file này không đổi, Docker sẽ không tải lại thư viện, giúp build cực nhanh ở những lần sau.
4. **CMD vs ENTRYPOINT?** `ENTRYPOINT` quy định executable chính của container (không thể dễ ghi đè), còn `CMD` cung cấp tham số mặc định cho `ENTRYPOINT` (dễ dàng ghi đè bằng lệnh khi chạy).

### Exercise 2.3: Multi-stage build
- **Stage 1 (Builder):** Cài đặt các công cụ build (như `gcc`, `g++`) và compile thư viện Python thành các bánh xe (wheels) hoặc thư mục site-packages.
- **Stage 2 (Runner):** Chỉ copy các file thư viện đã compile từ stage 1 sang một base image siêu nhẹ (ví dụ alpine/slim) mà không mang theo các công cụ build nặng nề.
- **Tại sao image nhỏ hơn?** Vì nó loại bỏ được toàn bộ build tools, cache file dư thừa của apt/pip từ Stage 1.

### Exercise 2.4: Docker Compose stack
- **Các services được start:** Thường gồm `agent` (ứng dụng web), `redis` (database lưu trạng thái), và `nginx` (Load Balancer).
- **Cách giao tiếp:** Qua mạng nội bộ (internal network) do Docker Compose tạo ra, sử dụng trực tiếp service name làm hostname (ví dụ: `redis:6379`).

---

## Part 3: Cloud Deployment

### Exercise 3.2: Render vs Railway
- `render.yaml` và `railway.toml` đều là file Infrastructure as Code (IaC) để cấu hình môi trường cloud tự động.
- Điểm khác: Cú pháp và các tuỳ chọn đặc thù. `render.yaml` hỗ trợ Blueprint để định nghĩa cả Database + Web Service cùng lúc rõ ràng, trong khi `railway.toml` thiên về tuỳ chỉnh behavior của buildpack/nix.

---

## Part 4: API Security

### Exercise 4.1: API Key authentication
- **Check ở đâu?** Trong Middleware hoặc FastAPI Dependency (ví dụ hàm `verify_api_key`).
- **Sai key xảy ra gì?** Trả về HTTP 401 Unauthorized hoặc 403 Forbidden.
- **Làm sao rotate key?** Tạo key mới trong `.env`, restart server/container, sau đó thu hồi key cũ.

### Exercise 4.3: Rate limiting
- **Algorithm:** Thường dùng *Sliding Window* hoặc *Token Bucket* lưu trong Redis để quản lý số request theo từng mốc thời gian.
- **Limit:** Ví dụ 10 requests / minute cho user thường.
- **Bypass:** Kiểm tra logic nếu `user_role == 'admin'` thì bỏ qua đoạn check trong Redis.

---

## Part 5: Scaling & Reliability

### Exercise 5.2: Graceful shutdown
- **Điều gì xảy ra:** Container nhận signal `SIGTERM` từ orchestrator -> Dừng nhận request mới -> Chờ các request hiện tại phản hồi xong -> Đóng kết nối DB -> Tắt ứng dụng.

### Exercise 5.3: Stateless design
- Cần Stateless vì khi có nhiều agent instances (chạy song song), các request của cùng 1 user có thể được Nginx chia cho nhiều instance khác nhau. Nếu lưu state trên RAM (memory), instance 2 sẽ không biết dữ liệu mà instance 1 đang giữ. Việc lưu tất cả ra Redis (external state) giúp các instance độc lập, dễ dàng scale up/down.

### Exercise 5.4: Load balancing
- Chạy `scale agent=3` sẽ tạo ra 3 bản sao của container Agent. Nginx sẽ đứng trước làm Proxy (Round Robin), chia đều traffic lần lượt vào 3 Agent để giảm tải cho mỗi node.

---

## Part 6: Final Project — Production AI Agent

### 🌐 Deployed URL
> **https://ai-agent-production-7vsu.onrender.com**

### Test endpoints
```bash
# Health check
curl https://ai-agent-production-7vsu.onrender.com/health

# Readiness check
curl https://ai-agent-production-7vsu.onrender.com/ready

# Ask agent (cần API Key)
curl https://ai-agent-production-7vsu.onrender.com/ask -X POST \
  -H "X-API-Key: <YOUR_API_KEY>" \
  -H "Content-Type: application/json" \
  -d '{"question": "Hello"}'
```

### Production Features Implemented
| Feature | Status |
|---------|--------|
| REST API (`/ask`) | ✅ |
| Conversation history (Redis) | ✅ |
| Multi-stage Docker build | ✅ |
| Environment variables config (12-Factor) | ✅ |
| API Key authentication | ✅ |
| Rate limiting (10 req/min/user) | ✅ |
| Cost guard ($10/month/user) | ✅ |
| Health check (`/health`) | ✅ |
| Readiness check (`/ready`) | ✅ |
| Graceful shutdown (SIGTERM) | ✅ |
| Stateless design (Redis) | ✅ |
| Structured JSON logging | ✅ |
| Deploy on Render | ✅ |
