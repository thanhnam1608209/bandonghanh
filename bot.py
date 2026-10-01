import asyncio
import json
import os
import random
import string
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

TOKEN = os.getenv("BOT_TOKEN", "8783875910:AAG8-oIXhhxzn4hE1vx46mayPYiyOJalSYw")
ADMIN_ID = 8956161451
ADMIN_USERNAME = "thanhnam1608" 
DATA_FILE = "data.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_new_price = State()
    waiting_for_lesson_name = State()
    waiting_for_lesson_link = State()
    waiting_for_edit_course_name = State()
    waiting_for_new_course_id = State()
    waiting_for_new_course_name = State()
    waiting_for_new_course_price = State()
    waiting_for_intro = State()
    waiting_for_combo_id = State()
    waiting_for_combo_name = State()
    waiting_for_combo_courses = State()
    waiting_for_combo_price = State()
    waiting_for_private_msg = State()

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "users": {},
            "courses": {
                "Toan": {"name": "Môn Toán", "price": 3000, "lessons": []},
                "Van": {"name": "Môn Văn", "price": 50000, "lessons": []}
            },
            "combos": {},
            "codes": {},
            "intro_text": "🎓 **Về Hệ thống Mini-LMS của chúng tôi**\n\n1️⃣ Dạo xem khóa học & Combo\n2️⃣ Thanh toán tự động VietQR\n3️⃣ Nhận bài học tự động!"
        }
        save_data(default_data)
        return default_data
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
        if "intro_text" not in data:
            data["intro_text"] = "🎓 **Về Hệ thống Mini-LMS của chúng tôi**\n\n1️⃣ Dạo xem khóa học\n2️⃣ Thanh toán tự động VietQR\n3️⃣ Nhận bài học tự động!"
        if "combos" not in data:
            data["combos"] = {}
        if "courses" not in data:
            data["courses"] = {}
        if "users" not in data:
            data["users"] = {}
        if "codes" not in data:
            data["codes"] = {}
        return data

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def generate_random_code(prefix="VIP"):
    chars = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
    return f"{prefix}-{chars}"

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

def format_time_diff(last_active_str):
    if not last_active_str:
        return "Chưa xác định"
    try:
        last_active = datetime.fromisoformat(last_active_str)
        diff = datetime.now() - last_active
        seconds = int(diff.total_seconds())
        if seconds < 60:
            return "Vừa hoạt động"
        minutes = seconds // 60
        if minutes < 60:
            return f"Không dùng {minutes} phút trước"
        hours = minutes // 60
        if hours < 24:
            return f"Không dùng {hours} giờ trước"
        days = hours // 24
        return f"Không dùng {days} ngày trước"
    except Exception:
        return "Không rõ"

@dp.message(CommandStart())
async def command_start_handler(message: types.Message, state: FSMContext):
    await state.clear() 
    user_id = message.from_user.id
    name = message.from_user.full_name
    data = load_data()
    
    str_uid = str(user_id)
    now_iso = datetime.now().isoformat()

    if str_uid not in data["users"]:
        data["users"][str_uid] = {
            "name": name, 
            "role": "guest", 
            "courses": [], 
            "qr_msg_id": None, 
            "last_active": now_iso
        }
    else:
        data["users"][str_uid]["name"] = name
        data["users"][str_uid]["last_active"] = now_iso
    save_data(data)

    if user_id == ADMIN_ID:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Quản lý Môn học (Lẻ)", callback_data="admin_courses"),
             InlineKeyboardButton(text="📦 Quản lý Combo (Gộp)", callback_data="admin_combos")],
            [InlineKeyboardButton(text="📂 Quản lý Bài giảng", callback_data="admin_lessons"),
             InlineKeyboardButton(text="📝 Sửa phần Giới thiệu", callback_data="edit_intro")],
            [InlineKeyboardButton(text="👥 Quản lý Học viên & Thời gian", callback_data="admin_users_list")],
            [InlineKeyboardButton(text="🖨 Máy in Code", callback_data="admin_print_codes")],
            [InlineKeyboardButton(text="📢 Thông báo Tổng", callback_data="admin_broadcast")]
        ])
        await message.answer(f"👑 Chào Boss tối cao **{name}**!\nBảng điều khiển dành riêng cho bạn:", reply_markup=admin_kb, parse_mode="Markdown")
    else:
        await message.answer(
            f"👋 Xin chào {name}!\nChào mừng bạn đến với Hệ thống Bot Học tập.\n\nHãy chọn chức năng ở menu bên dưới nhé 👇", 
            reply_markup=get_user_menu(user_id)
        )

