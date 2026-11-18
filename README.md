# Cảnh 3D — Hai kiếm sĩ đánh nhau (~20 giây)

Bộ file để render cảnh 3D "2 kiếm sĩ đánh nhau bằng kiếm" trên **GitHub Actions**
(máy của GitHub, CPU 4 nhân) thay vì render ở máy local quá chậm.

## Các file

| File | Vai trò |
|---|---|
| `scene.py` | Script Blender tự chứa: dựng sàn đấu + 2 kiếm sĩ (xanh/đỏ) từ khối nguyên thủy, hoạt cảnh 480 frame @ 24 fps (thủ thế → 3 lần chạm kiếm có tia lửa → đòn quyết định, bên thua ngã), camera quay vòng + đẩy gần. Render Cycles CPU, 640×360, xuất PNG sequence. |
| `.github/workflows/render.yml` | Workflow chạy bằng tay: cài Blender 4.2.9 + ffmpeg → render frames → ghép MP4 → upload artifact. |
| `README.md` | File này. |

Diễn biến trong video (20 giây):

- **0–4s:** hai bên thủ thế, đi vòng thăm dò.
- **4–15s:** ba đợt trao đổi đòn — chém/đỡ ở tầm trung, tầm cao và tầm thấp; mỗi lần kiếm chạm kiếm đều tóe tia lửa + chớp sáng (frame 120, 207, 300).
- **15–20s:** đòn quyết định (frame 417), bên đỏ bị đánh bật kiếm, loạng choạng rồi ngã; bên xanh hạ kiếm, cúi đầu.

## Cách chạy trên web GitHub

1. Đưa cả thư mục này lên một repo GitHub (thư mục này là gốc repo,
   tức `scene.py` nằm ở tầng cao nhất của repo).
2. Mở repo trên web → tab **Actions**.
3. Chọn workflow **"Render canh kiem 3D"** ở cột trái → nút **Run workflow** → **Run workflow**.
4. Đợi job chạy xong (mục lục sẽ hiện từng bước; bước render có in thời gian).
5. Mở job đã xong → kéo xuống mục **Artifacts** → tải **video-kiem-3d** (file `video-kiem-3d.mp4`).

## Lưu ý

- GitHub giới hạn **1 job tối đa 6 giờ**; workflow để trần 350 phút. Toàn bộ
  quá trình chạy trong đúng 1 job từ đầu tới cuối.
- Thời gian render thực tế trên máy GitHub chưa đo được trước — xem dòng
  "Thoi gian render" trong log của bước Render. Nếu quá chậm, giảm
  `cyc.samples` trong `scene.py` (đang để 32) xuống 16 rồi chạy lại.
- Muốn tự kiểm tra hình học chạm kiếm mà không render: chạy
  `SCENE_CHECK=1 blender -b --python scene.py` — script chỉ dựng cảnh và in
  khoảng cách hai lưỡi kiếm tại 4 frame chạm (đều < 0,2 đơn vị là đạt).
