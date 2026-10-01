import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiohttp import web

# --- CẤU HÌNH ---
TOKEN = os.getenv("BOT_TOKEN", "8783875910:AAG8-oIXhhxzn4hE1vx46mayPYiyOJalSYw")
ADMIN_ID = 8956161451
ADMIN_USERNAME = "thanhnam1608" 
DATA_FILE = "data.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- XỬ LÝ DỮ LIỆU ---
def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "users": {},
            "courses": {
                "Toan": {"name": "Môn Toán", "price": 500000},
                "Van": {"name": "Môn Văn", "price": 400000}
            },
            "codes": {}
        }
        save_data(default_data)
        return default_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- THIẾT KẾ BÀN PHÍM NỔI CHO KHÁCH/HỌC VIÊN ---
user_main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📖 Bảng danh sách"), KeyboardButton(text="🔑 Nhập code")],
        [KeyboardButton(text="💬 Tư vấn - CSKH"), KeyboardButton(text="ℹ️ Giới thiệu")]
    ],
    resize_keyboard=True,
    input_field_placeholder="Chọn chức năng học tập..."
)

# --- LỆNH /START ---
@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    data = load_data()
    
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {"name": name, "role": "guest", "courses": []}
        save_data(data)

    if user_id == ADMIN_ID:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Quản lý Khóa học & Giá", callback_data="admin_courses")],
            [InlineKeyboardButton(text="🖨 Máy in Code", callback_data="admin_codes")],
            [InlineKeyboardButton(text="👥 Theo dõi Học viên", callback_data="admin_users")],
            [InlineKeyboardButton(text="📢 Gửi thông báo", callback_data="admin_broadcast")]
        ])
        await message.answer(f"👑 Chào Boss tối cao **{name}**!\nBảng điều khiển dành riêng cho bạn:", reply_markup=admin_kb, parse_mode="Markdown")
    else:
        await message.answer(
            f"👋 Xin chào {name}!\nChào mừng bạn đến với Hệ thống Bot Bán Khóa Học tự động.\n\nHãy chọn chức năng ở menu bên dưới nhé 👇", 
            reply_markup=user_main_menu
        )

# ==========================================
# 1. XỬ LÝ NÚT BẤM CỦA ADMIN
# ==========================================
@dp.callback_query(F.data.startswith("admin_"))
async def process_admin_callbacks(callback: types.CallbackQuery):
    action = callback.data
    
    if action == "admin_courses":
        await callback.message.answer("🛠 **Tính năng:** Bạn sẽ có thể Thêm/Sửa/Xóa tên và giá khóa học tại đây. (Đang phát triển)", parse_mode="Markdown")
    elif action == "admin_codes":
        await callback.message.answer("🖨 **Máy in Code:** Chức năng tự động sinh mã ngẫu nhiên cho khóa học. (Đang phát triển)", parse_mode="Markdown")
    elif action == "admin_users":
        await callback.message.answer("👥 **Thống kê:** Xem danh sách học viên và lần truy cập cuối. (Đang phát triển)", parse_mode="Markdown")
    elif action == "admin_broadcast":
        await callback.message.answer("📢 **Phát thanh:** Gửi tin nhắn hàng loạt cho tất cả người dùng. (Đang phát triển)", parse_mode="Markdown")
    
    # Tắt biểu tượng "đang tải" trên nút bấm
    await callback.answer()

# ==========================================
# 2. XỬ LÝ LUỒNG KHÁCH MUA HÀNG & VIETQR
# ==========================================
@dp.message(F.text == "📖 Bảng danh sách")
async def show_courses(message: types.Message):
    data = load_data()
    courses_kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    for course_id, course_info in data["courses"].items():
        courses_kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"{course_info['name']} - {course_info['price']:,}đ", callback_data=f"view_{course_id}")
        ])
    
    await message.answer("📚 **Danh sách các môn học hiện có:**\nChọn một môn để xem chi tiết và thanh toán:", reply_markup=courses_kb, parse_mode="Markdown")

