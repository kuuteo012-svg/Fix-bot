# CODEBASE MAP — AutoBot (Telegram code bot, đa site)

> **File này để làm gì:** đây là bản đồ code để một model AI khác (hoặc chính
> bạn sau này) **không cần đọc từng file** vẫn biết: file nào làm gì, hàm nào
> xử lý việc gì, luồng gọi đi qua đâu, lỗi thường nằm ở đâu, và sửa ở đâu.
> Đọc file này trước, rồi chỉ mở đúng file/hàm được chỉ định khi cần sửa.
> Mọi tên hàm, tên file, marker trong tài liệu này đều lấy trực tiếp từ code
> bằng AST (không đoán), đối chiếu với snapshot ở mục 1.
>
> **Quy tắc vàng khi dùng file này để sửa code:**
> 1. Sửa đúng hàm được chỉ trong bảng "Muốn đổi X → sửa Y" (mục 4), đừng
>    viết lại luồng mới, đừng thêm file/hàm mới nếu chưa cần.
> 2. `.env` luôn thắng mặc định trong code — trước khi đổi mặc định, kiểm
>    tra tên biến đó trong `.env` (chỉ kiểm tra TÊN biến, không trích giá trị
>    secret ra ngoài).
> 3. Không bao giờ đọc, copy, hay đưa `.env`, file `.session`, token,
>    API key vào tài liệu, log, hay chat. File này cố tình không chứa bất kỳ
>    giá trị secret nào.
> 4. Không chạy 2 bot cùng lúc (single-instance lock + session SQLite lock).
> 5. Sau khi sửa, kiểm tra marker bằng `findstr` rồi mới chạy bot (mục 11).

---

## 1. Snapshot — tài liệu này mô tả đúng bản nào

- **Nguồn:** `blogs.zip` gửi ngày 28/10/2026. Zip này ngoài code còn chứa
  `logs/` (log, lịch sử code theo ngày, screenshot) và `.env` — tài liệu này
  **không** mô tả log và **không** đọc `.env`.
- **Code trong zip:** 40 file Python, tổng **27.654 dòng** (đếm bằng `wc -l`),
  cộng `run.bat`, `setup.bat`, `requirements.txt`, `README.md` (placeholder).
- **Entry point duy nhất:** `python main_script.py`, qua `run.bat`
  (launcher + supervisor tự chạy lại, xem mục 3).
- **Dòng build in lúc khởi động** (`main_script.py:main`):
  `2026-10-21-spoiler-dialog-batch-v11.0.2-poll-ocr-v4-2026-10-25-xx88-tabs-v5-2026-10-25`
  + `PATCH_MARKER_2026-10-25-v5-xx88-tabs-queue` +
  `PATCH_MARKER_2026-10-26-v9-core-ocr-sqlite`, `browser=dual-edge`.
- **Marker CÓ trong zip này** (đếm bằng `grep -r PATCH_MARKER`):
  - `PATCH_MARKER_2026-10-26-v10` — `browser_engine.py`, đủ 7 dòng
    (form timeout 1500 ms, log chunk, tab states, foreground throttle 2 s).
  - `PATCH_MARKER_2026-10-26-llwin-slider-logs2` — 5 chỗ
    (`browser_engine.py` ×3, `browser_site_profiles.py` ×1,
    `llwin_slider.py` ×1): slider LLwin bản logs-2, kèm OS mouse
    (xem mục 7.4).
  - `PATCH_MARKER_2026-10-28-xx88-clearance-cookie` ×3, `tabonly-prefill`
    ×2, `tabonly-form-recovery` ×1, `qq88-recaptcha-verify` ×2,
    `llwin-slider-api-race` ×1, `cleanup-verify` ×1, `stateless-entry` ×3,
    `parallel-llwin-local-labels` ×3, `v6-async-ingest` ×3,
    `streaming-ctc` ×4, `v9-core-ocr-sqlite` ×8, `v8-bugfix` ×9,
    `v5-xx88-tabs-queue` ×7, `v4-poll-ocr` ×6, `v7-apitimer-std` ×3,
    `v6-xx88-spoiler-nolock` ×2.
- **Marker KHÔNG có trong zip này — đừng tưởng là có:**
  `monitor-front` (đưa tab lên trước mỗi submit), `llwin-slider-logs2-v2`,
  `slider-drag-fix`, `phase1-verify-pool`, `cleanup-v1`. Nếu người dùng hỏi
  về các tính năng đó thì trả lời là chưa có trong snapshot này, cần vá riêng.
- **QQ88 và HI88 VẪN CÒN trong zip này** (kênh, profile, code xử lý riêng).
  Bản "bot gọn không QQ88/HI88" là một bản vá rời khác, không phải zip này.
- **Kênh:** 31 kênh trong `config.py: CHANNEL_CONFIG` (bảng ở mục 8).
- **Site:** 9 profile trong `browser_site_profiles.py: SITE_PROFILES`
  (bảng ở mục 8).
- **Python:** Windows, venv `.venv312`, xem `requirements.txt`
  (telethon, playwright, rapidocr, onnxruntime, opencv, pillow, numpy,
  psutil, httpx, rich, python-dotenv, cryptg, tzdata).

---

## 2. Kiến trúc tổng thể (một hình, đủ hiểu)

```
Telegram channels (31 kênh)
  │  push (Telethon update) + poll (quét định kỳ)
  ▼
tg_ingest.py: TelegramReceiver + IngressStage
  │  durable_inbox.py: DurableInbox (SQLite, at-least-once, checkpoint)
  ▼
main_script.py: message_worker / _inbox_drain_loop / ingest_worker
  │  process_telegram_message -> _process_telegram_message_impl
  │    ├─ text/spoiler/KJC ──► code_extraction + code_validator + kjc
  │    └─ ảnh/video ────────► media_download_manager -> ocr_pipeline
  │                            + image_code_extractor + streaming_code_reader
  ▼
main_script.py: _filter_channel_codes -> _build_*_items (fanout theo tài khoản)
  │  dedupe (code_identity + database) + tuổi mã (freshness + scheduling)
  ▼
domain_code_worker (1 worker / domain) -> _submit_code_with_account_retries
  │  submit_pacer (giữ slot, phạt khi 429) + TabPool / semaphore theo domain
  ├─ browser: browser_adapter -> browser_engine.submit_code_browser
  │             -> _submit_code_browser_locked_inner (form, Turnstile,
  │                slider LLwin, click, đọc kết quả toast + API listener)
  └─ direct HTTP (chỉ XX8): http_submitter.HttpSubmitter
  ▼
submission_outcomes.classify_result / record_outcome
  │  database.CodeDatabase + append_code_history (CSV/JSONL theo ngày)
  ▼
log (logger_setup) + dashboard (Rich) + admin /status (features)
```

**Nguyên tắc phân lớp (đừng phá vỡ khi sửa):**

- `main_script.py` là điều phối, không chứa selector form, không chứa
  thuật toán OCR, không chứa API endpoint của site. Selector/endpoint nằm
  ở `browser_site_profiles.py`; thuật toán OCR nằm ở `ocr_pipeline.py`;
  luật validate nằm ở `code_validator.py`.
- `browser_engine.py` là nhân submit trình duyệt, không biết gì về Telegram.
  Nó nhận `(user, code, target_url, systems)` và trả về dict kết quả chuẩn
  (`success`, `message`, `status`, `failure_kind`, `keep_page`…).
- `config.py` là nguồn cấu hình duy nhất. Không hard-code domain, tài khoản,
  timeout vào các file khác nếu đã có trong `Config` hoặc `SiteProfile`.
- Kết quả submit được phân loại ở `submission_outcomes.py`, không phân loại
  bằng `if "thành công" in text` rải rác ở các file khác.

---

## 3. Khởi động, chạy, dừng — hàm nào làm gì

| Việc | Hàm / file | Ghi chú cho AI sửa code |
|---|---|---|
| Chạy bot | `run.bat` → `python main_script.py` | `run.bat` là supervisor: exit 0/1/2/3/78/`-1073741510` thì không chạy lại; exit 4 (dừng ngoài ý muốn) thì chạy lại tối đa 10 lần, chờ 5→120 s, reset bộ đếm nếu chạy ổn định ≥ 600 s. Log supervisor: `logs/launcher_cmd.log`. |
| Cài lần đầu | `setup.bat` → tạo `.venv312`, cài `requirements.txt` | Không sửa `setup.bat` nếu chỉ vá logic bot. |
| Entry | `main_script.main()` | Kiểm tra `API_ID`/`API_HASH` (thiếu → exit 2), lấy single-instance lock (trùng → exit 3), `init_systems()`, load xoay tài khoản, `ensure_chromes_ready()`, warm-up OCR, `client.start()` (thử tối đa 3 lần), đăng ký handler, chạy workers. |
| Khởi tạo hệ thống | `main_script.init_systems()` | Trả về dict `systems`: `db`, `db_executor`, `inbox`, `performance_monitor`, `health_monitor`. Khởi tạo DB, monitoring, shutdown handler, history writer, `DurableInbox` (lease mặc định 300 s, retry tối đa 3 lần, backoff 2→120 s), khôi phục inbox (`reset_retryable_failed`, `reclaim_stale`) trừ khi `live_only` (khi đó `discard_unfinished` và tự chuyển về `at_least_once` nếu có checkpoint cũ). |
| Khởi tạo kênh/tài khoản | `main_script.init_channels_and_accounts()` | Đọc `CHANNEL_CONFIG`, xây map domain→tài khoản, kiểm tra kênh. |
| Single instance | `main_script.acquire_single_instance_lock()` + `_instance_lock_path()` | Phải chạy trước DB/Edge/Telethon để bản trùng thoát sạch. |
| Session Telegram | `main_script._build_telegram_session()`, `verify_telegram_session()`, `sync_telegram_dialogs()`, `verify_channels_and_get_ids()` | Session là `ResilientSQLiteSession` (busy timeout, WAL). Session bị khoá → `client.start()` báo lỗi và hướng dẫn tắt bot khác. `backup_corrupt_telegram_session()` sao lưu session hỏng. |
| Workers | `main_script.start_message_workers()`, `start_domain_workers()`, `start_ocr_media_workers()` | Message worker xử lý tin; domain worker (1/domain) xử lý hàng đợi submit; OCR worker xử lý media. Semaphore: `_get_proc_semaphore()`, `_get_submit_semaphore(domain)`, `_get_ocr_semaphore()`. |
| Dừng sạch | `features.GracefulShutdownHandler` (`setup`, `_do_shutdown`, `notify_cleanup_done`) + `browser_engine.cleanup_browsers()` / `shutdown()` | Đừng `sys.exit()` giữa chừng trong worker mà không qua shutdown handler. |
| Lệnh admin | `features.setup_admin_commands(client, admin_id, ...)` + `CommandRegistry` (`register`, `has`, `dispatch`) | Chỉ `TELEGRAM_ADMIN_ID` mới dùng được. Lệnh mặc định: `/status` → `_build_status_report()`. Lệnh chạy bất đồng bộ, có timeout riêng. |

---

## 4. Tra cứu nhanh — muốn đổi X thì sửa hàm Y (bảng quan trọng nhất)

