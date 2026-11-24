# Backup offsite GC2 production

Cutover ngày 26/11 chỉ WARN khi chưa có offsite. Trước khi chạy `resume-three` tối 27/11, hoàn tất upload đã xác minh và một lần diễn tập restore trên Mac. `resume-three` kiểm trực tiếp lại metadata trên Drive và chặn nếu snapshot đã đủ 26 giờ, không còn trong thư mục đúng, checksum sai hoặc Drive không truy cập được. Backup cùng ổ đĩa bảo vệ khỏi lỗi thao tác trên DB nhưng có thể mất cùng DB khi ổ đĩa hỏng, mất máy hoặc bị xóa.

## OAuth và folder Drive

Legacy v3.2 dùng OAuth `authorized_user` qua `GOOGLE_DRIVE_TOKEN_JSON`, với `GOOGLE_OAUTH_CLIENT_ID` và `GOOGLE_OAUTH_CLIENT_SECRET` nếu thông tin OAuth nằm riêng. Contract ở `shared/storage/google_drive.py`; GitHub Actions nạp ba tên này trong `.github/workflows/growth-daily-cycle.yml`. Credential có hiệu lực trên ASUS và email tài khoản Google chưa được xác minh từ repo. Script kiểm production env mà không in giá trị. Nếu thiếu, chuyển credential đã cấp quyền và refresh được vào `~/venho/secrets/growth-engine.env` (600) qua trình sửa bí mật trên server. JSON phải phù hợp với cú pháp systemd EnvironmentFile và wrapper Bash, chẳng hạn một dòng bọc nháy đơn. Giữ các base secrets hiện có. Dùng lại OAuth, không dùng uploader ảnh legacy vì uploader đó cấp quyền xem công khai.

1. Đăng nhập Drive bằng tài khoản Google cấp OAuth. Khi script hỏi folder, gõ `CREATE` để chính OAuth app tạo hoặc tìm lại folder riêng **VENHO GC2 Backups** trong My Drive. Giữ **General access → Restricted**. Cùng tài khoản OAuth sở hữu thư mục thì không phải chia sẻ cho service account.
2. Nếu Harry đã tạo folder private bằng UI, cấp quyền Editor cho chính **tài khoản người dùng OAuth** nếu khác chủ folder, rồi nhập ID folder. Với scope `drive.file`, app còn cần Picker cấp quyền truy cập thư mục đó, nên ưu tiên `CREATE` để thư mục thuộc phạm vi app ngay. Xác nhận user OAuth hoặc tài khoản Harry được cấp Viewer cho lần tải phục hồi.
3. Tách quyền xem backup và quyền giữ age identity. Key giải mã chỉ có trong Apple Passwords, mục **VENHO GC2 backup (age)**. Repo và ASUS giữ recipient công khai và fingerprint SHA-256. Script setup chỉ backup env mode 600 và sửa `GE_BACKUP_DRIVE_FOLDER_ID`.

## ASUS

Từ checkout riêng tại SHA bàn giao trên `gc2/build-v1-2`, chạy `bash ops/asus-server/growth-engine/setup-offsite-backup.sh` sau 09:30 ICT. Chạy bằng tài khoản quản lý GC2. Chỉ bước cài `age` nếu thiếu dùng `sudo apt-get`. Xác nhận `OFFSITE` qua TTY. Script kiểm folder hiện tại qua Drive trước khi hỏi. Nếu hợp lệ, script in `FOLDER_ENV=ALREADY_SET` và giữ nguyên env. Nếu cần nhập ID hoặc tạo folder, script xác minh folder qua Drive trước khi ghi env. Kỳ vọng `RELEASE_SHA`, checksum PASS và `OFFSITE_SETUP=PASS`, user timer `growth-engine-backup-offsite.timer` active. Không có migration mới. Script deploy vẫn kiểm schema trước khi switch.

Timer user chạy lúc **02:30 ICT** hằng ngày. Nó mã hóa snapshot staging dưới 1 giờ với `age`, upload resumable lên Drive rồi đối chiếu MD5 và SHA-256 nếu Drive cung cấp thêm SHA-256. Chỉ công nhận khi MD5, kích thước, thư mục và nhận diện file khớp. SHA-256 nguồn được lưu trong manifest bàn giao để kiểm file tải xuống. Receipt mode 600 ở `backup-offsite/latest.json` cạnh DB. Doctor kiểm local receipt theo giờ tạo snapshot, không gọi Drive. Gate `resume-three` và `offsite-status` kiểm lại Drive.

Để chạy lại và lấy filename + SHA-256 đã xác minh, từng lệnh thực thi độc lập:

```bash
bash "$HOME/venho/growth-engine/current/ops/asus-server/growth-engine/run-with-legacy-provider-env.sh" backup offsite-now
bash "$HOME/venho/growth-engine/current/ops/asus-server/growth-engine/run-with-legacy-provider-env.sh" backup offsite-status
```

Giữ bản mới nhất của 14 bucket ngày và 8 bucket tuần theo ICT. Một bản có thể đáp ứng cả hai bucket. Retention chỉ chuyển vào Trash các file được chính tool xác minh trong thư mục cấu hình, dựa trên marker cài đặt và marker trùng ID Drive thực tế. Giữ nguyên file ngoài folder, file gửi tay, bản sao và file chưa xác minh. Giữ marker local `backup-offsite/owner.json` khi chuyển server để tiếp tục retention. Các bản vào Trash vẫn chiếm quota theo chính sách Drive.

Nếu upload lỗi, kiểm mã lỗi của unit `growth-engine-backup-offsite.service`; mỗi đợt lỗi liên tiếp gửi tối đa một cảnh báo Telegram production và lần chạy PASS sẽ mở lại dedupe. Lỗi Drive không đổi mode, pause, channel hoặc job đăng bài. Nếu thiếu quyền hoặc OAuth hỏng, khôi phục credential rồi chạy lại; nếu checksum lệch, coi bản đó là lỗi và chỉ tải bản đã được `offsite-status` xác nhận. Khi cần quay lại cấu hình folder trước, tắt timer offsite, khôi phục riêng dòng folder từ env backup, sau đó chạy kiểm tra lại trước khi bật timer.

## Mac

Trước `resume-three` và sau đó **ngày 01 hằng tháng lúc 10:00 ICT**, chạy `backup offsite-status` trên ASUS, tải đúng file `.age` vừa báo từ folder private bằng trình duyệt và ghi nhận SHA-256. Trên Mac cài `brew install age` nếu thiếu, rồi chạy:

```bash
bash ops/asus-server/growth-engine/offsite-restore-mac.sh /path/to/downloaded.tar.gz.age VERIFIED_SHA256
```

Chờ dòng yêu cầu rồi mới copy identity từ Passwords và nhấn Enter. Script đọc clipboard sau Enter, xóa clipboard, kiểm `age-keygen -y` khớp recipient trước khi giải mã. Identity đi qua pipe nội bộ, không ghi file. Script kiểm SHA-256 tải xuống, `integrity_check`, `foreign_key_check` và từng artifact từ manifest, rồi dọn các file giải mã và DB tạm. Ghi ngày và `OFFSITE_RESTORE=PASS` vào checklist mở ba kênh hoặc log diễn tập tháng. Khi fail, giữ backup mã hóa để đối soát và chạy lại với file đã xác minh.
