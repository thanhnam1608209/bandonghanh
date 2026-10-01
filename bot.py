import asyncio
import json
import os
import random
import string
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# --- CẤU HÌNH ---
TOKEN = os.getenv("BOT_TOKEN", "8783875910:AAG8-oIXhhxzn4hE1vx46mayPYiyOJalSYw")
ADMIN_ID = 8956161451
ADMIN_USERNAME = "thanhnam1608" 
DATA_FILE = "data.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

# --- KHỞI TẠO TRẠNG THÁI (FSM) CHO ADMIN ---
class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_new_price = State()
    waiting_for_lesson_name = State()
    waiting_for_lesson_link = State()

# --- XỬ LÝ DỮ LIỆU ---
def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "users": {},
            "courses": {
                "Toan": {"name": "Môn Toán", "price": 60000, "lessons": []},
                "Van": {"name": "Môn Văn", "price": 50000, "lessons": []}
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

def generate_random_code(prefix="VIP"):
    chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{chars}"

# --- HÀM TẠO MENU ĐỘNG DỰA THEO QUYỀN HỌC VIÊN ---
def get_user_menu(user_id):
    data = load_data()
    kb_layout = [
        [KeyboardButton(text="📖 Bảng danh sách"), KeyboardButton(text="🔑 Nhập code")],
        [KeyboardButton(text="💬 Tư vấn - CSKH"), KeyboardButton(text="ℹ️ Giới thiệu")]
    ]
    
    user_courses = data["users"].get(str(user_id), {}).get("courses", [])
    if user_courses:
        study_buttons = []
        for cid in user_courses:
            if cid in data["courses"]:
                cname = data["courses"][cid]["name"]
                study_buttons.append(KeyboardButton(text=f"🎓 Vào học {cname}"))
        
        for i in range(0, len(study_buttons), 2):
            kb_layout.insert(0, study_buttons[i:i+2])
            
    return ReplyKeyboardMarkup(keyboard=kb_layout, resize_keyboard=True)

# --- LỆNH /START ---
@dp.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext):
    await state.clear() 
    user_id = message.from_user.id
    name = message.from_user.full_name
    data = load_data()
    
    if str(user_id) not in data["users"]:
        data["users"][str(user_id)] = {"name": name, "role": "guest", "courses": [], "qr_msg_id": None}
        save_data(data)

    if user_id == ADMIN_ID:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Quản lý Khóa học & Giá", callback_data="admin_courses")],
            [InlineKeyboardButton(text="📂 Thêm Bài giảng", callback_data="admin_lessons")],
            [InlineKeyboardButton(text="🖨 Máy in Code (Môn Toán)", callback_data="gen_Toan")],
            [InlineKeyboardButton(text="🖨 Máy in Code (Môn Văn)", callback_data="gen_Van")],
            [InlineKeyboardButton(text="👥 Thống kê Học viên", callback_data="admin_stats")],
            [InlineKeyboardButton(text="📢 Gửi thông báo", callback_data="admin_broadcast")]
        ])
        await message.answer(f"👑 Chào Boss tối cao **{name}**!\nBảng điều khiển dành riêng cho bạn:", reply_markup=admin_kb, parse_mode="Markdown")
    else:
        await message.answer(
            f"👋 Xin chào {name}!\nChào mừng bạn đến với Hệ thống Bot Học tập.\n\nHãy chọn chức năng ở menu bên dưới nhé 👇", 
            reply_markup=get_user_menu(user_id)
        )