| Muốn đổi / sửa | Sửa ở đâu (file : hàm) | Đừng sửa ở đâu |
|---|---|---|
| Thêm/bớt kênh Telegram, đổi site đích của kênh, đổi tài khoản của kênh | `config.py : CHANNEL_CONFIG` (dict, khóa là chat ID) | Đừng sửa `tg_ingest.py` để hard-code kênh. |
| Thêm site mới / đổi selector form / timeout / endpoint API của site | `browser_site_profiles.py : SITE_PROFILES` + `SiteProfile.validate()` | Đừng hard-code selector trong `browser_engine.py` (trừ selector dùng chung đã có hàm `_site_profile_value`). |
| Đổi giới hạn tab, slot song song, TTL mã, pacer, danh sách domain đặc biệt | `config.py : Config` (đọc `.env`) — kiểm tra `.env` trước | Đừng đổi số trong `browser_engine.py`/`main_script.py` nếu đã có biến `Config`. |
| Đổi luật mã hợp lệ (dài bao nhiêu, ký tự nào, từ cấm nào) | `code_validator.py : CodeValidator.validate_code()` + `has_code_shape()`, `is_likely_fake()`, `contains_blacklisted_fragment()` | Đừng sửa `code_extraction.py` để validate — file đó chỉ trích, không kết luận. |
| Đổi cách trích mã từ text (token, marker, regex) | `code_extraction.py : extract_codes_from_message()` → `extract_plain_text_codes()` / `extract_marker_near_codes()` / `extract_codes_by_regex()` | Đừng sửa `code_validator.py` để trích thêm mã. |
| Đổi cách giải spoiler `%` + `KT<n>` + số tiếng Việt | `code_validator.py : CodeValidator._expand_placeholder_code()` + `_resolve_viet_number()`; trích spoiler: `code_extraction.py : extract_spoiler_codes()` | Parser spoiler chạy TRƯỚC trích chung; nếu nó trả kết quả (kể cả không safe) thì không được rơi về trích chung. |
| Đổi luật KJC / broadcast đa site | `kjc.py : extract_kjc_routed_items()` → `extract_kjc_spoiler_codes()`, `detect_kjc_labeled_domains()`, `build_kjc_broadcast_items()` | Đừng suy site đích từ URL kênh KJC — KJC định tuyến theo nhãn domain trong tin. |
| Đổi cách tải ảnh/video Telegram | `media_download_manager.py : MediaDownloadManager.download()` / `_multipart_download()` | Đừng tải bằng Telethon trực tiếp trong `main_script.py` ngoài đường này (trừ test). |
| Đổi OCR ảnh / video, panel, glyph, early stop | `ocr_pipeline.py : extract_site_codes()` → `find_code_panels()`, `_glyph_crop()`, `_collect_video()`, `_recognize()`, `_select_readings()`; profile: `OCRProfile.for_site()` | Đừng sửa `image_code_extractor.py` để đổi thuật toán panel — file đó chỉ là wrapper RapidOCR. |
| Đổi đọc video streaming (CTC) | `streaming_code_reader.py : StreamingCodeReader.feed()` / `flush()` / `_maybe_emit()` | Sự kiện `final=False` không bao giờ được submit; từ đã gộp phải từng xuất hiện nguyên vẹn trong một khung. |
| Đổi luồng điền form trình duyệt, chờ Turnstile, bấm submit | `browser_engine.py : _submit_code_browser_locked_inner()` (xem mục 7.2) | Đừng bypass `_submit_code_browser_locked_inner` — mọi submit trình duyệt phải qua lock theo `(domain, user)`. |
| Đổi cách chọn tab / pin tài khoản / prefill | `browser_engine.py : TabPool.acquire()` / `_pin_account()` / `_bind_accounts()`; prefill tab-only: `_prefill_tab_username()`, `_fill_tab_only_form()`, `_recover_tab_only_form()` | Đừng ghi username đè lên tab đã prefill tài khoản khác — kiểm tra `_llwin_form_matches()` trước. |
| Đổi cách đưa cửa sổ/tab lên trước | `browser_engine.py : _wake_tab_for_submit()` → `_activate_exact_tab_window()`; ép OS: `_force_chrome_window_foreground()`; manual: `_show_manual_verification_page()` | Nhớ throttle 2 s và SKIP chỉ áp dụng khi `BROWSER_FOREGROUND_ON_SUBMIT=False` (mục 9). |
| Đổi slider LLwin (gap, kéo, OS mouse, Playwright fallback) | `llwin_slider.py : solve_llwin_slider()` → `_solve_llwin_slider_playwright()` / `_run_os_mouse_drag()`; gap: `_find_gap_from_png()` | Đừng đổi selector hash trong `browser_engine.py` — selector nằm ở dict `GOCAPTCHA` trong `llwin_slider.py`. |
| Đổi cách đọc kết quả submit (toast/API) | `browser_engine.py : _ApiTimer` (`attach`, `_on_response`, `_read`, `metrics`, `mark_click`) + `_resolve_result()` + `_completed_api_result()`; phân loại: `submission_outcomes.py : classify_result()` / `record_outcome()` | Đừng kết luận thành công chỉ từ text toast — phải đối chiếu API listener (đúng mã + đúng tài khoản). |
| Đổi submit API trực tiếp (XX8) | `http_submitter.py : HttpSubmitter.submit_for_target()` → `_submit()`; claim: `database.py : CodeDatabase.claim_http_submission()` / `release_http_submission()` | Chỉ site có `direct_http_fields` + nằm trong `DIRECT_HTTP_DOMAINS` mới được đi đường này. Không replay POST. |
| Đổi pacer / throttle 429 | `submit_pacer.py : SubmitPacer.reserve()` / `throttle()` / `accepted_response()` | Đừng throttle bằng `sleep` rải rác trong engine. |
| Đổi hàng đợi theo domain, freshest-first, verification gate, defer | `scheduling.py : freshest_first_enabled()`, `verification_gate_enabled()`, `hold_until_verification_ready()`; `EarlyDispatch.on_code()` / `settle()`; `queue_manager.py : QueueManager` | Đừng đổi thứ tự hàng đợi trong `domain_code_worker` trực tiếp. |
| Đổi xoay tài khoản, done-today, exhausted | `main_script.py : _get_next_available_account()` / `_pick_account_stateless()` / `_mark_account_done_today()` / `_is_account_done_today()`; bền: `database.py : CodeDatabase.get_account_rotation()` / `save_account_cursor()` / `mark_account_exhausted()` / `mark_account_success_done()` | Stateless entry và daily-lock là 2 chế độ khác nhau — xem mục 9. |
| Đổi QQ88 sync barrier / solo fallback | `browser_engine.py : _wait_qq88_sync_barrier()` / `_qq88_sync_leave()` / `_note_qq88_sync_click()`; `main_script.py : _claim_qq88_solo_fallback()` / `_qq88_solo_fallback_active()` | Đừng submit QQ88 solo khi `sync_expected > 1` mà chưa claim solo fallback. |
| Đổi xác minh thủ công / watcher | `browser_engine.py : arm_verification_watcher()` / `wait_for_pending_verification()` / `consume_pending_verification_result()` / `_verification_pending()` | Watcher giữ tab, không tính mã là lỗi khi chờ xác minh. |
| Đổi log / dashboard / lịch sử | `logger_setup.py : setup_logger()`; `dashboard.py : update_dashboard()` / `update_latency()`; `main_script.py : append_code_history()` / `_write_history_rows()` / `build_daily_summary()` | Đừng ghi log trực tiếp bằng `print` trong luồng submit (trừ `init_systems` lúc đầu). |
| Đổi dọn ổ đĩa / RAM | `disk_guard.py : cleanup_daily()` / `cleanup_weekly()` / `ensure_disk_space()`; `monitoring.py : HealthMonitor` | Không bao giờ xoá DB, credential, profile, media chưa có marker `.done`. |
| Đổi nhận tin (push/poll/backfill/checkpoint) | `tg_ingest.py : TelegramReceiver.run()` / `on_push()` / `_hot_poll_once()` / `_poll_loop()` / `_request_backfill()`; `durable_inbox.py : DurableInbox` | Đừng reset session, đừng tự join kênh khi push gặp sự cố — chuyển sang poll và hồi phục. |
| Thêm lệnh admin Telegram | `features.py : register_default_commands()` + `CommandRegistry.register()` | Lệnh phải có timeout, chạy bất đồng bộ, chỉ admin. |
| Phân tích log offline | `analyze_code_age.py : main()` (chỉ đọc log, không sửa gì) | Đừng viết tool phân tích mới nếu chỉ cần tuổi mã + nhịp 429 — dùng file này. |
| Test download resume | `test_partial_resume.py : main()` (offline, `FakeClient`) | Chạy độc lập, không cần Telegram thật. |

---

## 5. Luồng xử lý chi tiết theo từng chặng (kèm hàm)

### 5.1. Ingest — `tg_ingest.py` + `durable_inbox.py`

- `TelegramReceiver.__init__(client, chats, sink, adapter, ...)` — nhận danh
  sách kênh từ `main_script`.
- `TelegramReceiver.on_push(event, edited)` — đường push. `offer(chat_id,
  message, edited, source)` là cổng chung cho cả push và poll; `_offer_detailed`
  kiểm tra tuổi tin (`_message_age`, `_drop_if_old`, giới hạn theo
  `_ingress_age_limit`), dedupe (`_message_dedup_key`, `_ingress_dedup_key`,
  `_prune_seen`, `_mark_persisted`).
- `TelegramReceiver._hot_loop()` / `_hot_poll_once()` / `_poll_loop()` /
  `_poll_batch()` / `_poll_once()` — đường poll. `_resolve_peers()` ánh xạ
  chat ID sang peer Telethon. `_on_flood()` xử lý FloodWait (ngủ đúng số
  giây, không retry ngay). `telegram_push_health.TelegramPushHealth`
  (`note_push`, `note_poll`, `maybe_recover`, `hold`, `run`) quyết định khi
  nào push được coi là chết và khi nào hồi phục.
- Backfill: `_request_backfill(cid, target)` → `_schedule_fetch()` →
  `_fetch_loop()` → `_process_fetch_job()` → `_commit_backfill_batch()`
  → `_drain_to_target()`. Checkpoint: `_initial_checkpoint()`,
  `_offer_dialog_top()`, `_prepare_backfill_envelope()`.
- `IngressStage.put(env)` → `_flush(batch)` → `_deliver(env, row_id)`:
  ghi row vào `DurableInbox` trước, rồi mới giao cho worker. `IngressStage`
  có `max_batch`, `maxsize`, `retries`.
- `DurableInbox` — xem mục 6.2 cho đầy đủ hàm. Quy tắc: claim bằng
  `claim(row_id)` + token; xong thì `complete_item()`; lỗi thì
  `retry()`/`defer_work_item()`/`retry_work_item()`; lỗi vĩnh viễn thì
  `mark_failed()`; lỗi OCR có thể hồi phục thì `reset_retryable_failed()`
  khi restart. `is_permanent_error()` và `_recoverable_ocr_error()` là 2
  hàm quyết định retry hay bỏ — sửa 2 hàm này là đổi chính sách retry
  của inbox.

### 5.2. Xử lý tin — `main_script.py` (điều phối chính)

- `process_telegram_message(event)` → `_process_telegram_message_traced()` →
  `_process_telegram_message_impl(event)` — cổng xử lý một tin.
- Tin text: `extract_codes_from_message()` (code_extraction) →
  `_filter_channel_codes(codes, cfg, source)` → `_exclude_spoiler_codes_from_ocr()`
  (tránh OCR lại mã spoiler đã trích được từ text).
- Tin ảnh/video: `_enqueue_ocr_media_job()` → `ocr_media_worker()` →
  `_run_ocr_media_job()` → `_run_ocr_media_job_inner()` →
  `process_image_from_telegram()` / `_process_image_inner()` /
  `_extract_site_codes_local()` → `submit_codes_from_image()`.
  Cache OCR: `_ocr_file_cache_key()`, `_ocr_cache_get()`, `_ocr_cache_put()`,
  `_cached_photo_ocr()`; cache file video: `_ocr_video_cache_path()`,
  `_prune_ocr_video_file_cache()`, `_prune_ocr_video_partial_cache()`.
  Giới hạn: `_wait_for_ocr_admission()` (OCR admission, pause khi
  `monitoring.ocr_admission_paused()`).
- Fanout (một mã → nhiều tài khoản): `_build_distinct_code_items()` (mã
  khác nhau), `_build_spoiler_dispatch_items()` (mã spoiler),
  `_build_stateless_entry_items()` (chế độ stateless, xem mục 9),
  `_fanout_code_item(item, count, start_index, account_count)`,
  `_fanout_preferred_username(domain, item)`.
