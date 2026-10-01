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
    
    # Quản lý môn học & Giới thiệu
    waiting_for_edit_course_name = State()
    waiting_for_new_course_id = State()
    waiting_for_new_course_name = State()
    waiting_for_new_course_price = State()
    waiting_for_intro = State()
    
    # Quản lý Combo
    waiting_for_combo_id = State()
    waiting_for_combo_name = State()
    waiting_for_combo_courses = State()
    waiting_for_combo_price = State()

# --- XỬ LÝ DỮ LIỆU ---
def load_data():
    if not os.path.exists(DATA_FILE):
        default_data = {
            "users": {},
            "courses": {
                "Toan": {"name": "Môn Toán", "price": 60000, "lessons": []},
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
        return data

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

# ==========================================
# 1. ADMIN - QUẢN LÝ MÔN HỌC LẺ (THÊM, SỬA TÊN, SỬA GIÁ)
# ==========================================
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
    await callback.message.answer("🛠 **QUẢN LÝ MÔN HỌC LẺ:**\nBấm vào nút tương ứng để Sửa Tên/Giá hoặc Thêm môn mới:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("editname_"))
async def ask_edit_course_name(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    course_id = callback.data.split("_")[1]
    data = load_data()
    await state.update_data(edit_course_id=course_id)
    await state.set_state(AdminStates.waiting_for_edit_course_name)
    await callback.message.answer(f"✏ Bạn đang sửa tên cho môn: **{data['courses'][course_id]['name']}**.\n👉 Vui lòng nhắn tên mới:", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_edit_course_name))
async def set_edit_course_name(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    user_data = await state.get_data()
    course_id = user_data["edit_course_id"]
    db = load_data()
    db["courses"][course_id]["name"] = new_name
    save_data(db)
    await message.answer(f"✅ Đã cập nhật tên môn học thành: **{new_name}**", parse_mode="Markdown")
    await state.clear()

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
    await message.answer(f"✅ Đã cập nhật giá mới của **{db['courses'][course_id]['name']}** thành **{new_price:,}đ**", parse_mode="Markdown")
    await state.clear()

@dp.callback_query(F.data == "add_course")
async def ask_new_course_id(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_new_course_id)
    await callback.message.answer("➕ **THÊM MÔN HỌC MỚI (1/3):**\nNhập MÃ MÔN HỌC (viết liền, không dấu, ví dụ: Anh, Ly):", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_new_course_id))
async def ask_new_course_name(message: types.Message, state: FSMContext):
    new_id = message.text.strip()
    if not new_id.isalnum():
        await message.answer("❌ Lỗi: Mã môn học chỉ chứa chữ cái và số, không dấu cách. Nhập lại:")
        return
    await state.update_data(new_course_id=new_id)
    await state.set_state(AdminStates.waiting_for_new_course_name)
    await message.answer("📝 **Bước 2/3:** Vui lòng nhập TÊN MÔN HỌC (ví dụ: Môn Tiếng Anh):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_new_course_name))
async def ask_new_course_price(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    await state.update_data(new_course_name=new_name)
    await state.set_state(AdminStates.waiting_for_new_course_price)
    await message.answer("💰 **Bước 3/3:** Vui lòng nhập GIÁ MÔN HỌC (chỉ ghi số, ví dụ: 70000):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_new_course_price))
async def save_new_course(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Lỗi: Giá tiền chỉ được nhập SỐ. Vui lòng nhập lại:")
        return
    new_price = int(message.text.strip())
    user_data = await state.get_data()
    new_id = user_data["new_course_id"]
    new_name = user_data["new_course_name"]

    db = load_data()
    db["courses"][new_id] = {"name": new_name, "price": new_price, "lessons": []}
    save_data(db)
    
    await message.answer(f"✅ **ĐÃ THÊM MÔN HỌC THÀNH CÔNG!**\n📘 Môn: {new_name}\n💰 Giá: {new_price:,}đ", parse_mode="Markdown")
    await state.clear()

# ==========================================
# 2. ADMIN - TẠO COMBO (GỘP MÔN)
# ==========================================
@dp.callback_query(F.data == "admin_combos")
async def admin_manage_combos(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Liệt kê các combo đang có
    for combo_id, combo_info in data.get("combos", {}).items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📦 {combo_info['name']} - {combo_info['price']:,}đ", callback_data="ignore")])
        
    kb.inline_keyboard.append([InlineKeyboardButton(text="➕ TẠO COMBO MỚI", callback_data="add_combo")])
    await callback.message.answer("📦 **QUẢN LÝ COMBO:**\nCombo giúp bạn bán 1 lượt nhiều môn học với giá ưu đãi.", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "add_combo")
async def ask_new_combo_id(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_combo_id)
    await callback.message.answer("➕ **TẠO COMBO (1/4):**\nNhập MÃ COMBO (viết liền không dấu, ví dụ: C1, TOANVAN):", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_combo_id))
async def ask_new_combo_name(message: types.Message, state: FSMContext):
    new_id = message.text.strip()
    await state.update_data(combo_id=new_id)
    await state.set_state(AdminStates.waiting_for_combo_name)
    await message.answer("📝 **Bước 2/4:** Nhập TÊN COMBO để khách hàng thấy (ví dụ: Combo 2 môn Toán + Văn):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_name))
async def ask_new_combo_courses(message: types.Message, state: FSMContext):
    new_name = message.text.strip()
    await state.update_data(combo_name=new_name)
    
    data = load_data()
    course_list = ", ".join([f"`{cid}` ({cinfo['name']})" for cid, cinfo in data["courses"].items()])
    
    await state.set_state(AdminStates.waiting_for_combo_courses)
    await message.answer(f"🔗 **Bước 3/4:** Bạn muốn gộp những môn nào vào Combo này?\n\n**Các mã môn hiện có:**\n{course_list}\n\n👉 Hãy nhắn các MÃ MÔN HỌC, cách nhau bằng dấu phẩy (Ví dụ: `Toan, Van`)", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_courses))
async def ask_new_combo_price(message: types.Message, state: FSMContext):
    # Xử lý chuỗi nhập vào: "Toan, Van" -> ["Toan", "Van"]
    raw_courses = message.text.strip().split(',')
    course_ids = [c.strip() for c in raw_courses if c.strip()]
    
    data = load_data()
    invalid_courses = [cid for cid in course_ids if cid not in data["courses"]]
    
    if invalid_courses:
        await message.answer(f"❌ Lỗi: Mã môn học `{', '.join(invalid_courses)}` không tồn tại. Vui lòng nhắn lại mã chuẩn:", parse_mode="Markdown")
        return
        
    await state.update_data(combo_courses=course_ids)
    await state.set_state(AdminStates.waiting_for_combo_price)
    await message.answer("💰 **Bước 4/4:** Nhập GIÁ BÁN cho toàn bộ Combo này (chỉ ghi số, ví dụ: 99000):", parse_mode="Markdown")

@dp.message(StateFilter(AdminStates.waiting_for_combo_price))
async def save_new_combo(message: types.Message, state: FSMContext):
    if not message.text.strip().isdigit():
        await message.answer("❌ Lỗi: Giá tiền chỉ được nhập SỐ. Vui lòng nhập lại:")
        return
    new_price = int(message.text.strip())
    user_data = await state.get_data()
    
    combo_id = user_data["combo_id"]
    combo_name = user_data["combo_name"]
    combo_courses = user_data["combo_courses"]

    db = load_data()
    db["combos"][combo_id] = {
        "name": combo_name, 
        "price": new_price, 
        "course_ids": combo_courses
    }
    save_data(db)
    
    course_names = ", ".join([db["courses"][c]["name"] for c in combo_courses])
    await message.answer(f"✅ **TẠO COMBO THÀNH CÔNG!**\n📦 Tên Combo: {combo_name}\n📘 Gồm các môn: {course_names}\n💰 Giá: {new_price:,}đ\n\nKhách hàng hiện đã có thể nhìn thấy và mua Combo này!", parse_mode="Markdown")
    await state.clear()

# ==========================================
# 3. ADMIN - SỬA LỜI GIỚI THIỆU
# ==========================================
@dp.callback_query(F.data == "edit_intro")
async def ask_edit_intro(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID: return
    await state.set_state(AdminStates.waiting_for_intro)
    await callback.message.answer("📝 **SỬA LỜI GIỚI THIỆU:**\nHãy nhắn nội dung giới thiệu mới của bạn (Có thể dùng Emoji và xuống dòng thoải mái):", parse_mode="Markdown")
    await callback.answer()

@dp.message(StateFilter(AdminStates.waiting_for_intro))
async def save_new_intro(message: types.Message, state: FSMContext):
    new_intro = message.text.strip()
    db = load_data()
    db["intro_text"] = new_intro
    save_data(db)
    await message.answer("✅ Đã cập nhật Lời Giới Thiệu thành công! Khách hàng sẽ thấy nội dung mới ngay lập tức.")
    await state.clear()

# ==========================================
# 4. ADMIN - QUẢN LÝ BÀI GIẢNG VÀ MÁY IN CODE
# ==========================================
@dp.callback_query(F.data == "admin_lessons")
async def admin_manage_lessons(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    for course_id, course_info in data["courses"].items():
        lesson_count = len(course_info.get("lessons", []))
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"➕ Thêm bài vào {course_info['name']} ({lesson_count} bài)", callback_data=f"addlesson_{course_id}")])
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

@dp.callback_query(F.data == "admin_print_codes")
async def show_print_code_menu(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Hiển thị nút in code cho từng khóa lẻ
    for cid, cinfo in data["courses"].items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"🖨 Môn lẻ: {cinfo['name']}", callback_data=f"gen_course_{cid}")])
    
    # Hiển thị nút in code cho từng Combo
    for cid, cinfo in data.get("combos", {}).items():
        kb.inline_keyboard.append([InlineKeyboardButton(text=f"📦 Combo: {cinfo['name']}", callback_data=f"gen_combo_{cid}")])
        
    await callback.message.answer("🖨 **MÁY IN CODE:**\nChọn Môn lẻ hoặc Combo bạn muốn in mã kích hoạt:", reply_markup=kb, parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data.startswith("gen_course_") | F.data.startswith("gen_combo_"))
async def admin_generate_code(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    
    data = load_data()
    item_type = "combo" if "gen_combo_" in callback.data else "course"
    item_id = callback.data.split(f"gen_{item_type}_")[1]
    
    new_code = generate_random_code(item_id.upper())
    
    # Lưu thuộc tính type để bot biết mã này là cho Combo hay Khóa lẻ
    data["codes"][new_code] = {"type": item_type, "id": item_id, "used": False}
    save_data(data)
    
    item_name = data["combos"][item_id]["name"] if item_type == "combo" else data["courses"][item_id]["name"]
    await callback.message.answer(f"✅ Đã tạo 1 mã kích hoạt cho **{item_name}**:\n\n`{new_code}`\n\n_(Mã chỉ dùng được 1 lần)_", parse_mode="Markdown")
    await callback.answer()

@dp.callback_query(F.data == "admin_stats")
async def admin_show_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID: return
    data = load_data()
    total_users = len(data["users"])
    used_codes = sum(1 for c in data["codes"].values() if c["used"])
    await callback.message.answer(f"📊 **THỐNG KÊ HỆ THỐNG**\n\n👥 **Khách đã chat:** {total_users}\n✅ **Lượt kích hoạt học:** {used_codes}", parse_mode="Markdown")
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
# 5. KHU VỰC HỌC TẬP CỦA HỌC VIÊN
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
        lessons_kb.inline_keyboard.append([InlineKeyboardButton(text=f"▶ {lesson['name']}", url=lesson['link'])])
        
    await message.answer(f"🎓 **KHU VỰC HỌC TẬP: {course_name_clicked}**\n\nChúc bạn học tập hiệu quả. Bấm vào bài học bên dưới để mở:", reply_markup=lessons_kb, parse_mode="Markdown")

# ==========================================
# 6. LUỒNG KHÁCH MUA HÀNG VÀ GỬI MÃ QR (HỖ TRỢ CẢ COMBO)
# ==========================================
@dp.message(F.text == "📖 Bảng danh sách")
async def show_courses(message: types.Message):
    data = load_data()
    courses_kb = InlineKeyboardMarkup(inline_keyboard=[])
    
    # Nút cho khóa lẻ
    for course_id, course_info in data["courses"].items():
        courses_kb.inline_keyboard.append([InlineKeyboardButton(text=f"📘 {course_info['name']} - {course_info['price']:,}đ", callback_data=f"view_course_{course_id}")])
    
    # Nút cho Combo (nếu có)
    for combo_id, combo_info in data.get("combos", {}).items():
        courses_kb.inline_keyboard.append([InlineKeyboardButton(text=f"📦 {combo_info['name']} - {combo_info['price']:,}đ", callback_data=f"view_combo_{combo_id}")])
        
    await message.answer("📚 **DANH SÁCH MÔN HỌC & COMBO:**\nChọn mục bạn muốn thanh toán:", reply_markup=courses_kb, parse_mode="Markdown")

@dp.callback_query(F.data.startswith("view_course_") | F.data.startswith("view_combo_"))
async def process_course_view(callback: types.CallbackQuery):
    data = load_data()
    item_type = "combo" if "view_combo_" in callback.data else "course"
    item_id = callback.data.split(f"view_{item_type}_")[1]
    
    if item_type == "combo":
        item_info = data["combos"].get(item_id)
        description = f"Gồm các môn: " + ", ".join([data["courses"][cid]["name"] for cid in item_info["course_ids"]])
    else:
        item_info = data["courses"].get(item_id)
        description = "Môn học lẻ"
        
    if not item_info: return
    
    price = item_info['price']
    user_id = callback.from_user.id
    transfer_content = f"MUAKHOA {user_id}"
    
    qr_url = f"https://img.vietqr.io/image/mbbank-0812847035-compact2.png?amount={price}&addInfo={transfer_content}&accountName=PHUNG THANH NAM"

    msg = (
        f"📘 **{item_info['name']}**\n"
        f"📝 _{description}_\n"
        f"💰 **Giá tiền:** `{price:,} VNĐ`\n\n"
        f"🏦 **HƯỚNG DẪN THANH TOÁN TỰ ĐỘNG:**\n"
        f"Hệ thống duyệt tự động 24/7. Bạn hãy quét mã QR hoặc chuyển đúng **Nội dung chuyển khoản** bên dưới:\n\n"
        f"▪️ Ngân hàng: **MB Bank**\n"
        f"▪️ STK: **0812847035**\n"
        f"▪️ Chủ TK: **PHUNG THANH NAM**\n"
        f"▪️ Nội dung: `{transfer_content}` _(Chạm vào để copy)_\n\n"
        f"⏳ _Sau khi nhận tiền, mã QR này sẽ TỰ ĐỘNG BIẾN MẤT và hệ thống sẽ cấp quyền học cho bạn!_"
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
        code_info = data["codes"][code]
        if code_info["used"]:
            await message.answer("❌ Mã Code này đã được sử dụng trước đó!")
        else:
            data["codes"][code]["used"] = True
            user_id = str(message.from_user.id)
            
            # Kiểm tra xem code này thuộc loại Combo hay Khóa lẻ
            c_type = code_info.get("type", "course")
            if c_type == "combo":
                c_id = code_info["id"]
                courses_to_grant = data["combos"][c_id]["course_ids"]
                item_name = data["combos"][c_id]["name"]
            else:
                # Tương thích ngược với mã code cũ (không có type)
                c_id = code_info.get("course") or code_info.get("id")
                courses_to_grant = [c_id]
                item_name = data["courses"][c_id]["name"]
            
            # Cấp quyền tất cả các môn trong danh sách
            for cid in courses_to_grant:
                if cid not in data["users"][user_id]["courses"]:
                    data["users"][user_id]["courses"].append(cid)
            data["users"][user_id]["role"] = "member"
            save_data(data)
            
            await message.answer(
                f"🎉 **KÍCH HOẠT THÀNH CÔNG!**\nBạn đã sở hữu: **{item_name}**.\nMenu đã được cập nhật nút **🎓 Vào Học** ở bên dưới 👇", 
                reply_markup=get_user_menu(user_id), parse_mode="Markdown"
            )
    else:
        if len(code) > 4: 
            await message.answer("❌ Mã Code không tồn tại hoặc sai định dạng.")

@dp.message(F.text == "💬 Tư vấn - CSKH")
async def support_contact(message: types.Message):
    support_kb = InlineKeyboardMarkup(inline_keyboard=[[InlineKeyboardButton(text="💬 Nhắn tin Admin", url=f"https://t.me/{ADMIN_USERNAME}")]])
    await message.answer("👨‍💻 Nếu bạn cần hỗ trợ, hãy nhắn Admin nhé!", reply_markup=support_kb)

@dp.message(F.text == "ℹ️ Giới thiệu")
async def intro_system(message: types.Message):
    data = load_data()
    intro_text = data.get("intro_text", "Hệ thống Mini-LMS")
    await message.answer(intro_text, parse_mode="Markdown")

# ==========================================
# 7. ĐƯỜNG ỐNG WEBHOOK SEPAY NHẬN TIỀN CẢ COMBO VÀ MÔN LẺ
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
            
            course_ids_to_grant = []
            item_name = ""
            
            # 1. Ưu tiên kiểm tra giá trùng với Môn lẻ trước
            for cid, cinfo in db["courses"].items():
                if amount == cinfo["price"]:
                    course_ids_to_grant = [cid]
                    item_name = cinfo["name"]
                    break
                    
            # 2. Nếu không khớp môn lẻ, kiểm tra xem có khớp giá Combo không
            if not course_ids_to_grant:
                for cid, cinfo in db.get("combos", {}).items():
                    if amount == cinfo["price"]:
                        course_ids_to_grant = cinfo["course_ids"]
                        item_name = cinfo["name"]
                        break
                        
            if not course_ids_to_grant:
                return web.json_response({"status": "Khong khop gia"})
            
            if user_id in db["users"]:
                # XÓA MÃ QR CŨ
                qr_msg_id = db["users"][user_id].get("qr_msg_id")
                if qr_msg_id:
                    try:
                        await bot.delete_message(chat_id=int(user_id), message_id=qr_msg_id)
                        db["users"][user_id]["qr_msg_id"] = None
                    except Exception:
                        pass 
                
                # CẤP QUYỀN TRUY CẬP (Có thể là 1 môn hoặc nhiều môn trong combo)
                for cid in course_ids_to_grant:
                    if cid not in db["users"][user_id]["courses"]:
                        db["users"][user_id]["courses"].append(cid)
                db["users"][user_id]["role"] = "member"
                
                # PHÁT 1 MÃ CODE TƯỢNG TRƯNG
                new_code = generate_random_code("AUTO")
                db["codes"][new_code] = {"type": "auto", "id": "auto", "used": True}
                save_data(db)
                
                msg_to_user = (
                    f"🎉 **THANH TOÁN THÀNH CÔNG!**\n\n"
                    f"💳 Hệ thống đã nhận được `{amount:,}đ`.\n"
                    f"🎫 Mã Code của bạn là: `{new_code}`\n\n"
                    f"✅ _Hệ thống đã tự động thu hồi mã QR và cấp quyền truy cập **{item_name}** cho bạn._\n\n"
                    f"👉 **Hãy gõ lệnh /start để Menu hiện ra các nút 🎓 Vào Học tương ứng nhé!**"
                )
                await bot.send_message(chat_id=int(user_id), text=msg_to_user, parse_mode="Markdown")
            
            msg_to_admin = (f"🤑 **TIỀN VÀO TÀI KHOẢN!**\nKhách `{user_id}` chuyển `{amount:,}đ`.\n✅ Bot đã tự động duyệt đơn: **{item_name}**.")
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
