#!/bin/bash
# Mac / Linux: bấm đúp file này (hoặc chạy ./chay-mac.command) là render xong và tự mở video.
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
if ! command -v uv >/dev/null 2>&1; then
  echo ">> Chưa có uv, đang cài (chỉ một lần)..."
  curl -LsSf https://astral.sh/uv/install.sh | sh || { echo "Cài uv thất bại. Kiểm tra mạng rồi thử lại."; read -r -p "Nhấn Enter để thoát"; exit 1; }
  export PATH="$HOME/.local/bin:$HOME/.cargo/bin:$PATH"
fi
echo ">> Đang render video (khoảng 1-3 phút)..."
uv run render_v11.py --output noel-ascii.mp4 || { echo "Render thất bại."; read -r -p "Nhấn Enter để thoát"; exit 1; }
echo ">> Xong: $(pwd)/noel-ascii.mp4"
if command -v open >/dev/null 2>&1; then open noel-ascii.mp4
elif command -v xdg-open >/dev/null 2>&1; then xdg-open noel-ascii.mp4; fi
