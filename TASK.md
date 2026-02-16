# TASKS: Circle K-style POS System (Offline-First, Store Edge → HQ Sync)

## Milestone 1 – Local Store Edge MVP (No Sync Yet)

### Goal
Xây dựng được một Store Edge chạy local với Postgres, hỗ trợ checkout cơ bản trên 1 cửa hàng, 1 POS, **chưa cần đồng bộ HQ** nhưng đã có Outbox để chuẩn bị cho sync.

### Tasks
- [x] Khởi tạo repo
  - [x] Tạo monorepo hoặc 2 repo: `store-edge` và `hq-platform`
  - [ ] Thiết lập basic CI (lint, test)

- [ ] Store Edge – Setup cơ bản
  - [x] Viết docker-compose với Postgres + edge-api (FastAPI)
  - [x] Tạo migration (Alembic) cho các bảng: `transactions`, `line_items`, `payments`, `local_catalog`, `local_inventory`, `outbox`, `sync_cursors`
  - [ ] Seed data đơn giản cho `local_catalog` và `local_inventory`

- [ ] Store Edge – Checkout API (v1)
  - [x] API tạo transaction (DRAFT)
  - [x] API thêm item theo barcode
  - [ ] API tính tổng (subtotal, tax, total)
  - [ ] API tạo payment (QR dummy – sinh ra chuỗi JSON giả, chưa call provider thật)
  - [ ] API finalize transaction: chuyển sang PAID, trừ tồn kho

- [ ] Store Edge – Outbox (ghi event nhưng chưa relay)
  - [ ] Định nghĩa event model (`SaleRecorded`, `InventoryAdjusted`)
  - [ ] Trong finalize transaction, ghi event vào `outbox` cùng transaction DB
  - [ ] Viết job đơn giản để list outbox (debug, log ra console)

- [ ] Testing & Manual Verification
  - [ ] Viết unit test cho Checkout service (create/add-item/finalize)
  - [ ] Chạy end-to-end local: gọi API bằng Postman/HTTPie
  - [ ] Verify: transaction + line_items + inventory + outbox được ghi đúng


## Milestone 2 – Upstream Sync v1 (HTTP Batch)

### Goal
Đồng bộ **Store → HQ** bằng HTTP batch từ Outbox, đơn giản, dễ debug, gần real-time (0.5–2s). HQ lúc này chỉ cần service ingest nhận event và log/ghi DB.

### Tasks
- [ ] HQ Platform – Skeleton
  - [ ] Tạo service `hq-ingestion` (FastAPI hoặc Go nhỏ gọn)
  - [ ] Tạo bảng `hq_inbox` + `hq_transactions` (phiên bản đơn giản ở HQ)

- [ ] Store Edge – Outbox Relay (HTTP)
  - [ ] Viết process/worker đọc `outbox` với `FOR UPDATE SKIP LOCKED`
  - [ ] Gom event thành batch (ví dụ tối đa 50 events)
  - [ ] Gửi POST `/v1/ingestion/events` lên HQ
  - [ ] Mark `published_at` khi nhận ACK OK
  - [ ] Implement retry với exponential backoff (lưu `publish_attempts`, `last_error`)

- [ ] HQ – Ingestion API
  - [ ] Endpoint `/v1/ingestion/events` nhận danh sách events
  - [ ] Lưu vào `hq_inbox` để dedup theo `event_id`
  - [ ] Với event mới: ghi vào `hq_transactions`
  - [ ] Trả về thống kê `accepted`, `duplicates`, `errors`

- [ ] Connectivity & Offline Simulation
  - [ ] Thêm config URL HQ, timeout, retry interval cho relay
  - [ ] Test case: tắt HQ (hoặc chặn mạng), cho POS chạy, xem outbox tăng
  - [ ] Bật HQ lại, verify: tất cả events được gửi lên và đánh dấu `published_at`

- [ ] Monitoring cơ bản (local)
  - [ ] Thêm log structured cho relay (event_id, attempts, error)
  - [ ] Expose `/health` cho edge-api và hq-ingestion


## Milestone 3 – Offline Mode & Multi-POS

### Goal
Hỗ trợ **5 POS / cửa hàng**, xử lý offline mode rõ ràng (detect offline/online) nhưng upstream vẫn dùng HTTP batch. Đảm bảo transaction không bị mất khi mạng chập chờn.

### Tasks
- [ ] Multi-terminal support
  - [ ] Thêm concept `terminal_id`, `cashier_id` vào tất cả API và schema
  - [ ] POS giả lập: viết script CLI hoặc UI nhỏ gọi API như 5 máy khác nhau

