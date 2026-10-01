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
ADMIN_USERNAME = "thanhnam1608" # Đã cập nhật đúng username của bạn
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

# --- THIẾT KẾ BÀN PHÍM NỔI CHO KHÁCH/HỌC VIÊN (REPLY KEYBOARD) ---
user_main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="📖 Bảng danh sách"), KeyboardButton(text="🔑 Nhập code")],
        [KeyboardButton(text="💬 Tư vấn - CSKH"), KeyboardButton(text="ℹ️ Giới thiệu")]
    ],
    resize_keyboard=True, # Thu nhỏ cho vừa màn hình điện thoại
    input_field_placeholder="Chọn chức năng học tập..."
)

# --- LỆNH /START ---
@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    data = load_data()
    
    # Lưu người dùng mới
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {"name": name, "role": "guest", "courses": []}
        save_data(data)

    if user_id == ADMIN_ID:
        # Bàn phím Inline cho Admin (Gọn gàng để quản lý)
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Quản lý Khóa học & Giá", callback_data="admin_courses")],
            [InlineKeyboardButton(text="🖨 Máy in Code", callback_data="admin_codes")],
            [InlineKeyboardButton(text="👥 Theo dõi Học viên", callback_data="admin_users")],
            [InlineKeyboardButton(text="📢 Gửi thông báo (Broadcast)", callback_data="admin_broadcast")]
        ])
        await message.answer(f"👑 Chào Boss tối cao **{name}**!\nBảng điều khiển dành riêng cho bạn:", reply_markup=admin_kb, parse_mode="Markdown")
    else:
        # Khách/Học viên sẽ thấy bàn phím nổi dưới đáy
        await message.answer(
            f"👋 Xin chào {name}!\nChào mừng bạn đến với Hệ thống Bot Bán Khóa Học tự động.\n\nHãy chọn chức năng ở menu bên dưới nhé 👇", 
            reply_markup=user_main_menu
        )

# --- XỬ LÝ CÁC CHỨC NĂNG CỦA KHÁCH/HỌC VIÊN ---

@dp.message(F.text == "📖 Bảng danh sách")
async def show_courses(message: types.Message):
    data = load_data()
    courses_kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Render động danh sách môn học từ data.json
    for course_id, course_info in data["courses"].items():
        courses_kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"{course_info['name']} - {course_info['price']:,}đ", callback_data=f"view_{course_id}")
        ])
    
    await message.answer("📚 **Danh sách các môn học hiện có:**\nChọn một môn để xem chi tiết và thanh toán:", reply_markup=courses_kb, parse_mode="Markdown")

@dp.message(F.text == "🔑 Nhập code")
async def enter_code(message: types.Message):
    await message.answer("🔑 Vui lòng nhập mã Code kích hoạt khóa học của bạn (Ví dụ: TOAN-12345):")
    # Ghi chú: Phần check code thực tế sẽ code ở giai đoạn sau

@dp.message(F.text == "💬 Tư vấn - CSKH")
async def support_contact(message: types.Message):
    support_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Nhắn tin cho Admin Thành Nam", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    await message.answer(
        "👨‍💻 **Bộ phận CSKH - Hỗ trợ Trực tuyến**\n\n"
        "Nếu bạn cần tư vấn mua khóa học, chuyển khoản VietQR, hoặc gặp sự cố tài khoản, vui lòng nhấn nút bên dưới để chat trực tiếp với Admin nhé!",
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
        "3️⃣ Nhận Code và kích hoạt bài học ngay lập tức\n\n"
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
