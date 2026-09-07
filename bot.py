import os
import asyncio
import sqlite3
import logging
from pathlib import Path
from datetime import datetime

from aiohttp import web
from aiogram import Bot, Dispatcher, F, Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message, CallbackQuery, FSInputFile, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN", "")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))
UPI_ID = os.getenv("UPI_ID", "yourupi@upi")
STORE_NAME = os.getenv("STORE_NAME", "My Telegram Store")
PORT = int(os.getenv("PORT", "10000"))
WEBHOOK_SECRET = os.getenv("WEBHOOK_SECRET", "change-this-secret")
BASE_URL = os.getenv("BASE_URL", "")  # Example: https://your-service.onrender.com

DB_PATH = os.getenv("DB_PATH", "store.db")
QR_PATH = os.getenv("QR_PATH", "static/qr.png")

logging.basicConfig(level=logging.INFO)
router = Router()

def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = db()
    conn.executescript("""
    CREATE TABLE IF NOT EXISTS products (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        description TEXT DEFAULT '',
        price INTEGER NOT NULL,
        stock INTEGER DEFAULT -1,
        delivery TEXT DEFAULT ''
    );
    CREATE TABLE IF NOT EXISTS orders (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        username TEXT DEFAULT '',
        product_id INTEGER NOT NULL,
        utr TEXT DEFAULT '',
        status TEXT DEFAULT 'pending',
        created_at TEXT NOT NULL
    );
    """)
    count = conn.execute("SELECT COUNT(*) AS c FROM products").fetchone()["c"]
    if count == 0:
        conn.execute(
            

def main_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🛍️ PRODUCTS", callback_data="products"),
         InlineKeyboardButton(text="📦 MY ORDERS", callback_data="orders")],
        [InlineKeyboardButton(text="💬 SUPPORT", callback_data="support"),
         InlineKeyboardButton(text="✨ HOW TO BUY", callback_data="howto")]
    ])

def products_kb():
    conn = db()
    rows = conn.execute("SELECT * FROM products ORDER BY id DESC").fetchall()
    conn.close()
    kb = InlineKeyboardBuilder()
    for p in rows:
        stock = "🟢 IN STOCK" if p["stock"] != 0 else "🔴 OUT OF STOCK"
        kb.button(text=f"🛍️ {p['name']} — ₹{p['price']} | {stock}", callback_data=f"product:{p['id']}")
    kb.adjust(1)
    kb.row(InlineKeyboardButton(text="⬅️ BACK", callback_data="home"))
    return kb.as_markup()

@router.message(CommandStart())
async def start(message: Message):
    await message.answer(
        f"🛍️ <b>{STORE_NAME}</b>\n\n"
        "Choose an option below:",
        reply_markup=main_kb()
    )

@router.callback_query(F.data == "home")
async def "INSERT INTO products(name,description,price,stock,delivery) VALUES(?,?,?,?,?)",
            ("MEESHO JSON 205 OFF", "", 25, 3, "meesho_account_7508340520.json")
        )
    conn.commit()
    conn.close()home(call: CallbackQuery):
    await call.message.edit_text(
        f"🛍️ <b>{STORE_NAME}</b>\n\nChoose an option below:",
        reply_markup=main_kb()
    )
    await call.answer()

@router.callback_query(F.data == "products")
async def products(call: CallbackQuery):
    await call.message.edit_text("🛍️ <b>Products</b>\n\nChoose a product:", reply_markup=products_kb())
    await call.answer()

@router.callback_query(F.data.startswith("product:"))
async def product(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    conn = db()
    p = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    conn.close()
    if not p:
        await call.answer("Product not found.", show_alert=True)
        return
    if p["stock"] == 0:
        await call.answer("Out of stock.", show_alert=True)
        return
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text=f"💳 BUY — ₹{p['price']}", callback_data=f"buy:{pid}")],
        [InlineKeyboardButton(text="⬅️ BACK", callback_data="products")]
    ])
    stock = "🟢 IN STOCK" if p["stock"] != 0 else "🔴 OUT OF STOCK"
    await call.message.edit_text(
        f"🛍️ <b>{p['name']}</b>\n\n"
        f"{p['description']}\n\n"
        f"💰 Price: <b>₹{p['price']}</b>\n"
        f"{stock}",
        reply_markup=kb
    )
    await call.answer()

