# Backup và restore Growth Engine

## Tạo backup

1. Cài `age` trên máy chạy backup và đặt `GE_AGE_RECIPIENT` thành public recipient; private identity chỉ do Harry giữ.
2. Kiểm tra `GE_DB_PATH`, `GE_MEDIA_ROOT` và quyền ghi vào thư mục backup riêng.
3. Chạy `venho-engine backup now --destination <new-file.age>`.

Lệnh dùng SQLite Online Backup API, kiểm tra integrity/foreign keys, tính lại SHA-256 cho mọi original/variant đang được tham chiếu, và dừng nếu thiếu artifact. Snapshot, manifest và media được đóng thành archive rồi mã hoá bằng `age`; file đích được tạo với mode `0600`. Lệnh không xoá hay ghi đè backup cũ.

## Restore rehearsal

Restore chỉ được ghi vào một thư mục đích chưa tồn tại. Không restore đè DB đang chạy.

```bash
ops/asus-server/growth-engine/restore-rehearsal.sh \
  /path/to/backup.age /protected/path/to/age-identity /tmp/growth-engine-restore
```

Rehearsal giải mã bằng private identity do operator cấp, kiểm tra archive/manifest, integrity SQLite, foreign keys và SHA của từng media artifact. Sau đó nó đặt mọi runtime control hiện hữu về `DISABLED`, bật global pause và thay `dispatch_epoch`; do đó capability epoch cũ không còn khớp. Worker không được khởi động từ rehearsal.

## Sau sự cố thật

1. Giữ scheduler/worker dừng và khôi phục vào state directory mới ở `DISABLED`.
2. Xoay capability keys và Make bearer theo quy trình sự cố; dừng/drain execution cũ.
3. Đối soát mọi command PENDING/EXECUTING trong khoảng sau snapshot. Bài không rõ kết quả giữ `UNKNOWN`; không tự retry.
4. Chỉ mở từng Page sau khi kiểm tra evidence, `DRY_RUN` và quyết định của operator.

Lệnh restore chưa được chạy trên server production trong task này. Upload Drive, lịch giữ 48 bản theo giờ/14 theo ngày/8 theo tuần và kiểm soát quyền identity vẫn là bước vận hành riêng.
