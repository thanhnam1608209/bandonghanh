import asyncio
import json
import os
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN", "8783875910:AAG8-oIXhhxzn4hE1vx46mayPYiyOJalSYw")
ADMIN_ID = 8956161451
DATA_FILE = "data.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "users": {},
            "courses": {
                "course_1": {"name": "Môn Toán (Demo)", "price": 500000, "desc": "Khóa học Toán tư duy"},
                "course_2": {"name": "Môn Văn (Demo)", "price": 400000, "desc": "Khóa học Văn thực chiến"}
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

@dp.message(CommandStart())
async def command_start_handler(message: types.Message):
    user_id = message.from_user.id
    name = message.from_user.full_name
    data = load_data()
    
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {"name": name, "role": "guest", "courses": []}
    save_data(data)

    if user_id == ADMIN_ID:
        keyboard = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Quản lý Khóa học & Giá", callback_data="admin_courses")],
            [InlineKeyboardButton(text="🖨 Máy in Code", callback_data="admin_codes")],
            [InlineKeyboardButton(text="👥 Theo dõi Học viên", callback_data="admin_users")],
            [InlineKeyboardButton(text="📢 Gửi thông báo (Broadcast)", callback_data="admin_broadcast")]
        ])
        await message.answer(f"👑 Xin chào Boss tối cao **{name}**!\nBảng Điều Khiển Admin đã sẵn sàng:", reply_markup=keyboard, parse_mode="Markdown")
    else:
        role = data["users"][str(user_id)]["role"]
        if role == "guest":
            keyboard = InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="📖 Bảng danh sách khóa học", callback_data="guest_courses")],
                [InlineKeyboardButton(text="🔑 Nhập code", callback_data="guest_enter_code")],
                [InlineKeyboardButton(text="💬 Tư vấn", url="https://t.me/your_username_here")]
            ])
            await message.answer(f"👋 Xin chào {name}!\nChào mừng bạn đến với Hệ thống Học Tập. Vui lòng chọn chức năng bên dưới:", reply_markup=keyboard)
        else:
            await message.answer("🎓 Chào mừng học viên quay trở lại không gian học tập!")

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
    print(f"Web server started on port {port}")

async def main():
    await start_web_server()
    print("Bot đang chạy polling...")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