# Khi khách bấm vào 1 môn học cụ thể để thanh toán
@dp.callback_query(F.data.startswith("view_"))
async def process_course_view(callback: types.CallbackQuery):
    course_id = callback.data.split("_")[1]
    data = load_data()
    course = data["courses"].get(course_id)
    
    if not course:
        await callback.answer("Khóa học không tồn tại!", show_alert=True)
        return

    price = course['price']
    user_id = callback.from_user.id
    
    # Cú pháp chuyển khoản chứa ID của khách để Admin dễ check
    transfer_content = f"MUAKHOA {user_id}"
    
    # TẠO MÃ QR ĐỘNG (Tự động điền Techcombank, Số tiền, STK, Tên, Nội dung)
    qr_url = f"https://img.vietqr.io/image/techcombank-160820098386-compact2.png?amount={price}&addInfo={transfer_content}&accountName=PHUNG THANH NAM"

    msg = (
        f"📘 **{course['name']}**\n\n"
        f"💰 **Giá tiền:** `{price:,} VNĐ`\n\n"
        f"🏦 **HƯỚNG DẪN THANH TOÁN:**\n"
        f"Bạn hãy quét mã QR bên dưới bằng app ngân hàng (Mã QR đã tự động nhập sẵn số tiền và nội dung).\n\n"
        f"Hoặc chuyển khoản thủ công:\n"
        f"▪️ Ngân hàng: **Techcombank**\n"
        f"▪️ STK: **160820098386**\n"
        f"▪️ Chủ TK: **PHUNG THANH NAM**\n"
        f"▪️ Nội dung: `{transfer_content}` _(Chạm vào để copy)_\n\n"
        f"⏳ _Sau khi chuyển khoản thành công, vui lòng chụp bill gửi cho Admin ở mục Hỗ trợ để nhận Code nhé!_"
    )
    
    # Gửi ảnh QR kèm caption hướng dẫn
    await callback.message.answer_photo(photo=qr_url, caption=msg, parse_mode="Markdown")
    await callback.answer()

# ==========================================
# CÁC CHỨC NĂNG CÒN LẠI CỦA KHÁCH
# ==========================================
@dp.message(F.text == "🔑 Nhập code")
async def enter_code(message: types.Message):
    await message.answer("🔑 Vui lòng nhập mã Code kích hoạt khóa học của bạn (Ví dụ: TOAN-12345):")

@dp.message(F.text == "💬 Tư vấn - CSKH")
async def support_contact(message: types.Message):
    support_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Gửi Bill / Nhắn Admin", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    await message.answer(
        "👨‍💻 **Bộ phận CSKH - Hỗ trợ Trực tuyến**\n\n"
        "Nếu bạn đã chuyển khoản xong, vui lòng nhấn nút bên dưới để gửi Bill (Biên lai) cho Admin xác nhận và cấp Code nhé!",
        reply_markup=support_kb,
        parse_mode="Markdown"
    )

@dp.message(F.text == "ℹ️ Giới thiệu")
async def intro_system(message: types.Message):
    await message.answer(
        "🎓 **Về Hệ thống Mini-LMS của chúng tôi**\n\n"
        "Đây là nền tảng học tập tự động 24/7. Bạn có thể:\n"
        "1️⃣ Dạo xem danh sách khóa học\n"
        "2️⃣ Thanh toán tự động qua VietQR\n"
        "3️⃣ Nhập Code để mở khóa bài học ngay lập tức\n\n"
        "Chúc bạn có một trải nghiệm học tập tuyệt vời!",
        parse_mode="Markdown"
    )

# --- GIỮ BOT CHẠY TRÊN RENDER ---
async def handle(request):
    return web.Response(text="Bot Mini-LMS is running 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle)
    runner = web.AppRunner(app)
    await runner.setup()
    port = int(os.environ.get("PORT", 10000))
    site = web.TCPSite(runner, "0.0.0.0", port)
    await site.start()

async def main():
    await start_web_server()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