# ==========================================
# 1. CÁC TÍNH NĂNG CỦA ADMIN 
# ==========================================
@dp.callback_query(F.data == "admin_courses")
async def admin_manage_courses(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for course_id, course_info in data["courses"].items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"✏️ Sửa giá {course_info['name']} ({course_info['price']:,}đ)", callback_data=f"editprice_{course_id}")])
    await callback.message.answer("🛠 **QUẢN LÝ GIÁ BÁN:**\nChọn khóa học bạn muốn thay đổi giá:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("editprice_"))
async def ask_new_price(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    course_id = callback.data.split("_")[1]
    data = load_data()
    await state.update_data(edit_course_id=course_id)
    await state.set_state(AdminStates.waiting_for_new_price)
    await callback.message.answer(f"💰 Bạn đang sửa giá cho **{data['courses'][course_id]['name']}**.\n👉 Vui lòng nhắn con số giá mới (Ví dụ: 75000):", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_new_price))
async def set_new_price(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Lỗi! Bạn chỉ được phép nhập số. Vui lòng nhập lại:")
        return
    new_price = int(message.text.strip())
    user_data = await state.get_data()
    course_id = user_data["edit_course_id"]
    db = load_data()
    db["courses"][course_id]["price"] = new_price
    save_data(db)
    await message.answer(f"✅ Đã cập nhật thành công!\nGiá mới của **{db['courses'][course_id]['name']}** hiện tại là: **{new_price:,}đ**", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "admin_lessons")
async def admin_manage_lessons(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for course_id, course_info in data["courses"].items():
        lesson_count = len(course_info.get("lessons", []))
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"➕ Thêm bài vào {course_info['name']} (Đang có {lesson_count} bài)", callback_data=f"addlesson_{course_id}")])
    await callback.message.answer("📂 **QUẢN LÝ BÀI GIẢNG:**\nChọn khóa học bạn muốn thêm bài mới vào:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("addlesson_"))
async def ask_lesson_name(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    course_id = callback.data.split("_")[1]
    await state.update_data(lesson_course_id=course_id)
    await state.set_state(AdminStates.waiting_for_lesson_name)
    await callback.message.answer("📝 **Bước 1:** Vui lòng nhắn TÊN BÀI GIẢNG bạn muốn thêm.\n_(Ví dụ: Bài 1: Phương trình bậc 2)_", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_lesson_name))
async def ask_lesson_link(message: types.Message, state: FSMContext):
    lesson_name = message.text.strip()
    await state.update_data(lesson_name=lesson_name)
    await state.set_state(AdminStates.waiting_for_lesson_link)
    await message.answer("🔗 **Bước 2:** Vui lòng nhắn LINK BÀI GIẢNG (Link YouTube, Google Drive, File PDF... đều được).", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_lesson_link))
async def save_new_lesson(message: types.Message, state: FSMContext):
    lesson_link = message.text.strip()
    user_data = await state.get_data()
    course_id = user_data["lesson_course_id"]
    lesson_name = user_data["lesson_name"]
    
    db = load_data()
    if "lessons" not in db["courses"][course_id]:
        db["courses"][course_id]["lessons"] = []
    db["courses"][course_id]["lessons"].append({"name": lesson_name, "link": lesson_link})
    save_data(db)
    
    await message.answer(f"✅ Đã thêm bài giảng thành công vào **{db['courses'][course_id]['name']}**!\n\n**{lesson_name}**\n{lesson_link}", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data.startswith("gen_"))