- Hàng đợi theo domain: `get_domain_queue(domain)`, `_enqueue_domain_item()`,
  `_next_domain_dispatch_item()`; worker: `domain_code_worker(domain,
  target_url, worker_id)` → `_submit_code_with_account_retries()`.
- Submit an toàn: `submit_code_safe(user, code, target_url, systems,
  sync_expected, tab_only, sync_group)` → `submit_code_with_delay()` →
  hoặc `BrowserEngineAdapter.submit_for_target()` (trình duyệt) hoặc
  `HttpSubmitter.submit_for_target()` (API trực tiếp, chỉ XX8).
  `_mark_code_used_if_final(domain, code, status)` chỉ đánh dấu đã dùng
  khi kết quả là cuối cùng (final), không đánh dấu khi mập mờ.
- Dedupe trong main: `is_site_code_duplicate(domain, user, code)` /
  `_clear_site_code_duplicate()` (dựa trên `BotState._site_code_seen`,
  dọn bằng `_prune_site_code_seen()`); `_defer_budget_exhausted(domain, code)`.
- Lịch sử: `append_code_history(...)` → `_write_history_row()` /
  `_write_history_rows()` → `_history_writer_loop()` (ghi batch, không ghi
  trực tiếp trong luồng submit); `build_daily_summary()` tổng hợp theo ngày.

### 5.3. Trích mã và validate — thứ tự bắt buộc

Thứ tự xử lý một tin (đừng đảo lộn):

1. `code_extraction.extract_spoiler_codes(event, target_url)` — spoiler trước.
2. `code_extraction.extract_codes_from_message(event, raw_text, target_url,
   channel_name, include_text_after_spoiler, spoiler_codes)` — text chung.
   Bên trong: `remove_noise_from_text()` → tách dòng → `line_has_code_marker()`
   / `line_is_noise()` / `_line_has_vietnamese()` → `extract_tokens_from_line()`
   → `validate_candidate(code, target_url, source)` → `unique_keep_order()`.
3. `kjc.extract_kjc_routed_items(event, channel_name)` — riêng kênh KJC
   (kiểm tra `is_kjc_special_channel(chat_id)` trước).
4. `code_validator.CodeValidator.validate_code(code, target_url,
   filter_group_name, source)` — kết luận cuối cùng một mã có được submit
   không. Bên trong: `clean_code()` → `has_code_shape()` →
   `is_likely_fake()` / `contains_blacklisted_fragment()` /
   `is_site_allowed_for_group()` / `is_composed_of_common_words()` /
   `is_text_word()` / `is_sequential_code()` / `looks_like_domain_or_link()`
   / `detect_site_identity()`. Spoiler: `_expand_placeholder_code()` +
   `_resolve_viet_number()`. Có cache: `validate_code_cached()` /
   `_validate_code_cached()` (đừng bỏ cache nếu không muốn validate chậm).
5. `channel_rules` — luật riêng theo kênh, chạy trước/kèm validate:
   `_is_ocr_allowed_channel()`, `_has_qq88_code_link()`,
   `_is_qq88_code_post()`, `_qq88_ocr_shape_ok()`, `_hi88_code_shape_ok()`,
   `_has_hi88_code_link()`, `extract_hi88_near_link_codes()` (code_extraction).
6. Chuẩn hoá: `code_identity.normalize_code(code, domain, force_uppercase)`
   và `normalize_code_domain(domain)` — mọi nơi (trích, hàng đợi, submit,
   DB) phải dùng cùng 2 hàm này, không tự `.upper()`/`.strip()` riêng lẻ.

### 5.4. OCR — `ocr_pipeline.py` + `image_code_extractor.py` + `streaming_code_reader.py`

- `image_code_extractor.init_image_extractor()` / `get_image_extractor()` /
  `warmup_image_extractor()` — khởi tạo RapidOCR (gọi 1 lần lúc start,
  `_OCR_EXECUTOR` riêng). `ImageCodeExtractor._run_rapid_ocr(pil_img, ...)`,
  `confirm_code_readings(image_path, readings)` (xác nhận nhiều lần đọc),
  `read_image_regions(image)`, `recognize_code_regions(bgr_images)`,
  `confirm_video_readings(video_path, batches, track_motion)`,
  `get_streaming_recognizer()`.
- `ocr_pipeline.OCRProfile.for_site(url, cfg)` — profile OCR theo site
  (độ dài mã, tiền tố, crop, early stop…). `OCRProfile.candidate(text)`
  kiểm tra một chuỗi đọc được có phải ứng viên mã không.
- `ocr_pipeline.find_code_panels(bgr, profile)` — tìm panel theo pixel.
  Riêng XX8: `_xx8_anchor_components()` + `_xx8_text_mask()`; riêng LLwin
  grid: `_llwin_grid_cells()` + `_llwin_in_grid()`.
- `ocr_pipeline._glyph_crop(bgr, box, profile, frame)` — cắt đúng vùng chữ.
  `_same_artwork(a, b, tolerate_edges)` — hai khung có phải cùng một artwork
  không (để dedupe quan sát).
- Video: `_video_sample_limits()` → `_collect_video(path, profile, metrics,
  emit)` → `_recognize()` / `_recognize_cached()` → `_select_readings()` →
  `_confirm_sparse_appearances()` (mã xuất hiện thưa thì xác nhận thêm).
  `_extract_streaming_video()` là đường streaming (CTC); `_fallback_codes()`
  là đường fallback khi không tìm được panel (detector thần kinh).
- `streaming_code_reader.StreamingCodeReader` — `feed(bgr, t)` từng khung,
  `_maybe_emit(cell, t, flush)`, `flush()` cuối video. `CtcAlnumRecognizer`
  (`from_rapidocr`, `_prep`, `read`) là recognizer chữ số/chữ cái.
  `Reading.fuse(readings)` gộp nhiều lần đọc.
- Giới hạn: `_early_stop_samples()`, `_early_emit_allowed()`,
  `_early_emit_confidence()`, `_coarse_factor()` — đừng bỏ các giới hạn này
  nếu không muốn OCR video ngốn RAM/CPU vô hạn.

### 5.5. Submit — xem mục 7 (luồng submit là phần dài nhất, tách riêng)

---

## 6. Dữ liệu và trạng thái

### 6.1. `BotState` (`main_script.py`) — trạng thái RAM toàn cục

- `_site_code_seen: dict` — mã đã thấy theo (site, mã, tài khoản), chống
  trùng trong phiên. Dọn bằng `_prune_site_code_seen()` (chỉ cắt mục quá
  TTL, không `clear()` toàn bộ — xóa hết sẽ mất chống trùng đúng lúc máy
  quá tải, và `_emergency_ram_cleanup()` cũng chỉ gọi hàm prune này).
- `_daily_used: set`, `_daily_date` — tài khoản đã success trong ngày.
  Reset theo ngày bằng `_refresh_daily_state()` + `daily_reset_watchdog()`.
- `_channel_account_index`, `_domain_account_cursor`,
  `_fanout_account_cursor`, `_rotation_loaded_domains` — con trỏ xoay tài
  khoản (bền qua DB, xem 6.2).
- `_inflight_codes`, `_inflight_accounts` — mã/tài khoản đang xử lý.
- `_processed_message_hashes` — hash tin đã xử lý (dọn bằng
  `_prune_processed_message_hashes()`).