@router.callback_query(F.data.startswith("buy:"))
async def buy(call: CallbackQuery):
    pid = int(call.data.split(":")[1])
    conn = db()
    p = conn.execute("SELECT * FROM products WHERE id=?", (pid,)).fetchone()
    conn.close()
    if not p or p["stock"] == 0:
        await call.answer("Product unavailable.", show_alert=True)
        return

    conn = db()
    cur = conn.execute(
        "INSERT INTO orders(user_id,username,product_id,created_at) VALUES(?,?,?,?)",
        (call.from_user.id, call.from_user.username or "", pid, datetime.utcnow().isoformat())
    )
    order_id = cur.lastrowid
    conn.commit()
    conn.close()

    text = (
        f"💳 <b>Payment for Order #{order_id}</b>\n\n"
        f"Product: <b>{p['name']}</b>\n"
        f"Amount: <b>₹{p['price']}</b>\n\n"
        f"UPI ID: <code>{UPI_ID}</code>\n\n"
        "Scan the QR and complete the payment.\n"
        "⏳ Payment should be completed within 10 minutes.\n\n"
        "After payment, tap <b>I've Paid</b> and send your 12-digit UTR/transaction ID."
    )
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="📷 SHOW QR", callback_data=f"qr:{order_id}")],
        [InlineKeyboardButton(text="✅ I'VE PAID", callback_data=f"paid:{order_id}")],
        [InlineKeyboardButton(text="⬅️ BACK", callback_data="products")]
    ])
    await call.message.edit_text(text, reply_markup=kb)
    await call.answer()

@router.callback_query(F.data.startswith("qr:"))
async def qr(call: CallbackQuery):
    if not os.path.exists(QR_PATH):
        await call.answer("QR image is not configured yet.", show_alert=True)
        return
    await call.message.answer_photo(
        FSInputFile(QR_PATH),
        caption=f"💳 Pay using this QR\nUPI ID: <code>{UPI_ID}</code>"
    )
    await call.answer()

@router.callback_query(F.data.startswith("paid:"))
async def paid(call: CallbackQuery):
    order_id = int(call.data.split(":")[1])
    await call.message.answer(
        f"🧾 <b>Order #{order_id}</b>\n\n"
        "Enter your <b>12-digit UTR/transaction ID</b> using numbers only."
    )
    await call.answer()

@router.message(F.text.regexp(r"^\d{12}$"))
async def utr(message: Message):
    conn = db()
    order = conn.execute(
        "SELECT o.*, p.name, p.price, p.delivery FROM orders o JOIN products p ON p.id=o.product_id "
        "WHERE o.user_id=? AND o.status='pending' ORDER BY o.id DESC LIMIT 1",
        (message.from_user.id,)
    ).fetchone()
    if not order:
        conn.close()
        await message.answer("No pending order found. Please create an order first.")
        return

    conn.execute("UPDATE orders SET utr=? WHERE id=?", (message.text, order["id"]))
    conn.commit()
    conn.close()

    await message.answer(
        f"✅ UTR received for Order #{order['id']}.\n"
        "Your payment is waiting for admin verification."
    )
    if ADMIN_ID:
        await message.bot.send_message(
            ADMIN_ID,
            f"🔔 <b>New payment to verify</b>\n\n"
            f"Order: #{order['id']}\n"
            f"User: <code>{order['user_id']}</code> @{order['username']}\n"
            f"Product: {order['name']}\n"
            f"Amount: ₹{order['price']}\n"
            f"UTR: <code>{message.text}</code>",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                [InlineKeyboardButton(text="✅ APPROVE", callback_data=f"approve:{order['id']}"),
                 InlineKeyboardButton(text="❌ REJECT", callback_data=f"reject:{order['id']}")]
            ])
        )

@router.message()
async def other(message: Message):
    await message.answer("Please use /start and choose an option from the menu.")

