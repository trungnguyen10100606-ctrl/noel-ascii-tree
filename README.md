# Noel ASCII Tree 🎄

Video Giáng sinh dọc 1080×1920 (26 giây): cây thông xoay dựng hoàn toàn bằng ký tự code,
có bóng tròn nhiều màu, dải đèn, xe tuyết, hộp quà và dòng chữ **MERRY CHRISTMAS** viết bằng ký tự.
Toàn bộ khung hình được tính bằng Python (numpy + Pillow), không cần phần mềm dựng phim.

> A 26-second vertical Christmas video where a rotating tree is drawn entirely out of ASCII code characters.
> Pure Python (numpy + Pillow), one command to render.

## ▶ Xem ngay, không cần cài gì

Tải video đã render sẵn ở mục **[Releases](../../releases/latest)** (`noel-ascii.mp4`).

## ▶ Tự render trên máy của bạn (Mac & Windows, bấm đúp là chạy)

1. Bấm **Code → Download ZIP** trên trang repo, giải nén.
2. Chạy file tương ứng với máy của bạn:

| Máy | Làm gì |
|---|---|
| **Windows** | bấm đúp `chay-windows.bat` |
| **macOS** | bấm đúp `chay-mac.command` (lần đầu: chuột phải → Open → Open, vì macOS hỏi về file tải từ mạng) |
| **Linux** | `./chay-mac.command` |

Script tự cài [`uv`](https://docs.astral.sh/uv/) nếu máy chưa có (chỉ một lần). `uv` lo luôn Python, thư viện và `ffmpeg`, nên bạn **không phải cài gì thêm** và không đụng tới môi trường sẵn có.
Chờ khoảng 1–3 phút, video là `noel-ascii.mp4` trong thư mục và sẽ tự mở khi xong.

### Hoặc gõ lệnh

Đã có `uv` thì chỉ cần một lệnh trong thư mục repo (giống nhau trên Mac, Windows, Linux):

```bash
uv run render_v11.py
```

Chưa có `uv`: Mac/Linux `curl -LsSf https://astral.sh/uv/install.sh | sh`; Windows PowerShell `irm https://astral.sh/uv/install.ps1 | iex`.

### Chỉnh bố cục & độ rực

Đầu file `render_v11.py` có các núm chỉnh: `GLYPH_W`/`GLYPH_H` (kích thước ký tự, mặc định 12×20 px, gần giống video code-art trên Instagram),
`SCENE_SCALE` (độ lớn cây, ký tự không bị nhỏ theo), `STAR_Y` (vị trí ngôi sao), `TITLE_Y` (vị trí chữ chào),
`GAIN`, `SATURATION`, `GLOW` (độ sáng, độ rực, độ phát sáng). Mặc định giữ mọi thứ trong vùng an toàn của Reels
(cách mép trên khoảng 250px, mép dưới khoảng 340px). Video xuất chuẩn màu BT.709 để Instagram không làm lệch màu.

### Tùy chọn

```bash
uv run render_v11.py --output video-cua-toi.mp4      # đặt tên file
uv run render_v11.py --snapshot 24.89 --output khung.png   # xuất 1 khung hình tại giây 24.89
uv run render_v11.py --duration 10                   # chỉ render 10 giây đầu
```

### Không dùng `uv`?

Python 3.9+:
```bash
pip install -r requirements.txt
python render_v11.py
```

## Cấu trúc

| File | Vai trò |
|---|---|
| `render_v11.py` | **Điểm vào.** Màu rực rỡ, phát sáng, bố cục an toàn cho Instagram Reels (tránh thanh trên, caption và nút bên phải) |
| `render_v10.py` | Bản nền: cảnh v8 + sắc pixel-glitch nhẹ cho cây và bóng |
| `render_v8.py`, `greeting_v8.py` | Chữ MERRY CHRISTMAS dạng ký tự có hiệu ứng |
| `render_v7.py` | Bóng tròn nhiều màu, xoay không chập chờn |
| `render_v6.py`, `star_v6.py` | Dựng tán cây theo giai đoạn, dải đèn, ngôi sao |
| `render_v2.py` – `render_v4.py`, `render.py` | Lõi: chiếu 3D lên lưới ký tự, ghép khung hình |
| `sleigh.py`, `ground_gifts.py`, `point_canopy.py` | Xe tuyết, hộp quà, đám điểm tạo tán cây |
| `chay-mac.command`, `chay-windows.bat` | Chạy một chạm trên Mac / Windows |
| `tools/make_source.py` | Vẽ ảnh nguồn `assets/tree-source.png` bằng code |
| `assets/` | Ảnh nguồn và font monospace đi kèm (để chạy giống nhau trên mọi hệ điều hành) |

## Giấy phép & ghi chú

- Mã nguồn: MIT (xem `LICENSE`).
- Font `DejaVu Sans Mono`: giấy phép tự do của DejaVu/Bitstream Vera, được phép phân phối lại.
- `assets/tree-source.png` là ảnh nguồn do chính mã này tự vẽ (`tools/make_source.py`), không dùng ảnh của bên thứ ba.
  Muốn tạo lại: `uv run tools/make_source.py`. Muốn đổi dáng/màu cây, sửa script đó rồi render lại.