- `context_locks: dict[(domain, user) -> asyncio.Lock]` — lock submit theo
  từng (domain, tài khoản). `browser_engine.submit_code_browser()` dùng
  đúng mẫu này (kiểm tra `if key not in ...` trước khi tạo lock, không
  dùng `setdefault` vì `setdefault` luôn evaluate `Lock()` dù key đã có —
  đó là bug v8-bugfix #2 đã sửa, đừng viết lại kiểu cũ).
- `bg_tasks: set` — task nền, đăng ký bằng `schedule_tracked_task()`.

### 6.2. SQLite — 2 DB, đừng nhầm

**`data/code_history.db`** (`database.py : CodeDatabase`, `init_database()`):

| Bảng | Ghi bằng hàm | Dùng để |
|---|---|---|
| `code_submission` | `record_submission(code, account, website, status, result, attempt)` | Lịch sử submit từng lượt |
| `used_codes` | `mark_code_used(domain, code)` / `is_code_used(domain, code)` / `unused_codes(domain, codes)` | Dedupe bền: mã đã dùng thì không nhập lại |
| `submission_log` | (ghi log submit) | Truy vết lượt submit |
| `http_submission_guard` | `claim_http_submission(domain, account, code)` / `release_http_submission(...)` | Claim chống gửi trùng API trực tiếp |
| `account_stats`, `website_stats` | `_write_stats_locked(account, website, status, now)` (ghi batch, `stats_batch_size` mặc định 50) | Thống kê |
| `account_rotation` | `get_account_rotation(domain, date)` / `save_account_cursor(domain, cursor, date)` | Con trỏ xoay tài khoản theo ngày |
| `account_exhausted` | `mark_account_exhausted(domain, account, date)` | Tài khoản hết lượt/khoá |
| `account_success_done` | `mark_account_success_done(domain, account, date)` | Tài khoản đã success trong ngày |

**`data/telegram_inbox.db`** (`durable_inbox.py : DurableInbox`):

| Bảng | Ý nghĩa |
|---|---|
| `telegram_inbox` | Row tin Telegram (nội dung, chat, trạng thái, số lần thử) |
| `telegram_inbox_items` | Work item tách từ một row (một tin có thể tách nhiều item mã) |
| `telegram_poll_cursor` | Checkpoint poll theo từng kênh |

Cài đặt kết nối chung: `sqlite_support.connect_database()` +
`ensure_performance_indexes()`. Session Telethon dùng
`main_script.ResilientSQLiteSession` (riêng, không phải 2 DB trên).

### 6.3. `Config` (`config.py`) — nhóm biến theo chức năng

- Đọc env: `get_int_env`, `get_float_env`, `get_positive_int_env`,
  `get_positive_float_env`, `get_bool_env`, `get_int_list_env`,
  `floored_interval` (giới hạn dưới cho interval).
- Kênh: `CHANNEL_CONFIG` (31 kênh, khóa chat ID), `ACTIVE_DOMAINS`
  (rỗng = lấy toàn bộ), `DOMAIN_TO_CHANNEL_URL` (suy ra từ config).
- Trình duyệt: `EDGE_CDP_HOST/PORT` (9222), `EDGE2_*` (9223),
  `EDGE_PROFILE_1/2`, `EDGE_AUTO_LAUNCH`, `EDGE2_DOMAINS` (mặc định:
  XX8, QQ88, HI88, V79 đi Edge 2), `EDGE2_AUTO_OPEN_TABS`,
  `COCCOC_*` (mặc định tắt).
- Submit: `MAX_CONCURRENT_SUBMITS` (4), `MAX_CONCURRENT_SUBMITS_PER_DOMAIN`
  (3), `MAX_CONCURRENT_PROCESSING` (16), `MAX_CONCURRENT_MEDIA_DOWNLOADS`
  (4), `MAX_CONCURRENT_OCR` (2), `MAX_CONCURRENT_BROWSERS` (2),
  `TAB_POOL_SIZE` (3), `DYNAMIC_TAB_MAX_PER_DOMAIN` (3).
- Tab: `DOMAIN_TAB_LIMITS` (XX88=3, V79=3, còn lại 1),
  `PARALLEL_DOMAIN_TAB_LIMITS` (XX88=3, V79=2, XX8/QQ88/MM88/RR88/GG88=2,
  HI88=1, LLwin=1), `XX88_MIN_TABS`=3, `V79_MIN_TABS`=2.
- Tuổi mã: `CODE_MAX_AGE_SECONDS` (chung, mặc định 120),
  `SITE_CODE_MAX_AGE_SECONDS` theo từng site — **trong zip này XX88 = 120**
  (không còn 45 như bản v5 cũ; comment trong code giải thích: Turnstile
  được retry bất đồng bộ nên mã trong hàng đợi cần sống lâu hơn trong khi
  mỗi lần submit vẫn bị giới hạn thời gian). Các site khác dùng chung 120
  trừ khi `.env` ghi đè `<SITE>_CODE_MAX_AGE_SECONDS`.
- Hàng đợi: `FRESHEST_FIRST_DOMAINS` (mặc định XX88),
  `VERIFICATION_GATE_DOMAINS` (mặc định XX88), `DEFER_BUDGET_DOMAINS`,
  `SITE_SUBMIT_GAPS`, `OCR_VIDEO_EARLY_STOP_DOMAINS`,
  `OCR_VIDEO_EARLY_EMIT_DOMAINS`, `OCR_VIDEO_COARSE_DOMAINS`.
- Foreground: `BROWSER_FOREGROUND_ON_SUBMIT` (mặc định True),
  `MANUAL_VERIFICATION_FOREGROUND`,
  `MANUAL_VERIFICATION_FOREGROUND_DOMAINS`,
  `FOREGROUND_ON_VERIFICATION_SUBMIT`, `SKIP_BRING_TO_FRONT_DOMAINS`
  (mặc định trong code chỉ QQ88; `.env` thực tế mở rộng thêm).
- Direct HTTP: `DIRECT_HTTP_DOMAINS` (mặc định chỉ XX8),
  `BROWSER_ONLY = not DIRECT_HTTP_DOMAINS`.
- Captcha: `CAPTCHA_SAFE_DOMAINS`, `ADDITIONAL_CAPTCHA_SAFE_DOMAINS`
  (LLwin), `QQ88_MANUAL_CONFIRM` (mặc định False),
  `QQ88_MANUAL_TIMEOUT_S` (25).
- Log/DB: `LOG_FILE` (`logs/bot_activity.log`),
  `DATABASE_PATH` (`data/code_history.db`),
  `TELEGRAM_INBOX_DB_PATH` (`data/telegram_inbox.db`),
  `DASHBOARD_ENABLED` (mặc định True).
- Tài khoản hiệu dụng: `_build_effective_domain_accounts()` +
  `_effective_domain_accounts_cached()` + `get_effective_domain_accounts(domain)`
  — `.env` có thể ghi đè danh sách tài khoản trong `CHANNEL_CONFIG`.
  `_normalize_active_domain()` / `_normalize_config_domain()` chuẩn hoá
  domain trước khi tra cứu — luôn dùng 2 hàm này, đừng so sánh domain
  bằng chuỗi thô.

### 6.4. Log và lịch sử file

- Log chính: `logs/bot_activity.log` (`logger_setup.setup_logger()`).
  Log xoay theo ngày + kích thước; log Telethon lỗi tách riêng
  (`TelethonErrorOnlyFilter`, `TelethonErrorForwarder`); chống lặp
  (`ConsoleRepeatFilter`, `ConsoleWarnThrottleFilter`, `warning_once`);
  context theo kênh (`ContextTagFilter`, `set_log_context`);
  file log riêng theo kênh (`PerChannelFileHandler`); tắt QuickEdit
  Windows (`_disable_windows_quick_edit`) để console không bị đứng khi
  click nhầm.
- Lịch sử code theo ngày: `logs/code_history/code_history_YYYY-MM-DD.csv`
  và `.jsonl`, cộng `daily_summary_YYYY-MM-DD.csv` — ghi bởi
  `append_code_history` / `build_daily_summary` (xem 5.2). Đây là dữ liệu
  để đo hiệu quả theo ngày, không phải DB chính.
- Screenshot kết quả: `logs/screenshots/` (ghi bởi
  `media_helpers.take_result_screenshot`, có throttle
  `_screenshot_throttled`, dọn cũ bằng `_prune_screenshots`).
- Debug slider: thư mục tạm riêng cho từng lượt
  (`llwin_slider_<user>_<code>_…`), chỉ ghi khi caller truyền `debug_dir`.

---

## 7. Luồng submit trình duyệt — đọc kỹ mục này trước khi sửa engine

### 7.1. Điểm vào và lock

- `browser_adapter.BrowserEngineAdapter.submit_for_target(user, code,
  target_url, systems, sync_expected)` — main gọi qua adapter này.
  Trả về `BrowserResult` (enum `BrowserResultKind`).
- `browser_engine.submit_code_browser(user, code, target_url, systems,
  sync_expected=1)` — lấy lock theo key `f"{domain}|{user}"` trong
  `bot_state.context_locks`, rồi gọi `_submit_code_browser_locked_inner(...)`.
  Sau cùng, nếu là QQ88 thì `_qq88_sync_leave(code, user, sync_expected)`.
- `browser_engine.submit_code_browser_tab(code, target_url, systems,
  sync_group=None)` — **tab-only**: submit trên một tab đang rỗi mà
  **không chọn và không ghi tài khoản của tab đó**. Dùng cho chế độ
  stateless / tab đã prefill (xem 7.5). Đừng dùng hàm này thay cho
  `submit_code_browser` trong luồng thường — nó không pin tài khoản.
- `_submit_code_browser_locked_inner(user, code, target_url, systems,
  sync_expected, tab_only, sync_group, identity)` — hàm dài nhất của
  engine, chứa toàn bộ các bước dưới. Mọi sửa đổi submit trình duyệt đều
  nằm trong hàm này hoặc trong các hàm con nó gọi.

### 7.2. Các bước trong `_submit_code_browser_locked_inner` (theo thứ tự)

1. **Lấy tab:** `TabPool.acquire(domain, account)` (xem 7.3). Nếu tab bị
   kẹt/xác minh thì `wait_for_verification_ready(domain, timeout)` hoặc
   `verification_blocked(domain)`.
2. **Đi tới form:** `get_or_launch_browser_context(user, force_reconnect,
   domain)` → `get_context_for_endpoint(ep)` → `_connect_endpoint(ep)`
   (CDP, `_reset_playwright_driver` khi cần). `_needed_endpoints()` /
   `endpoint_for_domain(domain)` chọn Edge 1 hay Edge 2.
   `preload_browsers_and_accounts(account_targets)` mở sẵn tab lúc start.
   `dynamic_tab_watcher()` dọn tab idle (`TabPool.collect_garbage`,
   `cleanup_idle_memory`).
3. **Đưa tab lên trước:** `_wake_tab_for_submit(page, domain)` (xem 9).
4. **Điền form:** `_fill_profile_form(page, domain, user, code)` — điền
   theo selector của `SiteProfile`. Riêng XX88: `_xx88_submit_readiness(page)`
   chạy song song với điền form (đừng chờ token xong mới điền — đó là
   tối ưu đã có). Riêng V79: `_ensure_v79_captcha_image_ready(page,
   target_url)` (dựa trên `_probe_v79_captcha_image`) trước khi điền.
   Kiểm tra form sẵn sàng: `_site_form_ready(page, domain, wait, timeout_ms)`
   (fast window 1500 ms, bản v10) và `_ensure_submission_ui(page, domain,
   target_url, key)`.
5. **Tab-only prefill (28/10):** nếu tab đã có username prefill từ cấu hình
   thì `_prefill_tab_username()` / `_fill_tab_only_form()` điền tiếp, không
   ghi đè tài khoản. `_llwin_form_matches(page, user, code)` kiểm tra form
   có khớp tài khoản/mã không; `_log_tab_without_account(page, domain)`
   là diagnostic (tối đa 1 lần/60 s/domain) khi tự điền thất bại trước khi
   báo `TAB_UNAVAILABLE` — đọc log này khi tab trống username.
   `_recover_tab_only_form()` khôi phục form tab-only khi bị lỗi.
6. **Pacer:** `SubmitPacer.reserve(domain, account, account_gap, domain_gap)`
   (gap lấy từ `Config.SITE_SUBMIT_GAPS`). QQ88: `_submit_button_ready()` +
   `_wait_qq88_sync_barrier(code, user, expected)` (barrier đồng bộ khi
   `sync_expected > 1`; `_note_qq88_sync_click()` ghi lại lần click).
7. **Challenge snapshot:** `_challenge_token_snapshot(page)` — chụp token
   Turnstile/reCAPTCHA hiện tại. `_challenge_token_consumed(page, kind,
   token)` đánh dấu token đã dùng. `_refresh_used_challenges(page)` làm
   mới token cũ — riêng XX88 có clearance cookie thì không reset
   Turnstile (xem 7.6).
8. **Slider LLwin (nếu có):** xem 7.4.
9. **Bấm submit:** `click_submit_fast(page, domain)` — click nhanh, 1 lần.
   Trước click: `_ApiTimer.mark_click()` bắt đầu tính giờ API.
   Sau click: `_ApiTimer` nghe request/response (xem 7.7).
10. **Đọc kết quả:** `_resolve_result(api_fut, dom_factory, api_pending,
    api_timeout_seconds, late_dom_factory)` — kết hợp API + DOM.
    `detect_result_text(page, domain, before_text, selector_only)` đọc
    text kết quả; `_filter_nextjs_noise()` loại nhiễu Next.js;
    `_is_stale_static_text()` loại text cũ trước click;
    `_is_transient_captcha_text()` nhận diện text captcha thoáng qua;
    `_is_site_shell_result_candidate()` / `_is_decisive_result()` quyết
    định text có đủ chắc để kết luận không; `_code_matches_expected()`
    kiểm tra mã trong kết quả có khớp mã đã submit không.
11. **Dọn dẹp:** `_dismiss_result_popup(page, domain)`,
    `_clean_page_after_submit(page, domain, target_url, key, force_full)`
    (quick-clean: Escape + chờ 0.15 s + thử lần 2 cùng tab rồi mới reload;
    `QUICK_CLEAN_RETRY_BEFORE_RELOAD` mặc định True),
    `_quick_clean_page(page, key, domain)`, `_close_unwanted_popups(page)`,
    `_dismiss_pre_submit_popups(page, domain)`.
    `_reload_page_and_refill()` khi tab cần reload + điền lại.
12. **Ghi kết quả:** `submission_outcomes.record_outcome(...)` +
    `database.record_submission(...)` + `append_code_history(...)` +
    log `[METRIC]` (xem mục 10).

### 7.3. `TabPool` (`browser_engine.py`) — hàm nào làm gì

- `__init__(max_per_domain, per_domain_overrides)`; `_max_for(domain)` —
  giới hạn tab = min(profile `tab_slots`, `DOMAIN_TAB_LIMITS`,
  `PARALLEL_DOMAIN_TAB_LIMITS`, pool) theo từng domain.
- `acquire(domain, account)` / `_try_acquire(domain, account)` — lấy tab
  cho (domain, tài khoản), pin tài khoản (`_pin_account`), bind danh sách
  (`_bind_accounts`). `_find_existing_page(domain)` /
  `_claim_existing_or_new(domain)` / `_new_tab_for_domain(domain)` /
  `_create_bot_tab(domain)` — tái sử dụng tab cũ trước, mở tab mới sau.
- `prefilled_accounts(domain)` / `refresh_prefilled(domain)` /
  `get_prefilled_accounts(domain)` (hàm module) — tài khoản đã prefill
  sẵn trên tab (dùng cho tab-only).
- `mark_account_exhausted(domain, account)` /
  `_account_is_exhausted()` / `_reject_exhausted_account()` /
  `reset_exhausted_accounts()` — tài khoản hết lượt thì không được cấp tab.
- `open_tab_count(domain)` / `available_tab_count(domain)` /
  `available_user_tab_count(domain)` / `live_user_tab_count(domain)` —
  đếm tab (dùng cho log `[Tab-Slots]` và cho verification gate).
- `verification_blocked(domain)` — domain có bị chặn bởi tab đang chờ
  xác minh không.
- `discover_user_tabs()` — quét tab người dùng đã mở sẵn (không phải tab
  bot tạo) để tái sử dụng.
- `collect_garbage(idle_ttl, min_tabs_per_domain)` /
  `cleanup_idle_memory(...)` — dọn tab idle, compact/reload theo lịch.
- `recover_endpoint(ep)` — khôi phục endpoint CDP khi mất kết nối.
- `_event_for(domain)` / `_notify_available(domain)` — báo tab rỗi cho
  worker đang chờ.

### 7.4. Slider LLwin — `llwin_slider.py` (667 dòng, bản trong zip này)

- Selector (dict `GOCAPTCHA`, đã verify ngày 26/10): wrapper
  `.gocaptcha-module_wrapper__Kpdey`, body `KJKNu`, picture `LRwbY`,
  tile `.index-module_tile__8pkQD`, dragBlock `bFlwx`, dragSlideBar `noauW`,
  iconBlock `mVB8B`. Tile locator có fallback: div trong body chứa ảnh
  `data:image/png` — hash rebuild không làm hỏng toàn bộ solver.
- `is_llwin_slider_visible(page)` — chỉ kiểm tra wrapper có hiện không
  (bản trong zip này **chưa** có fallback theo text modal — đó là bản v2
  giao riêng, không có trong zip).
- `solve_llwin_slider(page, max_attempts=2, debug_dir, on_manual_required,
  on_os_mouse_required)` — cổng chính. Thử OS mouse trước, fallback
  Playwright sau.
- `_find_gap_from_png(png_bytes, piece_box)` — tìm gap bằng OpenCV
  (edge-template), trả về `{gap_x, gap_y, dx, dy, score, second_score}`.
  Chỉ kéo khi `score >= 0.20` và `dx > 0` (ngưỡng trong code, xem
  `_solve_llwin_slider_playwright` và `_run_os_mouse_drag`).
- `_solve_llwin_slider_playwright(page, max_attempts=2, debug_dir)` —
  kéo bằng chuột Playwright, chuyển động easing `_move_eased(page, x0, y0,
  from_off, to_off, delay_scale)`, có in-hold correction (đo
  `tile_delta / drag_delta` để học ratio trong chính lần kéo đó).
- OS mouse: `_run_os_mouse_drag(page, on_os_mouse_required, debug_dir)` →
  `_perform_os_drag(metrics, handle_box, dx, stop_event)`; tọa độ:
  `_viewport_to_screen(metrics, bounds, x, y)` (DPI/zoom aware, dùng JS
  `_VIEWPORT_METRICS_JS`: `innerWidth/innerHeight/devicePixelRatio/
  visualViewport.scale`); focus: `_focus_edge_for_os_mouse(page)` +
  `_activate_edge_window(marker)` + `_raise_window_z_order(user32, hwnd)`.
  **OS mouse dùng chuột thật của Windows và giữ `_OS_MOUSE_LOCK`
  (asyncio.Lock) — các lần kéo và các lần focus cửa sổ Edge đều serialize
  qua lock này. Đừng gọi solve song song, đừng focus cửa sổ khác trong
  lúc đang kéo.** Cảnh báo trong code: `OS_MOUSE_WARNING` — "Bot đang
  điều khiển chuột thật để kéo Captcha. Vui lòng không chạm vào chuột!"
- Debug: screenshot chỉ ghi khi caller truyền `debug_dir` riêng cho từng
  lượt — song song nhiều tab không được dùng chung thư mục debug.
- **Race slider vs API** (`browser_engine._solve_llwin_slider_or_api(solve_coro,
  api_fut)`): chạy solver nhưng dừng sớm khi API đã trả kết quả quyết định.
  Trả về `(slider_ok, api_text)`. **`slider_ok` chỉ True khi chính solver
  trả True — không bao giờ suy ra từ API.** Solver bị hủy luôn được chờ
  nhả chuột xong trước khi hàm trả về, kể cả khi task cha bị hủy. Lỗi
  solver được ném lại, trừ khi đã có kết quả API.
- Hook trong engine: sau click, poll slider tối đa 2 s (bản logs-2 v1)
  rồi giải, xong đi tiếp luồng đọc kết quả; hỏng → `PENDING_VERIFICATION`
  + `LLWIN_SLIDER_FAILED`, `keep_page=True`, không tính mã lỗi.
  Watcher (7.8) là lưới an toàn khi slider hiện muộn.

### 7.5. Tab-only / stateless entry (28/10) — đừng nhầm 2 chế độ

- **Tab-only:** tab đã prefill username từ cấu hình; submit chỉ điền mã,
  không chọn/ghi tài khoản. Hàm: `_prefill_tab_username()`,
  `_fill_tab_only_form()`, `_recover_tab_only_form()`,
  `submit_code_browser_tab()`. Diagnostic khi tự điền thất bại:
  `_log_tab_without_account()` (log sửa thành "đã thử tự điền từ cấu hình
  nhưng không được").
- **Stateless entry:** `_stateless_entry_enabled()` (đọc `Config`) bật
  chế độ không khóa tài khoản theo ngày. Hàm: `_pick_account_stateless(domain,
  accounts, preferred_username)` (thay cho `_get_next_available_account`),
  `_build_stateless_entry_items(items)`, `_uses_tab_dispatch(domain)`.
  Trong chế độ này, **không còn khóa tài khoản theo ngày** (marker
  `stateless-entry` trong engine) — đừng áp logic `_mark_account_done_today`
  / `_is_account_done_today` vào luồng stateless nếu chưa kiểm tra cờ.
- 2 chế độ có thể kết hợp (stateless + tab dispatch) nhưng phải qua đúng
  hàm `_build_stateless_entry_items` / `submit_code_browser_tab`, không
  tự chế đường riêng.

### 7.6. XX88 — readiness, clearance cookie, Turnstile

- `_arm_xx88_readiness(page, need_button)` — arm watcher readiness cho
  XX88 (probe, không lặp mỗi 0.75 s một cách vô tội vạ; khẳng định
  foreground một lần lúc arm). `_xx88_readiness_pending(page)` kiểm tra
  còn task readiness không.
- `_xx88_submit_readiness(page)` — readiness lúc submit (chạy song song
  với điền form). `_wait_for_turnstile_ready(page, domain, timeout_s)` +
  `_wait_for_challenge_token_retries(page, domain)` — chờ token, có
  retry có giới hạn.
- **Clearance cookie (28/10):** `_has_clearance_cookie(page, domain)` —
  True khi cookie `cf_clearance` còn hạn (session `expires<=0` hoặc chưa
  hết hạn). `_xx88_cookie_clearance(page)` chỉ gọi helper với
  `"xx88code.com"`. `_refresh_used_challenges(page)` — nếu token stale +
  cờ `SKIP_TURNSTILE_RESET_WITH_CLEARANCE_COOKIE` (mặc định True) + còn
  cookie của đúng domain thì xóa used tokens, trả True, **không**
  `turnstile.reset()`. Quick-clean lần 1 fail thì Escape + chờ 0.15 s +
  thử lần 2 cùng tab rồi mới reload; `QUICK_CLEAN_RETRY_BEFORE_RELOAD`
  mặc định True. **Guard bắt buộc:** `page_domain = _normalize_domain(page.url
  or "")` rồi gọi helper với `page_domain` đó, không quét toàn bộ cookie
  của context; và phải có `and page_domain` — domain rỗng thì rơi xuống
  `turnstile.reset()` (thà reset thừa còn hơn bỏ sót token cũ →
  `TOKEN_NOT_READY`). Kiểm tra bằng grep: `_has_clearance_cookie(page,
  page_domain)` phải ra đúng 1 dòng, và dòng `and page_domain` phải nằm
  ngay trên nó trong cùng khối if.
- `_wait_turnstile_solved(page, timeout_seconds)` / `_turnstile_solved(page)`
  / `_recaptcha_checked(page)` / `_wait_and_click_verify_button()` /
  `_click_verify_button_now(page)` / `click_verification_button_if_present(page,
  domain)` — các hàm bấm nút xác minh (Turnstile và reCAPTCHA Enterprise
  của QQ88, marker `qq88-recaptcha-verify`).
- `_record_captcha_occurrence(domain)` / `_send_captcha_admin_alert(domain,
  account, message)` — ghi nhận và báo admin khi captcha xuất hiện
  (có throttle, đừng spam admin).

### 7.7. `_ApiTimer` — nghe lén API để đọc kết quả

- `__init__(page, endpoint, domain, submitted_code, submitted_account)`;
  `attach()` / `detach()` gắn listener vào page.
- `_wanted(url, method)` / `_wanted_request(request)` /
  `_body_matches_request(request)` / `_body_values(value, depth)` — chỉ
  khớp request có đúng endpoint, đúng mã, đúng tài khoản đã submit.
- `_on_request()` / `_on_request_failed()` / `_on_response()` /
  `_read(response)` — đọc response, tách message (`_response_to_result_text`,
  xử lý cả dạng API trả `{"message": [{"text": ...}]}` — bug v8 #3).
- `mark_click()` — mốc bắt đầu tính giờ API (gọi ngay trước click).
- `metrics()` — trả về `api_ms`, `api_status`, `pre_api_ms`, `ttfb_ms`,
  `body_ms` cho log `[METRIC]`.
- `unconfirmed_result()` — kết quả chưa xác nhận được (để phân loại
  `AMBIGUOUS`).
- `_completed_api_result(api_fut)` / `_remaining_api_wait_seconds(api_timer,
  domain)` — kiểm tra API đã trả kết quả quyết định chưa và còn bao nhiêu
  thời gian chờ.

### 7.8. Watcher xác minh — `browser_engine.py`

- `arm_verification_watcher(page, domain, code, user, target_url, key,
  systems, llwin_slider_already_attempted)` — arm watcher cho một lượt
  đang chờ xác minh. Tham số cuối cho biết slider đã thử chưa (để watcher
  không thử lại vô hạn).
- `wait_for_pending_verification(domain, account, timeout_seconds)` —
  chờ kết quả xác minh đang chờ. `_verification_pending(page)` kiểm tra
  còn pending không. `_verification_result_key(domain, account, code)` /
  `consume_pending_verification_result(domain, account, code)` — lấy kết
  quả pending theo key.
- `_cleanup_after_verification_watcher(page, domain, target_url, key, tag,
  popup_wait_seconds)` — dọn sau watcher (marker `cleanup-verify`: 1 cửa
  duy nhất cho watcher, đừng tạo thêm nhánh dọn riêng).
- `_wait_for_site_result_popup(page, domain, timeout_seconds)` /
  `_site_popup_visible_now(page, domain)` — chờ popup kết quả của site.
- `_manual_verify_hint_now(page)` — gợi ý xác minh thủ công ngay lúc đó.
- `browser_watchdog()` — watchdog toàn cục cho browser (kill tab/worker
  kẹt quá lâu). `_recover_browser_endpoint(ep)` / `_observe_tab_verification()` /
  `_observe_all_tab_verifications(pool)` — quan sát và khôi phục tab.
- `_show_manual_verification_page(page, domain, tag)` — đưa tab xác minh
  lên trước cho người dùng hoàn tất bằng tay (xem 9).

---

## 8. Site, kênh, tài khoản — bảng tra cứu (từ code, không từ trí nhớ)

### 8.1. Site profiles (`browser_site_profiles.py`)

| Domain | Origin | Tab slots (profile) | Endpoint API nghe lén |
|---|---|---|---|
| llwincode.com | https://llwincode.com/ | 1 | api.llwincode.com/codes/use-code-public |
| getcodexx8bonus.pages.dev (XX8) | https://getcodexx8bonus.pages.dev/ | 2 | api.xx8web.vip/Promotion/GetCODEXX8Bonus (API trực tiếp) |
| xx88code.com | https://xx88code.com | 3 | api.xx88code.com/codes/use-code-public |
| tangquaqq88.com (QQ88) | https://tangquaqq88.com | 2 | api-code-qq88-v2.royalapps.net/client/giftcode |
| hi88-freecode.pages.dev (HI88) | https://hi88-freecode.pages.dev | 1 | api-code-hi88-v2.royalapps.net/client |
| livemm88.net (MM88) | https://livemm88.net/nhap-code | 2 | api.xx88code.com/codes/use-code-public |
| liverr88.net (RR88) | https://liverr88.net/nhap-code | 2 | (nghe POST chứa "code" + đúng mã/tài khoản) |
| gg88live.tv (GG88) | https://gg88live.tv/nhap-code | 2 | api.gg88code.com/codes/use-code-public |
| v79code.com (V79) | https://v79code.com | 2 | api.v79code.com/codes/use-code-public |

Lưu ý: số tab thực tế = min(profile `tab_slots`, `DOMAIN_TAB_LIMITS`,
`PARALLEL_DOMAIN_TAB_LIMITS`, pool) — xem mục 6.3. Đừng chỉ nhìn một cột.
`get_site_profile(domain)` chuẩn hoá domain (bỏ scheme, bỏ `www.`,
lấy hostname) trước khi tra. `validate_profiles()` chạy lúc import và
ném `ValueError` nếu profile sai — profile sai thì bot không lên, đó là
cố ý.

### 8.2. Kênh (31 kênh, `config.py : CHANNEL_CONFIG`)

Bảng đầy đủ (chat ID, tên, site đích, filter group) — dùng để đối chiếu
log (log ghi `chat=-100…`):

| Chat ID | Tên kênh | Site đích | Filter group |
|---|---|---|---|
| -1003873843218 | LLwin PHÁT CODE MIỄN PHÍ | llwincode.com | llwin |
| -1003506071961 | LLwin DỊCH VỤ GIAI NHÂN | llwincode.com | llwin |
| -1003903971775 | LLwin GIẢI TRÍ 24H | llwincode.com | llwin |
| -1004395536862 | XX8 - PHÁT CODE MỖI NGÀY | getcodexx8bonus.pages.dev | xx8 |
| -1002528908352 | KJC GÁI XINH | xx88code.com | multi_site_strict |
| -1003503954906 | KJC - ĐỒNG HÀNH THỂ THAO | xx88code.com | multi_site_strict |
| -1002817093108 | PHÁT CODE XX88 | xx88code.com | multi_site_strict |
| -1002768264448 | XX88 THỂ THAO ESPORT | xx88code.com | multi_site_strict |
| -1002730903277 | XX88 DỊCH VỤ GIAI NHÂN | xx88code.com | multi_site_strict |
| -1004352437280 | SOI KÈO CÙNG XX88 | xx88code.com | multi_site_strict |
| -1003731231345 | G88 DỊCH VỤ GIAI NHÂN | gg88live.tv | multi_site_strict |
| -1004411105242 | KÈO BÓNG GG88 | gg88live.tv | multi_site_strict |
| -1002421765170 | QQ88 - KHO GIF | tangquaqq88.com | qq88 |
| -1002278162941 | QQ88 - TIN HOT 24/7 | tangquaqq88.com | qq88 |
| -1002324210129 | QQ88 - GIẢI TRÍ | tangquaqq88.com | qq88 |
| -1002377579866 | QQ88 - TIN TỨC MỖI NGÀY | tangquaqq88.com | qq88 |
| -1002325212717 | QQ88 - REVIEW PHIM HAY | tangquaqq88.com | qq88 |
| -1003134541072 | MM88VIP Dịch Vụ Giai Nhân | livemm88.net | mm88 |
| -1003936595246 | GÁI 18+ | livemm88.net | mm88 |
| -1003939163957 | MM88 GIRL DANCE | livemm88.net | mm88 |
| -1003912975699 | SOI KÈO MM88 | livemm88.net | mm88 |
| -1002386905514 | RR88 DỊCH VỤ GIAI NHÂN | liverr88.net | multi_site_strict |
| -1004406362195 | RR88 SOI KÈO | liverr88.net | multi_site_strict |
| -1004435825431 | Hi88 PHÁT CODE MIỄN PHÍ NỖ HŨ-BẮN CÁ | hi88-freecode.pages.dev | hi88 |
| -1003933844700 | Hi88 - CƯỢC GIẢI TRÍ, KIẾM TIỀN TỶ | hi88-freecode.pages.dev | hi88 |
| -1002695720902 | Hi88 - KÊNH GIẢI TRÍ HOT | hi88-freecode.pages.dev | hi88 |
| -1002657420328 | Hi88 - TIN HOT MỖI NGÀY | hi88-freecode.pages.dev | hi88 |
| -1002018121888 | Hi88 - KHO GIF | hi88-freecode.pages.dev | hi88 |
| -1002662584621 | Hi88 - REVIEW PHIM HAY MỖI NGÀY | hi88-freecode.pages.dev | hi88 |
| -1002625548636 | Hi88 TUYỂN ĐẠI LÝ HOA HỒNG 60% | hi88-freecode.pages.dev | hi88 |
| -1004361482833 | V79 PHÁT CODE NỔ HŨ - BẮN CÁ | v79code.com | v79 |

Tài khoản game theo từng site (hợp của mọi kênh cùng site, từng kênh có
thứ tự ưu tiên riêng trong `CHANNEL_CONFIG`): LLwin: dad1; XX8: conve99sau,
kaoboy012; XX88: dad123, dad131, hugolan; QQ88: dad131, kaoboy012, kuuteo012,
okletgo123; HI88: hugolan012, kuuteo012, minichan0123, teoem0123; MM88:
dad123, dad131, kaoboy012, ola12; RR88: hugolan0123, kaoboy012, miniichan;
GG88: conve99sau, hugolan012, kaoboy012; V79: conve99sau, kaoboy012,
minichan011. Nguồn đúng duy nhất là `config.py` — đừng sửa danh sách này
trong tài liệu này.

---

## 9. Bẫy và lỗi đã biết trong snapshot này (đọc trước khi sửa)

Mỗi mục ghi rõ: triệu chứng → nguyên nhân trong code → sửa ở đâu / đừng
làm gì. Đây là phần giúp AI khác không phải mò lại từ đầu.

1. **Foreground bị throttle / SKIP — tưởng là bug đưa tab lên trước.**
   `_force_chrome_window_foreground(domain)` trong `browser_engine.py`
   có throttle 2 s mỗi endpoint (v10): trong 2 s chỉ trả lại
   `last_foreground_ok` cũ, không ép thật. `_wake_tab_for_submit(page,
   domain)`: nếu `BROWSER_FOREGROUND_ON_SUBMIT=True` thì kích hoạt cửa sổ
   tab qua `_activate_exact_tab_window()` (serialize qua `_OS_MOUSE_LOCK`);
   nếu False thì chỉ `page.bring_to_front()` khi domain **không** nằm trong
   `_SKIP_FRONT_DOMAINS` (mặc định code chỉ QQ88, `.env` mở rộng thêm).
   → Muốn tab luôn lên trước mỗi submit thì sửa đúng 2 chỗ này, đừng sửa
   `chrome_restore()` (hàm đó chỉ restore khi minimize, không
   `SetForegroundWindow`).
2. **Windows từ chối `SetForegroundWindow` khi người dùng đang gõ ở app
   khác (foreground lock).** `_force_chrome_window_foreground` đã có
   fallback: `BringWindowToTop` → `SetForegroundWindow` → tạm topmost rồi
   gỡ topmost → `FlashWindow`. Log sẽ ghi `foreground=False` nhưng tab vẫn
   được chọn trong Edge. Đây không phải lỗi code — đừng "sửa" bằng cách
   inject phím hay giữ topmost vĩnh viễn.
3. **Slider LLwin hiện muộn / kéo không qua.** Trong zip này solver đã có
   OS mouse + Playwright fallback, nhưng hook sau click chỉ poll 2 s (bản
   logs-2 v1) và watcher chỉ thử theo cờ `llwin_slider_already_attempted`.
   Nếu slider hiện sau 2 s thì chỉ watcher mới cứu được. Ngưỡng kéo:
   `score >= 0.20` và `dx > 0`, tối đa 2 attempt. Đừng hạ ngưỡng xuống 0
   một cách mù — kéo sai vị trí còn tệ hơn không kéo (site báo
   `CAPTCHA_EXPIRED`).
4. **Slider_ok không bao giờ suy ra từ API.** `_solve_llwin_slider_or_api`
   trả `(slider_ok, api_text)`; `slider_ok` chỉ True khi solver tự trả True.
   Nếu API trả kết quả quyết định trong lúc solver đang chạy thì solver
   vẫn được chờ nhả chuột xong, lỗi solver chỉ bị nuốt khi đã có kết quả
   API. Đừng đổi logic này thành "API thành công thì coi như slider qua".
5. **OS mouse giữ lock và dùng chuột thật.** `_OS_MOUSE_LOCK` trong
   `llwin_slider.py` serialize mọi lần kéo OS mouse và mọi lần focus cửa sổ
   Edge (`_activate_exact_tab_window` cũng qua lock này). Đừng gọi
   `solve_llwin_slider` song song cho 2 tab, đừng focus cửa sổ khác trong
   lúc kéo, và luôn truyền `debug_dir` riêng cho từng lượt.
6. **Tab prefill sai tài khoản.** Tab-only chỉ đúng khi tab đã prefill đúng
   tài khoản. `_llwin_form_matches(page, user, code)` phải True trước khi
   điền tiếp; nếu False thì `_log_tab_without_account` ghi diagnostic rồi
   báo `TAB_UNAVAILABLE`. Đừng ghi username đè lên tab prefill khác.
7. **XX88 clearance cookie.** Chỉ `xx88code.com` mới được dùng
   `_has_clearance_cookie`. `_refresh_used_challenges` bỏ qua
   `turnstile.reset()` chỉ khi đủ 3 điều kiện: token stale + cờ
   `SKIP_TURNSTILE_RESET_WITH_CLEARANCE_COOKIE` (mặc định True) + cookie
   của đúng domain còn hạn. Guard `and page_domain` bắt buộc (mục 7.6).
   Đừng áp logic này cho site khác, đừng quét toàn bộ cookie của context.
8. **QQ88 sync barrier.** Khi `sync_expected > 1`, các lượt QQ88 phải chờ
   nhau ở `_wait_qq88_sync_barrier` rồi mới click; click xong phải
   `_qq88_sync_leave`. Solo fallback chỉ khi `_claim_qq88_solo_fallback`
   thành công. Phá barrier = click lệch nhau = site từ chối hàng loạt.
9. **Kết quả mập mờ không được retry.** `AMBIGUOUS` / `NO_RESULT` /
   `REVIEW_REQUIRED` là thiết kế cố ý, không phải bug thiếu retry.
   `_mark_code_used_if_final` chỉ đánh dấu khi kết quả là final. Submit lại
   mã mập mờ có thể gây nhập trùng hoặc đốt lượt. Sửa ở
   `submission_outcomes.classify_result` và `_submit_code_with_account_retries`
   nếu muốn đổi chính sách — và phải nói rõ với người dùng trước.
10. **TTL XX88 trong zip này là 120 s, không phải 45 s.** Bản v5 cũ đặt 45 s,
    bản hiện tại đã đổi lại 120 s vì Turnstile retry bất đồng bộ. AI đọc
    ghi chú cũ mà áp 45 s sẽ làm mã trong hàng đợi bị bỏ oan. Kiểm tra
    `config.py : SITE_CODE_MAX_AGE_SECONDS` trong zip hiện tại, đừng tin
    ghi chú cũ.
11. **`.env` thắng code.** Mọi mặc định trong `config.py` đều có thể bị
    `.env` ghi đè (tên biến xem mục 6.3). Vá code đổi mặc định mà live
    không đổi → kiểm tra `.env` trước, đừng vá lại lần 2.
12. **Lock submit theo `(domain, user)` và lock tạo lock.** Mẫu đúng:
    `if key not in bot_state.context_locks: bot_state.context_locks[key] =
    asyncio.Lock()`. Đừng dùng `setdefault(..., Lock())` (bug v8 #2:
    `setdefault` luôn evaluate `Lock()` dù key đã có).
13. **Spoiler parser không được rơi về trích chung.** Nếu
    `extract_spoiler_codes` trả kết quả (kể cả không safe) thì dừng ở đó.
    Rơi về trích chung sẽ lấy nhầm mã thiếu ký tự hoặc lấy `KT4` làm mã.
14. **KJC định tuyến theo nhãn, không theo URL kênh.** Kênh KJC về
    `xx88code.com` nhưng tin có thể gắn nhãn site khác — dùng
    `kjc.detect_kjc_labeled_domains` + `build_kjc_broadcast_items`, đừng
    hard-code site đích cho KJC.
15. **Stateless entry không khóa tài khoản theo ngày.** Khi
    `_stateless_entry_enabled()` True thì `_pick_account_stateless` thay
    cho `_get_next_available_account`, và `_mark_account_done_today` không
    còn ý nghĩa như cũ. Đừng trộn 2 luồng.
16. **Direct HTTP chỉ XX8, không replay, có echo check.** `HttpSubmitter`
    claim trước khi POST, kiểm tra account/code trả về có khớp không, lệch
    thì `AMBIGUOUS`. Đừng thêm site vào `DIRECT_HTTP_DOMAINS` khi chưa
    kiểm chứng API đó không cần xác minh trình duyệt.
17. **OCR streaming: `final=False` không bao giờ submit.** Từ đã gộp phải
    từng xuất hiện nguyên vẹn trong một khung. Đừng lấy event chẩn đoán
    làm mã.
18. **Dọn RAM không được `clear()` tập dedupe.** `_emergency_ram_cleanup`
    chỉ gọi `_prune_site_code_seen` (cắt mục quá TTL). `clear()` toàn bộ
    sẽ mất chống trùng đúng lúc máy quá tải.
19. **Disk guard không xoá DB/credential/profile.** `disk_guard._protected`
    và `_walk(..., skip_profiles)` là guard — đừng bỏ guard để "dọn cho
    sạch".
20. **Profile sai thì bot không lên.** `validate_profiles()` chạy lúc
    import `browser_site_profiles.py` và ném `ValueError`. Đây là cố ý,
    không phải bug import — sửa profile, đừng bỏ validate.

---

## 10. Chẩn đoán bằng log — trace một mã từ tin tới kết quả

### 10.1. Thứ tự grep khi một mã "không vào" hoặc "vào mà không rõ kết quả"

1. Tin có tới không? Grep `chat=-100<chat_id>` trong `logs/bot_activity.log`
   quanh thời điểm tin đăng. Không thấy → kiểm tra đã join kênh chưa,
   push/poll có sống không (`[Rx]`, `[Rx-Stat]`), inbox có checkpoint không.
2. Mã có trích được không? Grep mã (hoặc một phần mã) + `[SPOILER-FLOW]` /
   `📥 Đã phân luồng`. Không thấy → xem `_filter_channel_codes` và
   `validate_code` có loại mã không (dáng mã, filter group, blacklist).
3. Mã có vào hàng đợi domain không? Grep `queued=` / `[Queue]` /
   `domain_code_worker`. Không thấy → xem dedupe (`is_site_code_duplicate`),
   tuổi mã (`[CODE-AGE]`), tài khoản done-today/exhausted.
4. Submit có bắt đầu không? Grep `🚀 [BROWSER] SUBMIT | <user> | <mã> |
   <domain>` hoặc `SUBMIT <mã>` (HTTP). Không thấy → xem pacer
   (`[FLOW]` có `pacer_wait`), tab verification (`BROWSER_VERIFICATION_WAIT`),
   semaphore domain.
5. Kết quả là gì? Grep mã + `SUCCESS_POINTS` / `FAILED` /
   `REVIEW_REQUIRED` / `PENDING_VERIFICATION` / `[METRIC]`.
   Đọc `[METRIC]` theo chặng: `cf_wait_ms` cao = Turnstile kẹt;
   `ttfb_ms`/`api_ms` cao = server site chậm; `result_wait_ms` hết
   timeout mà không có API = kết quả mập mờ; `monitor_front_ms` không có
   trong zip này (đó là bản monitor-front giao riêng).
6. Mã LLwin + slider? Grep `slider` / `LLWIN_SLIDER_FAILED` /
   `llwin_slider_` (thư mục debug). Slider mở mà không kéo → xem mục 9.3.

### 10.2. Bảng log signature → nguyên nhân → hàm liên quan

| Log | Nghĩa | Hàm liên quan |
|---|---|---|
| `[SPOILER-FLOW] chat=… message=… age_s=… queue_ms=… process_ms=…` | Mã spoiler đã phân luồng xong | `main_script` (dispatch spoiler) |
| `📥 Đã phân luồng \| N code \| M lượt \| queued=… deferred=…` | Mã đã vào hàng đợi | `main_script._fanout_code_item` |
| `⌨️ Đang nhập \| <mã> → <user>` | Bắt đầu điền/submit cho tài khoản đó | `main_script.domain_code_worker` |
| `🚀 [BROWSER] SUBMIT \| <user> \| <mã> \| <domain>` | Bắt đầu submit trình duyệt | `browser_engine.submit_code_browser` |
| `[METRIC] submit domain=… latency={tab_wait_ms, navigation_ms, form_dom_ms, input_fill_ms, cf_wait_ms, snapshot_ms, site_pacer_ms, submit_click_ms, challenge_wait_ms, result_wait_ms, api_ms, api_status, pre_api_ms, ttfb_ms, body_ms, cleanup_ms, total_submit_ms}` | Thời gian từng chặng của một lượt | `browser_engine._submit_code_browser_locked_inner` + `_ApiTimer.metrics()` |
| `[FLOW] site=… rate_wait/domain_wait/global_wait/pacer_wait/transport/submit` | Thời gian chờ pacer + tổng submit | `main_script` + `submit_pacer` |
| `[CODE-AGE] domain=… account=… code=… age_at_dispatch=… submit=… outcome=… max_age=…` | Tuổi mã lúc bắt đầu nhập và kết quả | `main_script._code_age_for_log` |
| `❌ [user\|domain] FAILED code=… — <lý do>` | Thất bại rõ ràng, không retry | `submission_outcomes.classify_result` |
| `❓ [user\|domain] Kết quả MƠ HỒ code=… — KHÔNG huỷ code, để retry` | Mập mờ, không tự submit lại (xem 9.9) | `submission_outcomes.record_outcome` |
| `⏭️ [domain] <mã> — <lý do> — không retry` | Kết quả rõ ràng nên không thử lại | `main_script._submit_code_with_account_retries` |
| `⏸️ [XX88] tab chưa xác minh — đã điền sẵn mã, giữ trong hàng chờ, chưa submit` | Tab XX88 chưa qua Turnstile | `browser_engine._xx88_submit_readiness` |
| `👁️ <tag> \| foreground=… — hãy hoàn tất Cloudflare/captcha nếu được yêu cầu` | Tab xác minh thủ công đã lên trước | `browser_engine._show_manual_verification_page` |
| `[Rx] poll lỗi (N lần liên tiếp): Telegram is having internal issues` | Lỗi phía Telegram, thoáng qua, không phải lỗi code | `tg_ingest.TelegramReceiver` |
| `[Tab-Slots] XX88=… MM88=… (domain workers)` | Số slot tab lúc start | `main_script.main` + `TabPool` |
| `[Queue] … FreshestFirstQueue` | Hàng đợi XX88 đang dùng freshest-first | `xx88_priority_queue.FreshestFirstQueue` |
| `[XX88-Ready] … foreground_at_arm=…` | Tab XX88 đã sẵn sàng xác minh lúc arm | `browser_engine._arm_xx88_readiness` |
| `[Submit-Pacer] …` | Thống kê pacer / nhịp throttle | `submit_pacer.SubmitPacer` |

### 10.3. Công cụ phân tích offline

- `python analyze_code_age.py logs/bot_activity.log [logs/khac.log ...]`
  — chỉ đọc log, thống kê tuổi mã theo bucket và nhịp 429.
  Hàm: `bucket_of(age)`, `main(paths)`.
- `python test_partial_resume.py` — test offline download resume
  (không cần Telegram thật, dùng `FakeClient`).
- `python -m py_compile <file>.py` — kiểm tra cú pháp sau khi vá, trước
  khi chạy bot. Bắt buộc sau mỗi lần sửa, kể cả sửa nhỏ.

---

## 11. Quy trình vá code (để AI khác làm theo, không phá bản đang chạy)

1. **Dừng bot trước.** Kiểm tra không còn tiến trình Python nào khác
   (`tasklist | findstr python`).
2. **Sao lưu file sắp sửa**, đặc biệt `browser_engine.py`,
   `browser_site_profiles.py`, `config.py`.
3. **Sửa đúng hàm** trong bảng mục 4. Không thêm file/hàm mới nếu chưa cần.
   Không đổi hành vi của hàm khác trong cùng lần vá (một lần vá = một việc).
4. **Đặt marker mới, tên khác hẳn bản cũ.** Ví dụ:
   `PATCH_MARKER_YYYY-MM-DD-<ten-viec>` — một dòng comment chứa marker
   trong mỗi file đã sửa, để kiểm tra bằng `findstr`:
   ```bat
   findstr /C:"PATCH_MARKER_YYYY-MM-DD-<ten-viec>" browser_engine.py browser_site_profiles.py llwin_slider.py
   ```
   Marker cũ (đặc biệt `PATCH_MARKER_2026-10-26-v10` đủ 7 dòng trong
   `browser_engine.py`) phải **vẫn còn đủ** sau khi vá — mất marker cũ
   nghĩa là đã chép đè nhầm file cũ hơn.
5. **Giữ nguyên `.env` và `config.py`** nếu bản vá không nói rõ phải đổi
   chúng. Nếu bản vá có kèm `.env` thì không chép đè `.env` đang chạy.
6. **Giữ nguyên CRLF** cho `browser_engine.py` (file này dùng CRLF):
   sửa bằng script đọc bytes → decode → replace → encode lại CRLF, rồi
   kiểm tra không còn ký tự LF lẻ. Sửa bằng editor thường rất dễ làm
   lệch CRLF và gây diff rác.
7. **Kiểm tra offline trước khi chạy bot:**
   ```bat
   python -m py_compile <file-da-sua>.py
   ```
   Nếu sửa slider: chạy detector trên ảnh mẫu (gap/dx/score phải khớp kỳ
   vọng). Nếu sửa profile: bot tự validate lúc import — lỗi profile thì
   sửa profile, đừng bỏ validate.
8. **Giao đúng 1 zip duy nhất, tên khác hẳn bản cũ**, chứa đủ file cần
   chép đè với tên cuối cùng, kèm file CHANGES ghi rõ: sửa gì, cài như
   thế nào, kiểm tra marker ra sao, test live nào. Không giao từng file lẻ,
   không dùng lại tên zip cũ (dễ chạy nhầm bản cũ do file cùng tên bị
   preview thay vì copy).
9. **Test live đúng 1 thứ:** một mã mới, chưa dùng, đúng domain/tài khoản
   liên quan, đọc đúng dòng log kỳ vọng (mục 10) trước khi kết luận vá
   có hiệu quả. Không test bằng mã đã chết (đã dùng/hết hạn) — mã chết
   sẽ `FAILED` dù code đúng.
10. **Sau khi vá, cập nhật tài liệu này:** sửa mục 1 (marker, số dòng),
    mục 4 (nếu đổi hàm xử lý), mục 9 (nếu phát hiện bẫy mới). Tài liệu
    lỗi thời còn tệ hơn không có tài liệu.

---

## 12. Chỉ mục hàm theo nhóm (để tra nhanh, không cần đọc từng file)

### 12.1. Ingest & inbox

`tg_ingest.TelegramReceiver`: `__init__`, `restore_checkpoints`,
`offer`, `_offer_detailed`, `on_push`, `run`, `_hot_loop`,
`_hot_poll_once`, `_poll_loop`, `_poll_batch`, `_poll_once`,
`_resolve_peers`, `_on_flood`, `_maybe_reconnect`, `_initial_checkpoint`,
`_request_backfill`, `_schedule_fetch`, `_fetch_loop`,
`_commit_backfill_batch`, `_drain_to_target`.
`tg_ingest.IngressStage`: `put`, `pending`, `run`, `commit_backfill_batch`,
`_flush`, `_deliver`, `drain`.
`tg_ingest.TelethonAdapter`: `make_request`, `make_peer`, `peer_id`,
`flood_seconds`, `call`, `bind_dialog_message`.
`durable_inbox.DurableInbox`: xem đầy đủ ở mục 5.1 (claim/complete/
retry/defer/mark_failed/mark_ignored/reset_retryable_failed/reclaim_stale).
`telegram_push_health.TelegramPushHealth`: `seconds_since_push`,
`note_push`, `note_poll`, `hold`, `enable`, `maybe_recover`, `run`.

### 12.2. Trích mã, validate, OCR

`code_extraction`: `extract_codes_from_message`, `extract_spoiler_codes`,
`extract_plain_text_codes`, `extract_marker_near_codes`,
`extract_codes_by_regex`, `extract_hi88_near_link_codes`,
`extract_tokens_from_line`, `validate_candidate`, `unique_keep_order`,
`remove_noise_from_text`, `line_has_code_marker`, `line_is_noise`.
`code_validator.CodeValidator`: `validate_code`, `clean_code`,
`calculate_entropy`, `has_code_shape`, `is_likely_fake`,
`contains_blacklisted_fragment`, `is_site_allowed_for_group`,
`detect_site_identity`, `is_sequential_code`, `looks_like_domain_or_link`,
`is_composed_of_common_words`, `is_text_word`,
`_expand_placeholder_code`, `_resolve_viet_number`,
`get_special_chars`, `count_special_chars`.
`kjc`: `is_kjc_special_channel`, `extract_kjc_spoiler_codes`,
`detect_kjc_labeled_domains`, `build_kjc_broadcast_items`,
`extract_kjc_routed_items`.
`ocr_pipeline`: `extract_site_codes`, `find_code_panels`, `_glyph_crop`,
`_collect_video`, `_recognize`, `_recognize_cached`, `_select_readings`,
`_confirm_sparse_appearances`, `_extract_streaming_video`, `_fallback_codes`;
`OCRProfile.for_site`, `OCRProfile.candidate`.
`image_code_extractor.ImageCodeExtractor`: `_run_rapid_ocr`,
`confirm_code_readings`, `read_image_regions`, `recognize_code_regions`,
`confirm_video_readings`, `get_streaming_recognizer`.
`streaming_code_reader.StreamingCodeReader`: `feed`, `_maybe_emit`, `flush`;
`CtcAlnumRecognizer.from_rapidocr`, `read`; `Reading.fuse`.
`media_download_manager.MediaDownloadManager`: `download`,
`_download_once`, `_download_with_size_check`, `_multipart_download`,
`_multipart_download_locked`, `key_for`, `_revive_dead_exported_senders`.
`manual_confirm`: `locate_code_region`, `prepare_preview`, `ask_code`;
`_UiThread.start/submit/_main/_poll/_show`.

### 12.3. Hàng đợi, pacer, submit

`main_script` (điều phối): `main`, `init_systems`,
`init_channels_and_accounts`, `process_telegram_message`,
`_process_telegram_message_impl`, `domain_code_worker`,
`_submit_code_with_account_retries`, `submit_code_safe`,
`submit_code_with_delay`, `build_domain_accounts_map`,
`build_unique_account_targets`, `get_domain_queue`,
`_enqueue_domain_item`, `_next_domain_dispatch_item`,
`_fanout_code_item`, `_build_distinct_code_items`,
`_build_spoiler_dispatch_items`, `_build_stateless_entry_items`,
`_get_next_available_account`, `_pick_account_stateless`,
`_mark_account_done_today`, `_is_account_done_today`,
`_load_account_rotation`, `append_code_history`, `build_daily_summary`,
`start_message_workers`, `start_domain_workers`, `start_ocr_media_workers`,
`acquire_single_instance_lock`.
`browser_engine` (submit): `submit_code_browser`,
`submit_code_browser_tab`, `_submit_code_browser_locked_inner`,
`_fill_profile_form`, `find_input_fields`, `scroll_to_input_fields`,
`open_mm88_code_form`, `click_submit_fast`, `_resolve_result`,
`_completed_api_result`, `detect_result_text`, `_wake_tab_for_submit`,
`_activate_exact_tab_window`, `_force_chrome_window_foreground`,
`_show_manual_verification_page`, `arm_verification_watcher`,
`wait_for_pending_verification`, `consume_pending_verification_result`,
`_xx88_submit_readiness`, `_arm_xx88_readiness`,
`_has_clearance_cookie`, `_xx88_cookie_clearance`,
`_refresh_used_challenges`, `_wait_for_turnstile_ready`,
`_challenge_token_snapshot`, `_solve_llwin_slider_or_api`,
`_quick_clean_page`, `_clean_page_after_submit`,
`_reload_page_and_refill`, `_recover_tab_only_form`,
`_prefill_tab_username`, `_fill_tab_only_form`, `_llwin_form_matches`,
`_log_tab_without_account`, `_wait_qq88_sync_barrier`,
`_qq88_sync_leave`, `_site_form_ready`, `_ensure_submission_ui`,
`_ensure_v79_captcha_image_ready`, `preload_browsers_and_accounts`,
`dynamic_tab_watcher`, `browser_watchdog`, `cleanup_browsers`,
`get_or_launch_browser_context`, `get_context_for_endpoint`,
`_connect_endpoint`, `endpoint_for_domain`, `chrome_restore`.
`browser_engine.TabPool`: `acquire`, `_try_acquire`, `_pin_account`,
`_bind_accounts`, `prefilled_accounts`, `mark_account_exhausted`,
`reset_exhausted`, `open_tab_count`, `available_tab_count`,
`verification_blocked`, `discover_user_tabs`, `collect_garbage`,
`cleanup_idle_memory`, `recover_endpoint`.
`browser_engine._ApiTimer`: `attach`, `detach`, `_on_request`,
`_on_request_failed`, `_on_response`, `_read`, `mark_click`, `metrics`,
`unconfirmed_result`.
`browser_adapter.BrowserEngineAdapter`: `submit_for_target`.
`http_submitter.HttpSubmitter`: `submit_for_target`, `_submit`;
`classify_api_response`, `_retry_after_seconds`.
`submit_pacer.SubmitPacer`: `reserve`, `throttle`, `wait_ready`,
`remaining`, `accepted_response`, `last_throttle_stats`.
`scheduling`: `freshest_first_enabled`, `verification_gate_enabled`,
`hold_until_verification_ready`; `EarlyDispatch.on_code`, `settle`.
`queue_manager.QueueManager`: `register`, `start`, `stop`, `snapshot`,
`_check_all`, `_drop_oldest`.
`xx88_priority_queue`: `FreshestFirstQueue`, `XX88SpoilerPriorityQueue`,
`is_priority_xx88_spoiler`.
`submission_outcomes`: `classify_result`, `record_outcome`,
`is_account_limit_text`; enum `ResultStatus`.
`llwin_slider`: `solve_llwin_slider`, `_solve_llwin_slider_playwright`,
`_run_os_mouse_drag`, `_perform_os_drag`, `is_llwin_slider_visible`,
`_find_gap_from_png`, `_tile_locator`, `_move_eased`,
`_viewport_to_screen`, `_focus_edge_for_os_mouse`,
`_activate_edge_window`, `_raise_window_z_order`.

### 12.4. Hạ tầng, log, giám sát

`config`: `get_int_env`, `get_float_env`, `get_positive_int_env`,
`get_positive_float_env`, `get_bool_env`, `get_int_list_env`,
`floored_interval`, `get_effective_domain_accounts`,
`_build_effective_domain_accounts`, `is_domain_enabled`.
`database.CodeDatabase`: xem bảng ở mục 6.2.
`logger_setup`: `setup_logger`, `warning_once`, `set_log_context`,
`reset_log_context`, `configure_telethon_logging`, `shutdown_logging`,
`disable_console_logging`.
`dashboard`: `start_dashboard`, `stop_dashboard`, `update_dashboard`,
`update_latency`, `report_ocr_result`, `report_download_started`,
`report_download_finished`, `report_timing_record`,
`get_dashboard_snapshot`.
`monitoring`: `init_monitoring`, `stop_monitoring`, `ocr_admission_paused`;
`HealthMonitor.snapshot/start/stop`, `PerformanceMonitor.record_task`.
`disk_guard`: `cleanup_daily`, `cleanup_weekly`, `ensure_disk_space`,
`register_ocr_tmp`, `release_ocr_tmp`, `_cleanup_stale_ocr_tmp`.
`chrome_launcher`: `ensure_chromes_ready`, `launch_chrome`,
`restart_chrome`, `shutdown_chromes`, `is_chrome_alive`,
`wait_for_chrome_ready`, `profile_for_port`, `send_chrome_alert`.
`features`: `setup_admin_commands`, `register_default_commands`,
`_build_status_report`, `print_version_info`, `get_shutdown_handler`.
`freshness`: `age_seconds`, `is_stale`, `first_known_age`.
`timing.RequestTimer`: `from_event`, `stage`, `stage_async`, `emit`, `finish`.
`code_identity`: `normalize_code`, `normalize_code_domain`.
`sqlite_support`: `connect_database`, `ensure_performance_indexes`.
`native_runtime`: `prepare_ocr_runtime`.
`analyze_code_age`: `bucket_of`, `main`.
`test_partial_resume`: `main` (FakeClient).

### 12.5. Tái tạo chỉ mục hàm đầy đủ bằng AST (không cần đọc từng file)

Nếu cần danh sách hàm đầy đủ hơn mục 12 (ví dụ sau khi vá thêm hàm),
chạy script sau trong thư mục bot — nó in mọi class/hàm kèm chữ ký mà
không cần mở từng file:

```python
import ast, pathlib
for f in sorted(pathlib.Path('.').glob('*.py')):
    try:
        tree = ast.parse(f.read_text(errors='ignore'))
    except Exception as e:
        print(f.name, 'PARSE FAIL', e); continue
    def sig(n):
        args = [a.arg for a in n.args.posonlyargs + n.args.args]
        if n.args.vararg: args.append('*' + n.args.vararg.arg)
        args += [a.arg for a in n.args.kwonlyargs]
        if n.args.kwarg: args.append('**' + n.args.kwarg.arg)
        return f"{n.name}({', '.join(args)})"
    print(f"\n### {f.name}")
    for n in tree.body:
        if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)):
            print('TOP:', sig(n))
    for n in ast.walk(tree):
        if isinstance(n, ast.ClassDef):
            ms = [sig(m) for m in n.body
                  if isinstance(m, (ast.FunctionDef, ast.AsyncFunctionDef))]
            print(f'CLASS {n.name}:', '; '.join(ms))
```

So sánh output của script này với mục 12 sau mỗi lần vá: hàm mới xuất
hiện mà mục 12 chưa có thì cập nhật mục 12 và mục 1 (số dòng, marker).

---

## 13. Những gì tài liệu này KHÔNG thay thế

- **Code thật:** khi sửa, vẫn phải mở đúng file/hàm được chỉ định để đọc
  logic chi tiết (điều kiện, timeout, thứ tự) — tài liệu này chỉ nói
  "sửa ở đâu", không copy toàn bộ thân hàm.
- **Log thật:** chẩn đoán luôn bắt đầu từ log của chính lượt đó (mục 10),
  không đoán từ tài liệu.
- **`.env` thật:** tài liệu này chỉ liệt kê tên biến; giá trị hiệu dụng
  chỉ có trong `.env` đang chạy trên máy người dùng.
- **Test live:** một mã mới, chưa dùng, đúng domain/tài khoản — không có
  tài liệu nào thay thế được bước này.
