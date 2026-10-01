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
# ĐIỀN USERNAME TELEGRAM CỦA BẠN VÀO ĐÂY (bỏ dấu @ ở đầu)
ADMIN_USERNAME = "thanhnam_admin" 
DATA_FILE = "data.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- XỬ LÝ DỮ LIỆU ---
def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {"users": {}, "courses": {}, "codes": {}}
        save_data(default_data)
        return default_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

# --- THIẾT KẾ BÀN PHÍM CHÍNH (GIỐNG ẢNH YÊU CẦU) ---
user_main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [KeyboardButton(text="💎 Mời bạn nhận quà"), KeyboardButton(text="👑 BXH hôm nay")],
        [KeyboardButton(text="🎁 Code Tân Thủ"), KeyboardButton(text="📈 Check Chia sẻ")],
        [KeyboardButton(text="📊 Thống Kê TK"), KeyboardButton(text="💁‍♂️️ Hỗ Trợ – CSKH")]
    ],
    resize_keyboard=True, # Tự động thu nhỏ vừa màn hình điện thoại
    input_field_placeholder="Chọn tính năng bên dưới..."
)

# --- LỆNH /START ---
@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    data = load_data()
    
    # Lưu người dùng mới
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {"name": name, "role": "guest", "balance": 0, "ref_count": 0}
        save_data(data)

    if user_id == ADMIN_ID:
        # Bàn phím Inline cho Admin (giữ nguyên để quản lý)
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Quản lý Khóa học", callback_data="admin_courses")],
            [InlineKeyboardButton(text="🖨 Máy in Code", callback_data="admin_codes")]
        ])
        await message.answer(f"👑 Chào Boss **{name}**!", reply_markup=admin_kb)
    else:
        # Hiển thị bàn phím nổi cho Khách/Học viên
        await message.answer(
            f"👋 Xin chào {name}!\nChào mừng bạn đến với hệ thống. Hãy chọn chức năng ở menu bên dưới nhé 👇", 
            reply_markup=user_main_menu
        )

# --- XỬ LÝ CÁC NÚT BẤM DƯỚI ĐÁY MÀN HÌNH ---

@dp.message(F.text == "💁‍♂️ Hỗ Trợ – CSKH")
async def handle_support(message: types.Message):
    # Gắn link trực tiếp tới Admin Thành Nam
    support_kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💬 Nhắn tin cho Admin Thành Nam", url=f"https://t.me/{ADMIN_USERNAME}")]
    ])
    await message.answer(
        "👨‍💻 **Bộ phận CSKH - Hỗ trợ Trực tuyến**\n\n"
        "Nếu bạn cần tư vấn mua khóa học, nạp tiền, hoặc gặp sự cố tài khoản, vui lòng nhấn nút bên dưới để chat trực tiếp với Admin nhé!",
        reply_markup=support_kb,
        parse_mode="Markdown"
    )

@dp.message(F.text == "🎁 Code Tân Thủ")
async def handle_newbie_code(message: types.Message):
    await message.answer("Vui lòng nhập mã Code Tân Thủ của bạn (Ví dụ: TANTHU2024):")
    # Ghi chú: Phần check code thực tế sẽ code sau

@dp.message(F.text == "💎 Mời bạn nhận quà")
async def handle_referral(message: types.Message):
    user_id = message.from_user.id
    ref_link = f"https://t.me/{(await bot.me()).username}?start={user_id}"
    await message.answer(
        f"🔗 **Link giới thiệu của bạn:**\n`{ref_link}`\n\n"
        "Hãy gửi link này cho bạn bè, khi họ nhấn vào và sử dụng bot, bạn sẽ nhận được hoa hồng/quà tặng!",
        parse_mode="Markdown"
    )

@dp.message(F.text == "📊 Thống Kê TK")
async def handle_stats(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    await message.answer(
        f"👤 **Tài khoản:** {name}\n"
        f"🆔 **ID:** `{user_id}`\n"
        f"💰 **Khóa học đã mua:** 0\n"
        f"👥 **Đã giới thiệu:** 0 người",
        parse_mode="Markdown"
    )

@dp.message(F.text.in_({"👑 BXH hôm nay", "📈 Check Chia sẻ"}))
async def handle_coming_soon(message: types.Message):
    await message.answer("🚧 Tính năng đang được cập nhật. Vui lòng quay lại sau!")


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