- [ ] Offline detection & state
  - [ ] Implement health-check loop ở Store Edge (Sync Agent)
  - [ ] Nếu ping HQ fail N lần liên tiếp → set state OFFLINE
  - [ ] API nội bộ/endpoint cho POS query trạng thái `online/offline` để hiển thị UI

- [ ] Behavior khi OFFLINE
  - [ ] Cho phép checkout bình thường (ghi DB + outbox)
  - [ ] Relay tạm thời chỉ retry theo backoff, không crash
  - [ ] Hạn chế các operation cần online (tạm thời chỉ cần log cảnh báo)

- [ ] Conflict & Ordering cơ bản
  - [ ] Đảm bảo ordering theo `outbox.id` khi gửi
  - [ ] Ở HQ, xử lý idempotent dựa trên `event_id`

- [ ] Test scenarios
  - [ ] Online bình thường với 5 POS
  - [ ] Đang checkout thì cắt mạng → vẫn trả lời OK cho POS
  - [ ] Sau khi mạng lên → tất cả events lên HQ đúng thứ tự


## Milestone 4 – Chuyển sang gRPC Streaming (Real-time hơn)

### Goal
Thay vì HTTP batch polling, dùng **gRPC streaming** giữa Store Edge và HQ để giảm latency, vẫn dựa trên Outbox pattern.

### Tasks
- [ ] Thiết kế proto
  - [ ] Định nghĩa `Event`, `EventBatch`, `Acknowledgment`
  - [ ] Service `SyncService.StreamEvents(stream EventBatch) returns (stream Acknowledgment)`

- [ ] HQ – gRPC server
  - [ ] Implement server nhận stream EventBatch
  - [ ] Áp dụng inbox/idempotency y như HTTP
  - [ ] Trả ACK theo batch (list event_id accepted/duplicate/error)

- [ ] Store Edge – gRPC client
  - [ ] Implement client duy trì stream lâu dài
  - [ ] Map outbox relay → thay vì gọi HTTP, push vào stream
  - [ ] Implement reconnect/backoff khi mất kết nối

- [ ] Feature flag
  - [ ] Cho phép chọn `SYNC_PROTOCOL = http|grpc` qua config
  - [ ] Đảm bảo fallback về HTTP nếu gRPC lỗi (option)

- [ ] Benchmark cơ bản
  - [ ] So sánh latency trung bình HTTP batch vs gRPC stream trên localhost


## Milestone 5 – HQ Services & Reporting Cơ Bản

### Goal
Hoàn thiện dần HQ để nhìn được dữ liệu multi-store, có vài report và chuẩn bị nền cho scaling.

### Tasks
- [ ] Chuẩn hóa schema HQ
  - [ ] Tách `hq_transactions`, `hq_line_items`, `hq_inventory` riêng
  - [ ] Viết migration cho HQ DB

- [ ] Simple reporting
  - [ ] API `GET /v1/reports/sales?store_id&from&to`
  - [ ] API `GET /v1/reports/inventory?store_id`

- [ ] Store metadata
  - [ ] Bảng `stores` ở HQ (id, name, address, status)
  - [ ] Gắn `store_id` trong mọi event/record để query theo store

- [ ] Observability
  - [ ] Thêm Prometheus metrics cho ingestion (events_received, duplicates, latency)
  - [ ] Dashboard Grafana đơn giản (nếu muốn)


## Milestone 6 – Payment QR Integration (Thực tế hơn)

### Goal
Thay QR giả bằng tích hợp thật (hoặc sandbox) với 1 payment provider (ví dụ VNPAY/MoMo), xử lý callback + reconcile.

### Tasks
- [ ] Abstraction Payment
  - [ ] Định nghĩa interface PaymentProvider
  - [ ] Implement provider fake trước (in-memory)

- [ ] Tích hợp provider thật/sandbox
  - [ ] API create payment → call provider tạo QR
  - [ ] Endpoint callback/webhook từ provider → update payment status

- [ ] Flow đồng bộ với HQ
  - [ ] Khi PaymentCaptured → sinh event `PaymentCaptured` lên HQ
  - [ ] HQ lưu vào `hq_payments`, phục vụ reconcile

- [ ] Test
  - [ ] User scan QR, thanh toán xong, POS thấy status CAPTURED và finalize transaction


## Milestone 7 – Cleanup, Hardening & Docs

### Goal
Ổn định, dọn code, bổ sung test + log + doc để hệ thống dùng được cho học tập lâu dài.

### Tasks
- [ ] Refactor & module hóa code Store Edge (domain, infra, api)
- [ ] Thêm nhiều unit/integration test (đặc biệt cho sync & offline)
- [ ] Viết README chi tiết cho `store-edge` và `hq-platform`
- [ ] Cập nhật lại `Circle-K-System-Design.md` theo implementation thực tế

