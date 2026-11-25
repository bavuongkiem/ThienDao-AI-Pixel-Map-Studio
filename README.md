# Thiên Đạo AI Pixel Map Studio — MVP 1.0

Bản mã nguồn thử nghiệm Windows, giao diện tiếng Việt (Tkinter). Không bao gồm model, EXE hoặc dịch vụ AI. Không dùng hình vẽ giả làm kết quả AI.

## Cài đặt
1. Cài Python 3.11 64-bit (python.org), Ollama (ollama.com), ComfyUI (comfy.org) và Godot 4 (godotengine.org).
2. Chạy `ollama pull qwen2.5:3b`, đảm bảo Ollama đang chạy tại 127.0.0.1:11434.
3. Cài checkpoint SD 1.5 tương thích trong ComfyUI/models/checkpoints; chọn model có giấy phép phù hợp. Khởi động ComfyUI ở 127.0.0.1:8188. Có thể dùng workflow API JSON xuất từ ComfyUI, có node CLIPTextEncode với text đúng bằng __PROMPT__ và node xuất ảnh. Tự cấu hình LoRA/ControlNet trong workflow này. Workflow mặc định không có LoRA.
4. Chạy install.bat, rồi start.bat. Chọn thư mục trống cho từng map, nhập tên checkpoint chính xác hoặc chọn workflow API, nhập yêu cầu tiếng Việt, nhấn tạo. RemBG tải model tách nền lần đầu; cần internet để tải các phụ thuộc/model.
5. Mở thư mục godot bằng Godot 4. Scene map.tscn dùng Sprite2D, chưa phải TileMapLayer; NPC/quái là marker, chưa có gameplay. Mỗi dự án có plan.json, assets và jobs.sqlite. Dùng lại thư mục sẽ dùng lại kế hoạch/asset cũ, muốn tạo lại nên chọn thư mục mới. Nút dừng chỉ ngừng điều phối khi tới điểm kiểm tra, không hủy job đã gửi đến ComfyUI.
6. build_exe.bat thử đóng gói bằng PyInstaller dạng thư mục dist/ThienDaoMapStudio. Cần giữ nguyên thư mục dist khi phân phối. Chưa kiểm thử build Windows.

## Giới hạn
Bố cục hiện tại là thuật toán lưới cố định, nền lặp lại; Ollama lập danh sách asset và prompt chứ chưa lập tọa độ chi tiết. Collision top-down là hình chữ nhật gần đúng; Ninja chỉ có sàn. Chưa có navigation, TileSet thực, editor kéo thả, preview, AI kiểm định hình ảnh, tự sửa lỗi, cài đặt AI tự động, hoặc nhân vật chơi được. Chưa có chế độ tạo lại từng asset qua UI. Chất lượng pixel phụ thuộc checkpoint/workflow; tách nền có thể làm mất chi tiết. Chạy tuần tự để giảm VRAM. Không cam kết chất lượng hình ảnh.

## Nhiệm vụ Codex tiếp theo
Đọc README và mã nguồn, giữ kết nối API thật. Bổ sung kiểm tra dịch vụ, quản lý cấu hình, workflow Pixel LoRA có giấy phép phù hợp, schema bố cục có tọa độ/layer/footprint, TileMapLayer + TileSetAtlasSource, navigation và kiểm tra kết nối đường đi, editor/preview, kiểm định ảnh và retry giới hạn, bảo vệ dữ liệu cũ. Kiểm thử với Ollama/ComfyUI thật, Godot headless, đóng gói Windows onedir và kiểm thử trên máy sạch. Không tuyên bố chức năng chưa chạy là hoàn tất. Không nhúng API key hoặc model chưa có quyền phân phối.
