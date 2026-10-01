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

def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "users": {},
            "courses": {
                "Toan": {"name": "Môn Toán", "price": 3000, "lessons": []},
                "Van": {"name": "Môn Văn", "price": 50000}
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
            [InlineKeyboardButton(text="📚 Quản lý Môn học (Lẻ)", callback_data="admin_courses"),
             InlineKeyboardButton(text="📦 Quản lý Combo (Gộp)", callback_data="admin_combos")],
            [InlineKeyboardButton(text="📂 Quản lý Bài giảng", callback_data="admin_lessons"),
             InlineKeyboardButton(text="📝 Sửa phần Giới thiệu", callback_data="edit_intro")],
            [InlineKeyboardButton(text="🖨 Máy in Code", callback_data="admin_print_codes")],
            [InlineKeyboardButton(text="👥 Thống kê", callback_data="admin_stats"),
             InlineKeyboardButton(text="📢 Thông báo", callback_data="admin_broadcast")]
        ])
        await message.answer(f"👑 Chào Boss tối cao **{name}**!\nBảng điều khiển dành riêng cho bạn:", reply_markup=admin_kb, parse_mode="Markdown")
    else:
        await message.answer(
            f"👋 Xin chào {name}!\nChào mừng bạn đến với Hệ thống Bot Học tập.\n\nHãy chọn chức năng ở menu bên dưới nhé 👇", 
            reply_markup=get_user_menu(user_id)
        )

# ADMIN - QUẢN LÝ MÔN HỌC
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
    course_id = callback.data.split("_")[1]
    data = load_data()
    await state.update_data(edit_course_id=course_id)
    await state.set_state(AdminStates.waiting_for_edit_course_name)
    await callback.message.answer(f"✏ Nhập tên mới cho **{data['courses'][course_id]['name']}**:", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_edit_course_name))