# ADMIN - QUẢN LÝ HỌC VIÊN
@dp.callback_query(F.data == "admin_users_list")
async def admin_users_list(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    users = data.get("users", {})
    
    if not users:
        await callback.message.answer("👥 Hệ thống chưa có học viên nào.")
        await callback.answer()
        return

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text_summary = f"👥 **DANH SÁCH HỌC VIÊN ({len(users)} người):**\n\n"
    
    for uid, info in users.items():
        name = info.get("name", "Không rõ")
        last_active = info.get("last_active", "")
        time_status = format_time_diff(last_active)
        courses_count = len(info.get("courses", []))
        
        text_summary += f"▪️ **{name}**\n   ├ UID: `{uid}`\n   ├ Đã mua: {courses_count} môn\n   └ Trạng thái: _{time_status}_\n\n"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"✉️ Nhắn riêng {name}", callback_data=f"privatemsg_{uid}")])

    if len(text_summary) > 4000:
        text_summary = text_summary[:4000] + "\n...(Danh sách quá dài)..."

    await callback.message.answer(text_summary, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("privatemsg_"))
async def ask_private_message(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    target_uid = callback.data.split("_")[1]
    await state.update_data(private_target_uid=target_uid)
    await state.set_state(AdminStates.waiting_for_private_msg)
    await callback.message.answer(f"✉️ **GỬI TIN NHẮN CÁ NHÂN:**\nĐang gửi tới UID: `{target_uid}`\n👉 Nhập nội dung:", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_private_msg))