async def admin_generate_code(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    course_id = callback.data.split("_")[1]
    data = load_data()
    new_code = generate_random_code(course_id.upper())
    data["codes"][new_code] = {"course": course_id, "used": False}
    save_data(data)
    await callback.message.answer(f"✅ Đã tạo 1 mã kích hoạt cho **{data['courses'][course_id]['name']}**:\n\n`{new_code}`\n\n_(Mã chỉ dùng được 1 lần)_", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def admin_show_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    total_users = len(data["users"])
    used_codes = sum(1 for c in data["codes"].values() if c["used"])
    await callback.message.answer(f"📊 **THỐNG KÊ HỆ THỐNG**\n\n👥 **Khách đã chat:** {total_users}\n✅ **Khóa học đã bán:** {used_codes}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def admin_ask_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await callback.message.answer("📢 **Chế độ Phát thanh:**\nHãy nhắn nội dung tin nhắn bạn muốn gửi cho toàn bộ khách hàng (Có thể gửi kèm ảnh).")
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_broadcast))
async def admin_send_broadcast(message: types.Message, state: FSMContext):
    data = load_data()
    success = 0
    await message.answer("⏳ Đang gửi tin nhắn...")
    for user_id in data["users"].keys():
        try:
            await message.send_copy(chat_id=user_id)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(f"✅ Đã gửi xong cho **{success}** khách hàng!")
    await state.clear()

# ==========================================
# 2. KHU VỰC HỌC TẬP CỦA HỌC VIÊN
# ==========================================
@dp.message(F.text.startswith("🎓 Vào học"))
async def student_learning_area(message: types.Message):
    user_id = str(message.from_user.id)
    course_name_clicked = message.text.replace("🎓 Vào học ", "").strip()
    data = load_data()
    
    target_course_id = None
    for cid, cinfo in data["courses"].items():
        if cinfo["name"] == course_name_clicked:
            target_course_id = cid
            break
            
    if not target_course_id or target_course_id not in data["users"].get(user_id, {}).get("courses", []):
        await message.answer("❌ Bạn chưa có quyền truy cập khóa học này!")
        return
        
    lessons = data["courses"][target_course_id].get("lessons", [])
    if not lessons:
        await message.answer(f"🚧 Khóa học **{course_name_clicked}** hiện chưa có bài giảng nào được tải lên.", parse_mode="Markdown")
        return
        
    lessons_kb = InlineKeyboardMarkup(inline_keyboard=[])
    for lesson in lessons:
        lessons_kb.inline_keyboard.append([InlineKeyboardButton(text=f"▶️️ {lesson['name']}", url=lesson['link'])])
        
    await message.answer(f"🎓 **KHU VỰC HỌC TẬP: {course_name_clicked}**\n\nChúc bạn học tập hiệu quả. Bấm vào bài học bên dưới để mở:", reply_markup=lessons_kb, parse_mode="Markdown")

# ==========================================
# 3. LUỒNG KHÁCH MUA HÀNG VÀ GỬI MÃ QR
# ==========================================
@dp.message(F.text == "📖 Bảng danh sách")
async def show_courses(message: types.Message):
    data = load_data()
    courses_kb = InlineKeyboardMarkup(inline_keyboard=[])
    for course_id, course_info in data["courses"].items():
        courses_kb.inline_keyboard.append([InlineKeyboardButton(text=f"{course_info['name']} - {course_info['price']:,}đ", callback_data=f"view_{course_id}")])
    await message.answer("📚 **Danh sách các môn học hiện có:**\nChọn một môn để thanh toán:", reply_markup=courses_kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("view_"))
async def process_course_view(callback: types.CallbackQuery):
    course_id = callback.data.split("_")[1]
    data = load_data()
    course = data["courses"].get(course_id)
    if not course: return
    price = course['price']
    user_id = callback.from_user.id
    transfer_content = f"MUAKHOA {user_id}"
    
    # QR MB Bank
    qr_url = f"https://img.vietqr.io/image/mbbank-0812847035-compact2.png?amount={price}&addInfo={transfer_content}&accountName=PHUNG THANH NAM"

    msg = (
        f"📘 **{course['name']}**\n💰 **Giá tiền:** `{price:,} VNĐ`\n\n"
        f"🏦 **HƯỚNG DẪN THANH TOÁN TỰ ĐỘNG:**\n"
        f"Hệ thống duyệt tự động 24/7. Bạn hãy quét mã QR hoặc chuyển đúng **Nội dung chuyển khoản** bên dưới:\n\n"
        f"▪️ Ngân hàng: **MB Bank**\n"
        f"▪️ STK: **0812847035**\n"
        f"▪️ Chủ TK: **PHUNG THANH NAM**\n"
        f"▪️ Nội dung: `{transfer_content}` _(Chạm vào để copy)_\n\n"
        f"⏳ _Sau khi nhận tiền, mã QR này sẽ TỰ ĐỘNG BIẾN MẤT và hệ thống sẽ cấp mã học cho bạn!_"
    )
    
    sent_msg = await callback.message.answer_photo(photo=qr_url, caption=msg, parse_mode="Markdown")
    data["users"][str(user_id)]["qr_msg_id"] = sent_msg.message_id
    save_data(data)
    
    await callback.answer()

@dp.message(F.text == "🔑 Nhập code")
async def enter_code_prompt(message: types.Message):
    await message.answer("🔑 Vui lòng nhập mã Code của bạn (Ví dụ: TOAN-VIP123):")

@dp.message(F.text.regexp(r'^[A-Z0-9-]+$'))
async def check_code(message: types.Message):
    code = message.text.strip()
    data = load_data()
    if code in data["codes"]:
        if data["codes"][code]["used"]:
            await message.answer("❌ Mã Code này đã được sử dụng trước đó!")
        else:
            course_id = data["codes"][code]["course"]
            data["codes"][code]["used"] = True
            user_id = str(message.from_user.id)
            if course_id not in data["users"][user_id]["courses"]:
                data["users"][user_id]["courses"].append(course_id)
                data["users"][user_id]["role"] = "member"
            save_data(data)
            
            await message.answer(
                f"🎉 **KÍCH HOẠT THÀNH CÔNG!**\nBạn đã sở hữu khóa học **{data['courses'][course_id]['name']}**.\nMenu đã được cập nhật nút **🎓 Vào Học** ở bên dưới 👇", 
                reply_markup=get_user_menu(user_id), parse_mode="Markdown"
            )
    else:
        if len(code) > 4: 
            await message.answer("❌ Mã Code không tồn tại hoặc sai định dạng.")

@dp.message(F.text == "💬 Tư vấn - CSKH")
async def support_contact(message: types.Message):
    support_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Nhắn tin Admin", url=f"https://t.me/{ADMIN_USERNAME}")]])
    await message.answer("👨‍💻 Nếu bạn cần hỗ trợ, hãy nhắn Admin nhé!", reply_markup=support_kb)

@dp.message(F.text == "ℹ️️ Giới thiệu")
async def intro_system(message: types.Message):
    await message.answer("🎓 **Về Hệ thống Mini-LMS của chúng tôi**\n\n1️⃣ Dạo xem khóa học\n2️⃣ Thanh toán tự động VietQR\n3️⃣ Nhận bài học tự động!", parse_mode="Markdown")

# ==========================================
# 4. ĐƯỜNG ỐNG WEBHOOK TỰ ĐỘNG XÓA QR & HIỆN CODE
# ==========================================
async def auto_payment_webhook(request):
    try:
        data = await request.json()
        transfer_content = data.get("content", "").upper()
        amount = int(data.get("transferAmount", 0))
        
        if "MUAKHOA" in transfer_content:
            parts = transfer_content.split("MUAKHOA")
            user_id = parts[1].strip().split()[0]
            db = load_data()
            
            course_id = None
            for cid, cinfo in db["courses"].items():
                if amount == cinfo["price"]:
                    course_id = cid
                    break
            if not course_id:
                return web.json_response({"status": "Khong khop gia"})
                
            course_name = db["courses"][course_id]["name"]
            
            if user_id in db["users"]:
                # 1. TÌM VÀ XÓA MÃ QR CŨ MÀ KHÁCH ĐÃ QUÉT
                qr_msg_id = db["users"][user_id].get("qr_msg_id")
                if qr_msg_id:
                    try:
                        await bot.delete_message(chat_id=int(user_id), message_id=qr_msg_id)
                        db["users"][user_id]["qr_msg_id"] = None
                    except Exception:
                        pass 
                
                # 2. TẠO RA MỘT MÃ CODE MỚI TINH VÀ ĐÁNH DẤU LÀ "ĐÃ SỬ DỤNG"
                new_code = generate_random_code(course_id.upper())
                db["codes"][new_code] = {"course": course_id, "used": True}
                
                # 3. CẤP QUYỀN KHÓA HỌC CHO KHÁCH
                if course_id not in db["users"][user_id]["courses"]:
                    db["users"][user_id]["courses"].append(course_id)
                    db["users"][user_id]["role"] = "member"
                    
                save_data(db)
                
                # 4. NHẮN TIN HIỂN THỊ CODE CHO KHÁCH
                msg_to_user = (
                    f"🎉 **THANH TOÁN THÀNH CÔNG!**\n\n"
                    f"💳 Hệ thống đã nhận được `{amount:,}đ`.\n"
                    f"🎫 Mã Code của bạn là: `{new_code}`\n\n"
                    f"✅ _Hệ thống đã tự động thu hồi mã QR và kích hoạt khóa học **{course_name}** cho bạn._\n\n"
                    f"👉 **Hãy gõ lệnh /start để Menu hiện ra nút 🎓 Vào Học nhé!**"
                )
                await bot.send_message(chat_id=int(user_id), text=msg_to_user, parse_mode="Markdown")
            
            # 5. BÁO CÁO CHO ADMIN
            msg_to_admin = (f"🤑 **TIỀN VÀO TÀI KHOẢN!**\nKhách `{user_id}` chuyển `{amount:,}đ`.\n✅ Bot đã tự động xóa QR và phát mã code `{new_code}` môn **{course_name}**.")
            await bot.send_message(chat_id=ADMIN_ID, text=msg_to_admin, parse_mode="Markdown")
            
        return web.json_response({"status": "success"})
    except Exception as e:
        return web.json_response({"status": "error", "message": str(e)})

async def handle_ping(request):
    return web.Response(text="Bot Mini-LMS is running 24/7!")

async def start_web_server():
    app = web.Application()
    app.router.add_get("/", handle_ping)
    app.router.add_post("/sepay-webhook", auto_payment_webhook)
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