async def set_edit_course_name(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    user_data = await state.get_data()
    db = load_data()
    db["courses"][user_data["edit_course_id"]]["name"] = new_name
    save_data(db)
    await message.answer(f"✅ Đã đổi tên thành: **{new_name}**", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data.startswith("editprice_"))
async def ask_new_price(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    course_id = callback.data.split("_")[1]
    data = load_data()
    await state.update_data(edit_course_id=course_id)
    await state.set_state(AdminStates.waiting_for_new_price)
    await callback.message.answer(f"💰 Nhập giá mới cho **{data['courses'][course_id]['name']}** (chỉ số):", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_new_price))
async def set_new_price(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Chỉ được nhập số. Nhập lại:")
        return
    new_price = int(message.text.strip())
    user_data = await state.get_data()
    db = load_data()
    db["courses"][user_data["edit_course_id"]]["price"] = new_price
    save_data(db)
    await message.answer(f"✅ Đã đổi giá thành **{new_price:,}đ**", parse_mode="Markdown")
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
    await message.answer("📝 Nhập TÊN MÔN HỌC:", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_new_course_name))
async def ask_new_course_price(message: types.Message, state: FSMContext):
    await state.update_data(new_course_name=message.text.strip())
    await state.set_state(AdminStates.waiting_for_new_course_price)
    await message.answer("💰 Nhập GIÁ MÔN HỌC (chỉ số):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_new_course_price))
async def save_new_course(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Giá phải là số. Nhập lại:")
        return
    user_data = await state.get_data()
    db = load_data()
    db["courses"][user_data["new_course_id"]] = {"name": user_data["new_course_name"], "price": int(message.text.strip()), "lessons": []}
    save_data(db)
    await message.answer("✅ Đã thêm môn học thành công!", parse_mode="Markdown")
    await state.clear()

# ADMIN - COMBO & GIỚI THIỆU & BÀI GIẢNG & IN CODE & STATS
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
    await message.answer("📝 Nhập TÊN COMBO:", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_name))
async def ask_new_combo_courses(message: types.Message, state: FSMContext):
    await state.update_data(combo_name=message.text.strip())
    await state.set_state(AdminStates.waiting_for_combo_courses)
    await message.answer("🔗 Nhập các MÃ MÔN HỌC gộp, cách nhau bởi dấu phẩy (VD: Toan, Van):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_courses))
async def ask_new_combo_price(message: types.Message, state: FSMContext):
    courses = [c.strip() for c in message.text.strip().split(',') if c.strip()]
    await state.update_data(combo_courses=courses)
    await state.set_state(AdminStates.waiting_for_combo_price)
    await message.answer("💰 Nhập GIÁ COMBO (chỉ số):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_price))
async def save_new_combo(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Giá phải là số. Nhập lại:")
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

@dp.callback_query(F.data == "admin_stats")
async def admin_show_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    await callback.message.answer(f"📊 Khách đã chat: {len(data['users'])}\n✅ Lượt kích hoạt: {sum(1 for c in data['codes'].values() if c['used'])}", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def admin_ask_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_broadcast)
    await callback.message.answer("📢 Nhập nội dung thông báo gửi toàn bộ khách hàng:")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_broadcast))
async def admin_send_broadcast(message: types.Message, state: FSMContext):
    data = load_data()
    success = 0
    for uid in data["users"].keys():
        try:
            await message.send_copy(chat_id=uid)
            success += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
    await message.answer(f"✅ Đã gửi xong cho {success} khách!")
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
    for cid, cinfo in data["courses"].items():
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
    data["users"][str(user_id)]["qr_msg_id"] = sent.message_id
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

# ĐƯỜNG ỐNG WEBHOOK SEPAY THÔNG MINH (BẮT USER ID CHUẨN XÁC)
async def auto_payment_webhook(request):
    try:
        data = await request.json()
        transfer_content = data.get("content", "").upper()
        amount = int(data.get("transferAmount", 0))
        
        if "MUAKHOA" in transfer_content:
            # Tách chuỗi linh hoạt lấy ra ID số nằm sau chữ MUAKHOA
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
            
            # Check giá khớp môn lẻ
            for cid, cinfo in db["courses"].items():
                if amount == cinfo["price"]:
                    to_grant = [cid]
                    item_name = cinfo["name"]
                    break
            
            # Check giá khớp Combo nếu môn lẻ không khớp
            if not to_grant:
                for cid, cinfo in db.get("combos", {}).items():
                    if amount == cinfo["price"]:
                        to_grant = cinfo["course_ids"]
                        item_name = cinfo["name"]
                        break
            
            if not to_grant:
                # Báo về cho Admin biết có khách chuyển sai giá
                await bot.send_message(chat_id=ADMIN_ID, text=f"⚠️ Cảnh báo: Có giao dịch chuyển `{amount:,}đ` với nội dung `{transfer_content}` nhưng không khớp giá khóa học nào!")
                return web.json_response({"status": "Khong khop gia"})
            
            if user_id in db["users"]:
                # Xóa mã QR cũ
                qr_msg_id = db["users"][user_id].get("qr_msg_id")
                if qr_msg_id:
                    try:
                        await bot.delete_message(chat_id=int(user_id), message_id=qr_msg_id)
                        db["users"][user_id]["qr_msg_id"] = None
                    except Exception:
                        pass 
                
                # Cấp quyền
                for cid in to_grant:
                    if cid not in db["users"][user_id]["courses"]:
                        db["users"][user_id]["courses"].append(cid)
                
                new_code = generate_random_code("AUTO")
                db["codes"][new_code] = {"type": "auto", "id": "auto", "used": True}
                save_data(db)
                
                # Báo cho khách
                await bot.send_message(
                    chat_id=int(user_id), 
                    text=f"🎉 **THANH TOÁN THÀNH CÔNG!**\n\n💳 Nhận `{amount:,}đ`.\n🎫 Mã Code: `{new_code}`\n\n✅ Đã kích hoạt **{item_name}**. Gõ `/start` để xem nút Vào Học!", 
                    parse_mode="Markdown"
                )
            
            # Báo cho Admin
            await bot.send_message(chat_id=ADMIN_ID, text=f"🤑 **TIỀN VÀO!**\nKhách `{user_id}` chuyển `{amount:,}đ`.\n✅ Đã tự động duyệt: **{item_name}**.", parse_mode="Markdown")
            
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