async def send_private_message_action(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    target_uid = user_data["private_target_uid"]
    try:
        await bot.send_message(chat_id=int(target_uid), text=f"📩 **Tin nhắn từ Admin:**\n\n{message.text.strip()}", parse_mode="Markdown")
        await message.answer(f"✅ Đã gửi tới UID `{target_uid}`!", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Gửi thất bại: {str(e)}")
    await state.clear()

# ADMIN - MÔN HỌC & COMBO & GIỚI THIỆU & BÀI GIẢNG & IN CODE
@dp.callback_query(F.data == "admin_courses")
async def admin_manage_courses(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for course_id, course_info in data["courses"].items():
        kb.inline_keyboard.append([
            InlineKeyboardButton(text=f"✏️ Tên: {course_info['name']}", callback_data=f"editname_{course_id}"),
            InlineKeyboardButton(text=f"💰 Giá: {course_info['price']:,}đ", callback_data=f"editprice_{course_id}")
        ])
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ THÊM MÔN HỌC MỚI", callback_data="add_course")])
    await callback.message.answer("🛠 **QUẢN LÝ MÔN HỌC LẺ:**", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("editname_"))
async def ask_edit_course_name(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.update_data(edit_course_id=callback.data.split("_")[1])
    await state.set_state(AdminStates.waiting_for_edit_course_name)
    await callback.message.answer("✏ Nhập tên mới:", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_edit_course_name))
async def set_edit_course_name(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    db = load_data()
    db["courses"][user_data["edit_course_id"]]["name"] = message.text.strip()
    save_data(db)
    await message.answer("✅ Đã đổi tên thành công!", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data.startswith("editprice_"))
async def ask_new_price(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.update_data(edit_course_id=callback.data.split("_")[1])
    await state.set_state(AdminStates.waiting_for_new_price)
    await callback.message.answer("💰 Nhập giá mới (chỉ số):", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_new_price))
async def set_new_price(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Chỉ nhập số:")
        return
    user_data = await state.get_data()
    db = load_data()
    db["courses"][user_data["edit_course_id"]]["price"] = int(message.text.strip())
    save_data(db)
    await message.answer("✅ Đã đổi giá thành công!", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "add_course")
async def ask_new_course_id(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_new_course_id)
    await callback.message.answer("➕ Nhập MÃ MÔN HỌC (viết liền không dấu, VD: Anh):", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_new_course_id))
async def ask_new_course_name(message: types.Message, state: FSMContext):
    await state.update_data(new_course_id=message.text.strip())
    await state.set_state(AdminStates.waiting_for_new_course_name)
    await callback.message.answer("📝 Nhập TÊN MÔN HỌC:", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_new_course_name))
async def ask_new_course_price(message: types.Message, state: FSMContext):
    await state.update_data(new_course_name=message.text.strip())
    await state.set_state(AdminStates.waiting_for_new_course_price)
    await callback.message.answer("💰 Nhập GIÁ MÔN HỌC (chỉ số):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_new_course_price))
async def save_new_course(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Giá phải là số:")
        return
    user_data = await state.get_data()
    db = load_data()
    db["courses"][user_data["new_course_id"]] = {"name": user_data["new_course_name"], "price": int(message.text.strip()), "lessons": []}
    save_data(db)
    await message.answer("✅ Đã thêm môn học thành công!", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "admin_combos")
async def admin_manage_combos(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for combo_id, combo_info in data.get("combos", {}).items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📦 {combo_info['name']} - {combo_info['price']:,}đ", callback_data="ignore")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ TẠO COMBO MỚI", callback_data="add_combo")])
    await callback.message.answer("📦 **QUẢN LÝ COMBO:**", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "add_combo")
async def ask_new_combo_id(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_combo_id)
    await callback.message.answer("➕ Nhập MÃ COMBO (VD: C1):", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_combo_id))
async def ask_new_combo_name(message: types.Message, state: FSMContext):
    await state.update_data(combo_id=message.text.strip())
    await state.set_state(AdminStates.waiting_for_combo_name)
    await callback.message.answer("📝 Nhập TÊN COMBO:", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_name))
async def ask_new_combo_courses(message: types.Message, state: FSMContext):
    await state.update_data(combo_name=message.text.strip())
    await state.set_state(AdminStates.waiting_for_combo_courses)
    await callback.message.answer("🔗 Nhập các MÃ MÔN HỌC gộp, cách nhau bởi dấu phẩy (VD: Toan, Van):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_courses))
async def ask_new_combo_price(message: types.Message, state: FSMContext):
    courses = [c.strip() for c in message.text.strip().split(',') if c.strip()]
    await state.update_data(combo_courses=courses)
    await state.set_state(AdminStates.waiting_for_combo_price)
    await message.answer("💰 Nhập GIÁ COMBO (chỉ số):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_price))
async def save_new_combo(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Giá phải là số:")
        return
    user_data = await state.get_data()
    db = load_data()
    db["combos"][user_data["combo_id"]] = {"name": user_data["combo_name"], "price": int(message.text.strip()), "course_ids": user_data["combo_courses"]}
    save_data(db)
    await message.answer("✅ Tạo Combo thành công!", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "edit_intro")
async def ask_edit_intro(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_intro)
    await callback.message.answer("📝 Nhập nội dung GIỚI THIỆU mới:", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_intro))
async def save_new_intro(message: types.Message, state: FSMContext):
    db = load_data()
    db["intro_text"] = message.text.strip()
    save_data(db)
    await message.answer("✅ Đã cập nhật giới thiệu!")
    await state.clear()

@dp.callback_query(F.data == "admin_lessons")
async def admin_manage_lessons(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cid, cinfo in data["courses"].items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"➕ Thêm bài vào {cinfo['name']}", callback_data=f"addlesson_{cid}")])
    await callback.message.answer("📂 Chọn môn học để thêm bài:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("addlesson_"))
async def ask_lesson_name(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.update_data(lesson_course_id=callback.data.split("_")[1])
    await state.set_state(AdminStates.waiting_for_lesson_name)
    await callback.message.answer("📝 Nhập TÊN BÀI GIẢNG:", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_lesson_name))
async def ask_lesson_link(message: types.Message, state: FSMContext):
    await state.update_data(lesson_name=message.text.strip())
    await state.set_state(AdminStates.waiting_for_lesson_link)
    await message.answer("🔗 Nhập LINK BÀI GIẢNG:", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_lesson_link))
async def save_new_lesson(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    db = load_data()
    if "lessons" not in db["courses"][user_data["lesson_course_id"]]:
        db["courses"][user_data["lesson_course_id"]]["lessons"] = []
    db["courses"][user_data["lesson_course_id"]]["lessons"].append({"name": user_data["lesson_name"], "link": message.text.strip()})
    save_data(db)
    await message.answer("✅ Đã thêm bài giảng thành công!", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "admin_print_codes")
async def show_print_code_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cid, cinfo in data["courses"].items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"🖨 Môn: {cinfo['name']}", callback_data=f"gen_course_{cid}")])
    for cid, cinfo in data.get("combos", {}).items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"🖨 Combo: {cinfo['name']}", callback_data=f"gen_combo_{cid}")])
    await callback.message.answer("🖨 Chọn mục cần in mã code:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("gen_course_") | F.data.startswith("gen_combo_"))
async def admin_generate_code(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    item_type = "combo" if "gen_combo_" in callback.data else "course"
    item_id = callback.data.split(f"gen_{item_type}_")[1]
    new_code = generate_random_code(item_id.upper())
    data["codes"][new_code] = {"type": item_type, "id": item_id, "used": False}
    save_data(data)
    await callback.message.answer(f"✅ Mã code mới:\n`{new_code}`", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def admin_ask_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer("📢 Nhập nội dung thông báo TỔNG gửi toàn bộ học viên:")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_broadcast))
async def admin_send_broadcast(message: types.Message, state: FSMContext):
    data = load_data()
    success = 0
    for uid in data["users"].keys():
        try:
            await message.send_copy(chat_id=int(uid))
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(f"✅ Đã gửi thông báo tổng tới {success} học viên!")
    await state.clear()

# KHU VỰC HỌC TẬP & MUA HÀNG
@dp.message(F.text.startswith("🎓 Vào học"))
async def student_learning_area(message: types.Message):
    user_id = str(message.from_user.id)
    cname = message.text.replace("🎓 Vào học ", "").strip()
    data = load_data()
    target_id = next((cid for cid, cinfo in data["courses"].items() if cinfo["name"] == cname), None)
    
    if not target_id or target_id not in data["users"].get(user_id, {}).get("courses", []):
        await message.answer("❌ Bạn chưa có quyền học môn này!")
        return
    lessons = data["courses"][target_id].get("lessons", [])
    if not lessons:
        await message.answer("🚧 Môn này chưa có bài giảng nào.")
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text=f"▶ {l['name']}", url=l['link'])] for l in lessons])
    await message.answer(f"🎓 **{cname}**:", reply_markup=kb, parse_mode="Markdown")

