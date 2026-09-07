# Telegram Store Bot

A simple Telegram shop bot with products, UPI QR payment instructions, UTR collection, admin approval, and automatic delivery.

## 1. Create the bot

Open Telegram and use **@BotFather** to create a bot and copy its token.

Get your Telegram numeric user ID and put it in `ADMIN_ID`.

## 2. Configure

Set these environment variables on Render:

- `BOT_TOKEN` — BotFather token
- `ADMIN_ID` — your Telegram numeric ID
- `UPI_ID` — your UPI ID
- `STORE_NAME` — store name
- `WEBHOOK_SECRET` — random secret
- `BASE_URL` — your Render HTTPS URL, for example `https://telegram-store-bot.onrender.com`

Put your QR image at:

`static/qr.png`

## 3. Products

For the first version, edit the sample product inside `bot.py`, then redeploy.

For a production version, add an admin product-management panel/database commands.

## 4. Deploy to Render

1. Create a GitHub repository.
2. Upload all files from this folder.
3. In Render, create a **Web Service** from the repository.
4. Render will use `render.yaml`, or set:
   - Build command: `pip install -r requirements.txt`
   - Start command: `python bot.py`
5. Add the environment variables.
6. Deploy.

## Important: database persistence

This starter uses SQLite. Render's normal filesystem is not a permanent database across redeploys/restarts. For a real store, use a managed PostgreSQL database (or another persistent database) before relying on it for important orders.

## Payment verification

This bot does NOT pretend to verify UPI payments automatically. It collects the customer's 12-digit UTR and sends it to the admin. The admin approves/rejects the order. Automatic verification requires a supported payment gateway/API and webhook.

## Safety

Never put your BotFather token or other secrets directly into GitHub. Use Render environment variables.
