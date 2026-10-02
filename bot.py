import asyncio
import json
import os
import random
import string
from datetime import datetime
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import CommandStart, StateFilter, Command
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, ReplyKeyboardMarkup, KeyboardButton
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiohttp import web

# --- CẤU HÌNH TOKEN MỚI ---
TOKEN = "8653171399:AAHz-Pt0olwmPYabflt4LUicSEsc8lFwc_o"
ADMIN_ID = 8956161451
ADMIN_USERNAME = "thanhnam1608" 
DATA_FILE = "data.json"

bot = Bot(token=TOKEN)
dp = Dispatcher()

class AdminStates(StatesGroup):
    waiting_for_broadcast = State()
    waiting_for_new_price = State()
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
    
    # Trạng thái quản lý Chương & Tệp bài giảng
    waiting_for_chapter_name = State()
    waiting_for_lesson_name = State()
    waiting_for_lesson_content = State() # Đổi từ link sang nội dung văn bản

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "users": {},
            "courses": {
                "Toan": {"name": "Môn Toán", "price": 3000, "chapters": []},
                "Van": {"name": "Môn Văn", "price": 50000, "chapters": []}
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
        for cid, cinfo in data["courses"].items():
            if "lessons" in cinfo and "chapters" not in cinfo:
                cinfo["chapters"] = [{"chapter_name": "Tài liệu chung", "lessons": cinfo["lessons"]}]
                del cinfo["lessons"]
            if "chapters" not in cinfo:
                cinfo["chapters"] = []
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
        if seconds < 60: return "Vừa hoạt động"
        minutes = seconds // 60
        if minutes < 60: return f"Không dùng {minutes} phút trước"
        hours = minutes // 60
        if hours < 24: return f"Không dùng {hours} giờ trước"
        return f"Không dùng {hours // 24} ngày trước"
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
        data["users"][str_uid] = {"name": name, "role": "guest", "courses": [], "qr_msg_id": None, "last_active": now_iso}
    else:
        data["users"][str_uid]["name"] = name
        data["users"][str_uid]["last_active"] = now_iso
    save_data(data)

    if user_id == ADMIN_ID:
        admin_kb = InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="📚 Quản lý Môn học (Lẻ)", callback_data="admin_courses"),
             InlineKeyboardButton(text="📦 Quản lý Combo (Gộp)", callback_data="admin_combos")],
            [InlineKeyboardButton(text="📂 Quản lý Tài liệu & Bài giảng", callback_data="admin_manage_chapters")],
            [InlineKeyboardButton(text="📝 Sửa phần Giới thiệu", callback_data="edit_intro")],
            [InlineKeyboardButton(text="👥 Quản lý Học viên & Thời gian", callback_data="admin_users_list")],
            [InlineKeyboardButton(text="🖨 Máy in Code", callback_data="admin_print_codes")],
            [InlineKeyboardButton(text="📢 Thông báo Tổng", callback_data="admin_broadcast")]
        ])
        await message.answer(f"👑 Chào Boss tối cao **{name}**!\nBảng điều khiển dành riêng cho bạn:", reply_markup=admin_kb, parse_mode="Markdown")
    else:
        await message.answer(f"👋 Xin chào {name}!\nChào mừng bạn đến với Hệ thống Bot Học tập.\n\nHãy chọn chức năng ở menu bên dưới nhé 👇", reply_markup=get_user_menu(user_id))