@router.callback_query(F.data.startswith("approve:"))
async def approve(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Admin only.", show_alert=True)
        return
    oid = int(call.data.split(":")[1])
    conn = db()
    order = conn.execute(
        "SELECT o.*, p.name, p.delivery FROM orders o JOIN products p ON p.id=o.product_id WHERE o.id=?",
        (oid,)
    ).fetchone()
    if not order:
        conn.close()
        await call.answer("Order not found.", show_alert=True)
        return
    conn.execute("UPDATE orders SET status='approved' WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    await call.message.edit_text(f"✅ Order #{oid} approved.")
    await call.bot.send_message(
        order["user_id"],
        f"🎉 <b>Payment approved!</b>\n\n"
        f"Order: #{oid}\n"
        f"Product: <b>{order['name']}</b>\n\n"
        f"📦 Your delivery:\n<code>{order['delivery']}</code>"
    )
    await call.answer()

@router.callback_query(F.data.startswith("reject:"))
async def reject(call: CallbackQuery):
    if call.from_user.id != ADMIN_ID:
        await call.answer("Admin only.", show_alert=True)
        return
    oid = int(call.data.split(":")[1])
    conn = db()
    order = conn.execute("SELECT user_id FROM orders WHERE id=?", (oid,)).fetchone()
    conn.execute("UPDATE orders SET status='rejected' WHERE id=?", (oid,))
    conn.commit()
    conn.close()
    await call.message.edit_text(f"❌ Order #{oid} rejected.")
    if order:
        await call.bot.send_message(order["user_id"], f"❌ Payment for Order #{oid} was rejected. Please contact support.")
    await call.answer()

@router.callback_query(F.data == "orders")
async def orders(call: CallbackQuery):
    conn = db()
    rows = conn.execute(
        "SELECT o.id,o.status,o.created_at,p.name,p.price FROM orders o JOIN products p ON p.id=o.product_id "
        "WHERE o.user_id=? ORDER BY o.id DESC LIMIT 10",
        (call.from_user.id,)
    ).fetchall()
    conn.close()
    if not rows:
        text = "📦 <b>My Orders</b>\n\nNo orders yet."
    else:
        lines = [f"📦 <b>My Orders</b>\n"]
        for r in rows:
            lines.append(f"#{r['id']} • {r['name']} • ₹{r['price']} • <b>{r['status'].upper()}</b>")
        text = "\n".join(lines)
    await call.message.edit_text(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="⬅️ BACK", callback_data="home")]
    ]))
    await call.answer()

@router.callback_query(F.data == "howto")
async def howto(call: CallbackQuery):
    await call.message.edit_text(
        "✨ <b>How to Buy</b>\n\n"
        "1. Open Products.\n"
        "2. Select your product.\n"
        "3. Tap BUY.\n"
        "4. Pay the shown amount to the UPI ID/QR.\n"
        "5. Tap I'VE PAID.\n"
        "6. Enter your 12-digit UTR.\n"
        "7. Wait for admin verification.\n"
        "8. After approval, your product is delivered automatically.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ BACK", callback_data="home")]
        ])
    )
    await call.answer()

@router.callback_query(F.data == "support")
async def support(call: CallbackQuery):
    await call.message.edit_text(
        "💬 <b>Support</b>\n\n"
        "For payment/order issues, contact the store administrator.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="⬅️ BACK", callback_data="home")]
        ])
    )
    await call.answer()

async def health(request):
    return web.Response(text="OK")

async def main():
    if not BOT_TOKEN:
        raise RuntimeError("BOT_TOKEN is missing.")
    init_db()
    bot = Bot(BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
    dp = Dispatcher()
    dp.include_router(router)

    app = web.Application()
    app.router.add_get("/", health)
    app.router.add_get("/health", health)

    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, "0.0.0.0", PORT)
    await site.start()

    if BASE_URL:
        webhook_url = f"{BASE_URL.rstrip('/')}/telegram/{WEBHOOK_SECRET}"
        await bot.set_webhook(webhook_url, drop_pending_updates=True)
        logging.info("Webhook set: %s", webhook_url)

        async def telegram_webhook(request):
            from aiogram.types import Update
            data = await request.json()
            update = Update.model_validate(data, context={"bot": bot})
            await dp.feed_update(bot, update)
            return web.Response(text="OK")
        app.router.add_post(f"/telegram/{WEBHOOK_SECRET}", telegram_webhook)
    else:
        logging.info("BASE_URL not set; starting polling.")
        await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