@dp.message(F.text == "📖 Bảng danh sách")
async def show_courses(message: types.Message):
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cid, cinfo in data.get("courses", {}).items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📘 {cinfo['name']} - {cinfo['price']:,}đ", callback_data=f"view_course_{cid}")])
    for cid, cinfo in data.get("combos", {}).items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📦 {cinfo['name']} - {cinfo['price']:,}đ", callback_data=f"view_combo_{cid}")])
    await message.answer("📚 Chọn môn hoặc Combo cần thanh toán:", reply_markup=kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("view_course_") | F.data.startswith("view_combo_"))
async def process_course_view(callback: types.CallbackQuery):
    data = load_data()
    item_type = "combo" if "view_combo_" in callback.data else "course"
    item_id = callback.data.split(f"view_{item_type}_")[1]
    
    info = data["combos"].get(item_id) if item_type == "combo" else data["courses"].get(item_id)
    if not info: return
    
    price = info['price']
    user_id = callback.from_user.id
    transfer_content = f"MUAKHOA {user_id}"
    qr_url = f"https://img.vietqr.io/image/mbbank-0812847035-compact2.png?amount={price}&addInfo={transfer_content}&accountName=PHUNG THANH NAM"

    msg = (
        f"📘 **{info['name']}**\n💰 **Giá:** `{price:,} VNĐ`\n\n"
        f"🏦 **QUÉT MÃ THANH TOÁN TỰ ĐỘNG:**\n"
        f"▪️ Ngân hàng: **MB Bank**\n"
        f"▪️ STK: **0812847035**\n"
        f"▪️ Nội dung: `{transfer_content}`\n\n"
        f"⏳ _Chuyển khoản xong QR sẽ tự biến mất và nhận code tự động!_"
    )
    sent = await callback.message.answer_photo(photo=qr_url, caption=msg, parse_mode="Markdown")
    
    str_uid = str(user_id)
    if str_uid not in data["users"]:
        data["users"][str_uid] = {"name": callback.from_user.full_name, "role": "guest", "courses": [], "last_active": datetime.now().isoformat()}
    data["users"][str_uid]["qr_msg_id"] = sent.message_id
    save_data(data)
    await callback.answer()

@dp.message(F.text == "🔑 Nhập code")
async def enter_code_prompt(message: types.Message):
    await message.answer("🔑 Nhập mã Code kích hoạt:")

@dp.message(F.text.regexp(r'^[A-Z0-9-]+$'))
async def check_code(message: types.Message):
    code = message.text.strip()
    data = load_data()
    if code in data["codes"]:
        c_info = data["codes"][code]
        if c_info["used"]:
            await message.answer("❌ Mã này đã được dùng!")
        else:
            data["codes"][code]["used"] = True
            user_id = str(message.from_user.id)
            c_type = c_info.get("type", "course")
            
            if c_type == "combo":
                to_grant = data["combos"][c_info["id"]]["course_ids"]
                name = data["combos"][c_info["id"]]["name"]
            elif c_type == "auto":
                to_grant = list(data["courses"].keys())[:1]
                name = "Khóa học tự động"
            else:
                c_id = c_info.get("course") or c_info.get("id")
                to_grant = [c_id]
                name = data["courses"][c_id]["name"]
            
            for cid in to_grant:
                if cid not in data["users"][user_id]["courses"]:
                    data["users"][user_id]["courses"].append(cid)
            save_data(data)
            await message.answer(f"🎉 Kích hoạt thành công **{name}**!", reply_markup=get_user_menu(user_id), parse_mode="Markdown")
    else:
        if len(code) > 4: 
            await message.answer("❌ Mã không tồn tại.")