@dp.message(Command("cancel"))
async def cancel_handler(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔄 Đã hủy trạng thái hiện tại. Gõ /start để về menu chính.", reply_markup=get_user_menu(message.from_user.id))

# --- QUẢN LÝ TÀI LIỆU (NHẬP NỘI DUNG TRỰC TIẾP) ---
@dp.callback_query(F.data == "admin_manage_chapters")
async def admin_manage_chapters(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cid, cinfo in data["courses"].items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📂 {cinfo['name']}", callback_data=f"ch_course_{cid}")])
    await callback.message.answer("📁 **QUẢN LÝ TÀI LIỆU & BÀI GIẢNG:**\nChọn môn học:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("ch_course_"))
async def admin_select_course_chapters(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    course_id = callback.data.split("ch_course_")[1]
    data = load_data()
    course = data["courses"].get(course_id)
    if not course: return

    kb = InlineKeyboardMarkup(inline_keyboard=[])
    chapters = course.get("chapters", [])
    for idx, chap in enumerate(chapters):
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📑 {chap['chapter_name']} ({len(chap.get('lessons', []))} tệp)", callback_data=f"view_chap_{course_id}_{idx}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Thêm Chương Mới", callback_data=f"add_chap_{course_id}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅ Quay lại", callback_data="admin_manage_chapters")])
    
    await callback.message.answer(f"📚 **Môn: {course['name']}**\nDanh sách các Chương tài liệu:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("add_chap_"))
async def ask_chapter_name(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.update_data(chap_course_id=callback.data.split("add_chap_")[1])
    await state.set_state(AdminStates.waiting_for_chapter_name)
    await callback.message.answer("📝 Nhập **Tên Chương / Lớp tài liệu** mới:", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_chapter_name))
async def save_new_chapter(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    db = load_data()
    if "chapters" not in db["courses"][user_data["chap_course_id"]]:
        db["courses"][user_data["chap_course_id"]]["chapters"] = []
    db["courses"][user_data["chap_course_id"]]["chapters"].append({"chapter_name": message.text.strip(), "lessons": []})
    save_data(db)
    await message.answer("✅ Đã thêm chương thành công!", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data.startswith("view_chap_"))
async def view_chapter_details(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    parts = callback.data.split("_")
    course_id = parts[2]
    chap_idx = int(parts[3])
    
    data = load_data()
    chap = data["courses"][course_id]["chapters"][chap_idx]
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    lessons = chap.get("lessons", [])
    
    text = f"📑 **Chương: {chap['chapter_name']}**\n\n"
    if lessons:
        for l_idx, lesson in enumerate(lessons):
            text += f"▪️ {l_idx+1}. {lesson['name']}\n"
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"❌ Xóa bài: {lesson['name'][:12]}...", callback_data=f"dellesson_{course_id}_{chap_idx}_{l_idx}")])
    else:
        text += "_Chưa có tệp bài giảng nào._\n"
        
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ Thêm Bài Học / Công Thức", callback_data=f"addlesson_{course_id}_{chap_idx}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="🗑 XÓA CHƯƠNG NÀY", callback_data=f"delchap_{course_id}_{chap_idx}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="⬅️ Quay lại", callback_data=f"ch_course_{course_id}")])
    
    await callback.message.answer(text, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("delchap_"))
async def delete_chapter_item(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    parts = callback.data.split("_")
    course_id = parts[1]
    chap_idx = int(parts[2])
    
    db = load_data()
    chapters = db["courses"][course_id]["chapters"]
    if 0 <= chap_idx < len(chapters):
        removed = chapters.pop(chap_idx)
        save_data(db)
        await callback.message.answer(f"🗑 Đã xóa toàn bộ chương: **{removed['chapter_name']}**")
    await callback.answer()

@dp.callback_query(F.data.startswith("addlesson_"))
async def ask_lesson_name(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    parts = callback.data.split("_")
    await state.update_data(lesson_course_id=parts[1], lesson_chap_idx=int(parts[2]))
    await state.set_state(AdminStates.waiting_for_lesson_name)
    await callback.message.answer("📝 Bước 1: Nhập **TÊN BÀI HỌC** (Ví dụ: Định lý Vi-ét):", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_lesson_name))
async def ask_lesson_content(message: types.Message, state: FSMContext):
    await state.update_data(lesson_name=message.text.strip())
    await state.set_state(AdminStates.waiting_for_lesson_content)
    
    hint_text = (
        "📝 Bước 2: Nhập **NỘI DUNG BÀI HỌC / CÔNG THỨC**.\n\n"
        "Bạn có thể gõ nội dung dài, công thức, ví dụ cách áp dụng và xuống dòng thoải mái. "
        "Mẹo:\n"
        "▪️ Bôi đậm: `**Nội dung**`\n"
        "▪️ In nghiêng: `_Nội dung_`\n"
        "▪️ Khung code: \n\\`\\`\\`\nCông thức ở đây\n\\`\\`\\`"
    )
    await message.answer(hint_text, parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_lesson_content))
async def save_new_lesson(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    db = load_data()
    
    # Lưu nội dung trực tiếp (content) thay vì link
    db["courses"][user_data["lesson_course_id"]]["chapters"][user_data["lesson_chap_idx"]]["lessons"].append({
        "name": user_data["lesson_name"], 
        "content": message.text.strip()
    })
    save_data(db)
    await message.answer("✅ Đã lưu bài học thành công!", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data.startswith("dellesson_"))
async def delete_lesson_item(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    parts = callback.data.split("_")
    db = load_data()
    lessons = db["courses"][parts[1]]["chapters"][int(parts[2])]["lessons"]
    if 0 <= int(parts[3]) < len(lessons):
        lessons.pop(int(parts[3]))
        save_data(db)
        await callback.message.answer("🗑 Đã xóa bài học thành công!")
    await callback.answer()

# --- CÁC TÍNH NĂNG ADMIN KHÁC GIỮ NGUYÊN ---
@dp.callback_query(F.data == "admin_users_list")
async def admin_users_list(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    users = data.get("users", {})
    if not users:
        await callback.message.answer("👥 Chưa có học viên.")
        await callback.answer()
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    text_summary = f"👥 **HỌC VIÊN ({len(users)}):**\n\n"
    for uid, info in users.items():
        text_summary += f"▪️ {info.get('name')} (UID: `{uid}`)\n"
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"✉️ Nhắn riêng {info.get('name')}", callback_data=f"privatemsg_{uid}")])
    await callback.message.answer(text_summary, reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("privatemsg_"))
async def ask_private_message(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.update_data(private_target_uid=callback.data.split("_")[1])
    await state.set_state(AdminStates.waiting_for_private_msg)
    await callback.message.answer("✉️ Nhập nội dung tin nhắn riêng:", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_private_msg))
async def send_private_message_action(message: types.Message, state: FSMContext):
    user_data = await state.get_data()
    try:
        await bot.send_message(chat_id=int(user_data["private_target_uid"]), text=f"📩 **Tin nhắn từ Admin:**\n\n{message.text.strip()}", parse_mode="Markdown")
        await message.answer("✅ Đã gửi!", parse_mode="Markdown")
    except Exception as e:
        await message.answer(f"❌ Lỗi: {str(e)}")
    await state.clear()

@dp.callback_query(F.data == "admin_courses")
async def admin_manage_courses(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cid, cinfo in data["courses"].items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"✏️ {cinfo['name']} - {cinfo['price']:,}đ", callback_data=f"editprice_{cid}")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ THÊM MÔN HỌC MỚI", callback_data="add_course")])
    await callback.message.answer("🛠 **MÔN HỌC LẺ:**", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("editprice_"))
async def ask_new_price(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.update_data(edit_course_id=callback.data.split("_")[1])
    await state.set_state(AdminStates.waiting_for_new_price)
    await callback.message.answer("💰 Nhập giá mới (số):", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_new_price))
async def set_new_price(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit(): return
    user_data = await state.get_data()
    db = load_data()
    db["courses"][user_data["edit_course_id"]]["price"] = int(message.text.strip())
    save_data(db)
    await message.answer("✅ Đã cập nhật giá!", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "add_course")
async def ask_new_course_id(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_new_course_id)
    await callback.message.answer("➕ Nhập MÃ MÔN HỌC (viết liền không dấu):", parse_mode="Markdown")
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
    await callback.message.answer("💰 Nhập GIÁ MÔN HỌC (số):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_new_course_price))
async def save_new_course(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit(): return
    user_data = await state.get_data()
    db = load_data()
    db["courses"][user_data["new_course_id"]] = {"name": user_data["new_course_name"], "price": int(message.text.strip()), "chapters": []}
    save_data(db)
    await message.answer("✅ Đã thêm môn học thành công!", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "admin_combos")
async def admin_manage_combos(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for cid, cinfo in data.get("combos", {}).items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📦 {cinfo['name']} - {cinfo['price']:,}đ", callback_data="ignore")])
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ TẠO COMBO MỚI", callback_data="add_combo")])
    await callback.message.answer("📦 **COMBO:**", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "add_combo")
async def ask_new_combo_id(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_combo_id)
    await callback.message.answer("➕ Nhập MÃ COMBO:", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_combo_id))
async def ask_new_combo_name(message: types.Message, state: FSMContext):
    await state.update_data(combo_id=message.text.strip())
    await state.set_state(AdminStates.waiting_for_combo_name)
    await message.answer("📝 Nhập TÊN COMBO:", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_name))
async def ask_new_combo_courses(message: types.Message, state: FSMContext):
    await state.update_data(combo_name=message.text.strip())
    await state.set_state(AdminStates.waiting_for_combo_courses)
    await message.answer("🔗 Nhập các MÃ MÔN HỌC gộp (VD: Toan, Van):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_courses))
async def ask_new_combo_price(message: types.Message, state: FSMContext):
    await state.update_data(combo_courses=[c.strip() for c in message.text.strip().split(',') if c.strip()])
    await state.set_state(AdminStates.waiting_for_combo_price)
    await message.answer("💰 Nhập GIÁ COMBO (số):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_price))
async def save_new_combo(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit(): return
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
    await message.answer("✅ Đã cập nhật giới thiệu!", parse_mode="Markdown")
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
    await callback.message.answer("🖨 Chọn mục in mã code:", reply_markup=kb, parse_mode="Markdown")
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
    await callback.message.answer("📢 Nhập nội dung thông báo TỔNG gửi học viên:")
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
    await message.answer(f"✅ Đã gửi tới {success} học viên!", parse_mode="Markdown")
    await state.clear()

# --- KHU VỰC HỌC TẬP: ĐỌC NỘI DUNG VÀ KHÓA CHỐNG COPY ---
@dp.message(F.text.startswith("🎓 Vào học"))
async def student_learning_area(message: types.Message, state: FSMContext):
    await state.clear()
    user_id = str(message.from_user.id)
    cname = message.text.replace("🎓 Vào học ", "").strip()
    data = load_data()
    target_id = next((cid for cid, cinfo in data["courses"].items() if cinfo["name"] == cname), None)
    
    if not target_id or target_id not in data["users"].get(user_id, {}).get("courses", []):
        await message.answer("❌ Bạn chưa có quyền học môn này!")
        return
        
    course_info = data["courses"][target_id]
    chapters = course_info.get("chapters", [])
    
    if not chapters:
        await message.answer("🚧 Môn học này đang cập nhật tài liệu.")
        return

    text = f"🎓 **KHU VỰC HỌC TẬP: {cname}**\nBấm vào bài học để đọc nội dung:\n"
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for chap_idx, chap in enumerate(chapters):
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📂 --- {chap['chapter_name']} ---", callback_data="ignore")])
        for l_idx, lesson in enumerate(chap.get("lessons", [])):
            # Chuyển từ nút bấm URL (mở link) sang nút Callback (đọc bài)
            kb.inline_keyboard.append([InlineKeyboardButton(text=f"📖 {lesson['name']}", callback_data=f"readlesson_{target_id}_{chap_idx}_{l_idx}")])
            
    await message.answer(text, reply_markup=kb, parse_mode="Markdown")

# Xử lý hiển thị nội dung bài học khi học viên bấm nút
@dp.callback_query(F.data.startswith("readlesson_"))
async def read_lesson_content(callback: types.CallbackQuery):
    parts = callback.data.split("_")
    course_id = parts[1]
    chap_idx = int(parts[2])
    l_idx = int(parts[3])
    
    db = load_data()
    try:
        lesson = db["courses"][course_id]["chapters"][chap_idx]["lessons"][l_idx]
        
        # Lấy nội dung hoặc link cũ để hiển thị
        content = lesson.get("content", lesson.get("link", "Nội dung đang được cập nhật."))
        
        display_text = f"📚 **{lesson['name']}**\n\n{content}"
        
        # protect_content=True: NGĂN CHẶN FORWARD, LƯU VÀ CHỤP MÀN HÌNH TRÊN ĐIỆN THOẠI
        await callback.message.answer(display_text, parse_mode="Markdown", protect_content=True)
    except Exception as e:
        await callback.answer(f"Lỗi hiển thị bài học.", show_alert=True)
    await callback.answer()

@dp.message(F.text == "📖 Bảng danh sách")
async def show_courses(message: types.Message, state: FSMContext):
    await state.clear()
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
        f"⏳ _Chuyển khoản xong QR sẽ tự biến mất và cấp quyền học tự động!_"
    )
    sent = await callback.message.answer_photo(photo=qr_url, caption=msg, parse_mode="Markdown")
    str_uid = str(user_id)
    if str_uid not in data["users"]:
        data["users"][str_uid] = {"name": callback.from_user.full_name, "role": "guest", "courses": [], "last_active": datetime.now().isoformat()}
    data["users"][str_uid]["qr_msg_id"] = sent.message_id
    save_data(data)
    await callback.answer()

@dp.message(F.text == "🔑 Nhập code")
async def enter_code_prompt(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("🔑 Nhập mã Code kích hoạt:")

@dp.message(F.text.regexp(r'^[A-Z0-9-]+$'))
async def check_code(message: types.Message, state: FSMContext):
    await state.clear()
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
            elif c_type in ["auto", "evt"]:
                c_id = c_info.get("id")
                to_grant = [c_id] if c_id in data["courses"] else list(data["courses"].keys())[:1]
                name = data["courses"][to_grant[0]]["name"] if to_grant[0] in data["courses"] else "Khóa học"
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
        if len(code) > 4: await message.answer("❌ Mã không tồn tại.")

@dp.message(F.text == "💬 Tư vấn - CSKH")
async def support_contact(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👨‍‍💻 Liên hệ Admin:", reply_markup=InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="Chat Admin", url=f"https://t.me/{ADMIN_USERNAME}")]]))

@dp.message(F.text == "ℹ️ Giới thiệu")
async def intro_system(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer(load_data().get("intro_text", "Mini-LMS"), parse_mode="Markdown")

# WEBHOOK SEPAY
async def auto_payment_webhook(request):
    try:
        data = await request.json()
        transfer_content = data.get("content", "").upper()
        amount = int(data.get("transferAmount", 0))
        
        if "MUAKHOA" in transfer_content:
            words = transfer_content.replace(",", " ").replace(".", " ").split()
            user_id = next((words[i + 1] for i, word in enumerate(words) if word == "MUAKHOA" and i + 1 < len(words)), None)
            if not user_id: return web.json_response({"status": "Khong tim thay user_id"})
                
            db = load_data()
            to_grant, item_name, matched_id, item_type = [], "", "", "course"
            
            for cid, cinfo in db["courses"].items():
                if amount == cinfo["price"]:
                    to_grant, item_name, matched_id, item_type = [cid], cinfo["name"], cid, "course"
                    break
            if not to_grant:
                for cid, cinfo in db.get("combos", {}).items():
                    if amount == cinfo["price"]:
                        to_grant, item_name, matched_id, item_type = cinfo["course_ids"], cinfo["name"], cid, "combo"
                        break
            if not to_grant:
                return web.json_response({"status": "Khong khop gia"})
            
            str_uid = str(user_id)
            if str_uid not in db["users"]:
                db["users"][str_uid] = {"name": "Học viên", "role": "member", "courses": [], "qr_msg_id": None, "last_active": datetime.now().isoformat()}
            
            qr_msg_id = db["users"][str_uid].get("qr_msg_id")
            if qr_msg_id:
                try: await bot.delete_message(chat_id=int(str_uid), message_id=qr_msg_id)
                except Exception: pass 
            db["users"][str_uid]["qr_msg_id"] = None
            
            for cid in to_grant:
                if cid not in db["users"][str_uid]["courses"]:
                    db["users"][str_uid]["courses"].append(cid)
            db["users"][str_uid]["role"] = "member"
            
            new_code = generate_random_code("EVT")
            db["codes"][new_code] = {"type": item_type, "id": matched_id, "used": False}
            save_data(db)
            
            try:
                await bot.send_message(chat_id=int(str_uid), text=f"🎉 **THANH TOÁN THÀNH CÔNG!**\n\n💳 Nhận `{amount:,}đ`.\n✅ Đã cấp quyền **{item_name}**.\n\n👉 Gõ `/start` để vào học!", parse_mode="Markdown")
            except Exception: pass
            
            await bot.send_message(chat_id=ADMIN_ID, text=f"🤑 **TIỀN VÀO NỔ!**\nKhách `{str_uid}` chuyển `{amount:,}đ`.\n✅ Đã cấp **{item_name}**.\n🎫 Mã sự kiện: `{new_code}`", parse_mode="Markdown")
            
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