@dp.message(F.text == "💬 Tư vấn - CSKH")
async def support_contact(message: types.Message):
    await message.answer("👨‍💻 Liên hệ Admin:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Chat Admin", url=f"https://t.me/{ADMIN_USERNAME}")]]))

@dp.message(F.text == "ℹ️ Giới thiệu")
async def intro_system(message: types.Message):
    await message.answer(load_data().get("intro_text", "Mini-LMS"), parse_mode="Markdown")

# ĐƯỜNG ỐNG WEBHOOK SEPAY
async def auto_payment_webhook(request):
    try:
        data = await request.json()
        transfer_content = data.get("content", "").upper()
        amount = int(data.get("transferAmount", 0))
        
        if "MUAKHOA" in transfer_content:
            words = transfer_content.replace(",", " ").replace(".", " ").split()
            user_id = None
            for i, word in enumerate(words):
                if word == "MUAKHOA" and i + 1 < len(words):
                    user_id = words[i + 1]
                    break
            
            if not user_id:
                return web.json_response({"status": "Khong tim thay user_id"})
                
            db = load_data()
            to_grant = []
            item_name = ""
            
            for cid, cinfo in db["courses"].items():
                if amount == cinfo["price"]:
                    to_grant = [cid]
                    item_name = cinfo["name"]
                    break
            
            if not to_grant:
                for cid, cinfo in db.get("combos", {}).items():
                    if amount == cinfo["price"]:
                        to_grant = cinfo["course_ids"]
                        item_name = cinfo["name"]
                        break
            
            if not to_grant:
                await bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ Cảnh báo: Giao dịch `{amount:,}đ` với nội dung `{transfer_content}` không khớp giá khóa học nào!")
                return web.json_response({"status": "Khong khop gia"})
            
            str_uid = str(user_id)
            if str_uid not in db["users"]:
                db["users"][str_uid] = {"name": "Học viên", "role": "member", "courses": [], "qr_msg_id": None, "last_active": datetime.now().isoformat()}
            
            qr_msg_id = db["users"][str_uid].get("qr_msg_id")
            if qr_msg_id:
                try:
                    await bot.delete_message(chat_id=int(str_uid), message_id=qr_msg_id)
                except Exception:
                    pass 
            db["users"][str_uid]["qr_msg_id"] = None
            
            for cid in to_grant:
                if cid not in db["users"][str_uid]["courses"]:
                    db["users"][str_uid]["courses"].append(cid)
            db["users"][str_uid]["role"] = "member"
            
            new_code = generate_random_code("AUTO")
            db["codes"][new_code] = {"type": "auto", "id": "auto", "used": True}
            save_data(db)
            
            msg_to_user = (
                f"🎉 **THANH TOÁN THÀNH CÔNG!**\n\n"
                f"💳 Hệ thống đã nhận được `{amount:,}đ`.\n"
                f"🎫 Mã Code kích hoạt của bạn là: `{new_code}`\n\n"
                f"✅ _Hệ thống đã tự động thu hồi mã QR và cấp quyền truy cập **{item_name}** cho bạn._\n\n"
                f"👉 **Hãy gõ lệnh /start để Menu hiện ra nút 🎓 Vào Học nhé!**"
            )
            try:
                await bot.send_message(chat_id=int(str_uid), text=msg_to_user, parse_mode="Markdown")
            except Exception as e:
                await bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ Không thể gửi tin nhắn cho user {str_uid}: {str(e)}")
            
            await bot.send_message(chat_id=ADMIN_ID, text=f"🤑 **TIỀN VÀO NỔ THÀNH CÔNG!**\nKhách `{str_uid}` chuyển `{amount:,}đ`.\n✅ Đã thu hồi QR và nhả code **{item_name}**.", parse_mode="Markdown")
            
        return web.json_response({"status": "success"})
    except Exception as e:
        try:
            await bot.send_message(chat_id=ADMIN_ID, text=f"❌ Lỗi Webhook: {str(e)}")
        except Exception:
            pass
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
