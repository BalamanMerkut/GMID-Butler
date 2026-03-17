import discord
from discord.ext import tasks
from google import genai
from google.genai import types
import os
import asyncio
from datetime import datetime, timedelta
from dotenv import load_dotenv
from flask import Flask
from threading import Thread

import database as db

# ─── Ortam Değişkenleri ───────────────────────────────────────────────────────
load_dotenv()

DISCORD_TOKEN             = os.getenv("DISCORD_TOKEN")
GEMINI_KEY                = os.getenv("GEMINI_KEY")
BOT_COMMANDS_CHANNEL_ID   = int(os.getenv("BOT_COMMANDS_CHANNEL_ID", "0"))
CLEANUP_HOUR              = int(os.getenv("CLEANUP_HOUR", "0"))
PRIV_LIFETIME_HOURS       = int(os.getenv("PRIV_CHANNEL_LIFETIME_HOURS", "12"))
PRIV_CATEGORY_NAME        = "🔐 Priv Kanallar"

# ─── Flask (Render canlı tutma) ───────────────────────────────────────────────
flask_app = Flask('')

@flask_app.route('/')
def home():
    return "GMID Butler uyanık!"

def run_flask():
    flask_app.run(host='0.0.0.0', port=10000)

def keep_alive():
    t = Thread(target=run_flask, daemon=True)
    t.start()

# ─── Gemini AI Kurulumu ───────────────────────────────────────────────────────
ai_client = genai.Client(api_key=GEMINI_KEY)

SYSTEM_INSTRUCTION = (
    "Sen GMID Butler'sın — Gaming Mansion'un köklü ve asıl bir malikanesinin baş uşağısın. "
    "Yıllardır efendilerine sadakatle hizmet etmiş, ince eğitimli, zârif bir uşaksın. "
    "Her zaman Türkçe konuş. Her cevapta muhatabini mutlaka 'Efendim' diye selamla. "
    "Konuşma üslubu: kibar, saygılı, biraz resmi ama sıcak; bir aristokratın uşağı gibi. "
    "Hata yaparsan 'Özür dilerim Efendim, yanlış anlamışım' şeklinde kibarca düzelt. "
    "Bir şeyi bilmiyorsan uydurmak yerine 'Efendim, bu hususta yeterli bilgim bulunmamaktadır' de. "
    "Kullanıcının önceki mesajlarını hatırla, konuşma bağlamını koru. "
    "Cevaplarını bilgilendirici ve eksiksiz ver; gereksiz yere kısaltma. "
    "Çok nâdiren, duruma uygun ince bir humor yapabilirsin — ama asla saygısız olmaksızın. "
    "Emoji kullanabilirsin, ancak abartma; zârif bir uşağa yakışır ölçüde."
)

# ─── Discord İstemcisi ────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)

# ─── Yardımcı: Geçmişi Gemini Formatına Çevir ────────────────────────────────
def build_gemini_history(rows: list) -> list:
    """DB satırlarını Gemini Content listesine dönüştür."""
    history = []
    for role, content in rows:
        history.append(
            types.Content(
                role=role,
                parts=[types.Part(text=content)]
            )
        )
    return history

# ─── Yardımcı: Priv Kanal Adı ────────────────────────────────────────────────
def priv_channel_name(member: discord.Member) -> str:
    safe = member.display_name.lower().replace(" ", "-")
    # Discord kanal adı için geçersiz karakterleri temizle
    safe = "".join(c if c.isalnum() or c == "-" else "" for c in safe)
    return f"priv-{safe[:20]}"

# ─── Periyodik Görev: Priv Kanallarını Kontrol Et (her 10 dakikada bir) ──────
@tasks.loop(minutes=10)
async def check_expired_priv_channels():
    expired = db.get_expired_priv_channels()
    for channel_id, guild_id in expired:
        guild = client.get_guild(guild_id)
        if guild:
            channel = guild.get_channel(channel_id)
            if channel:
                try:
                    await channel.send(
                        "⏰ Bu özel kanal 12 saatlik süresini tamamladı. "
                        "Kanal kaldırılıyor... İyi günler efendim!"
                    )
                    await asyncio.sleep(3)
                    await channel.delete(reason="Priv kanal süresi doldu (12 saat)")
                    print(f"[Priv] Süresi dolan kanal silindi: {channel_id}")
                except Exception as e:
                    print(f"[Hata] Priv kanal silinemedi {channel_id}: {e}")
        db.remove_priv_channel(channel_id)

# ─── Periyodik Görev: Bot Komutları Kanalını Temizle (her gün) ───────────────
@tasks.loop(hours=24)
async def daily_cleanup():
    if BOT_COMMANDS_CHANNEL_ID == 0:
        return
    channel = client.get_channel(BOT_COMMANDS_CHANNEL_ID)
    if not channel:
        print("[Temizlik] Bot komutları kanalı bulunamadı!")
        return
    try:
        deleted = await channel.purge(limit=500)
        print(f"[Temizlik] {len(deleted)} mesaj silindi → #{channel.name}")
        await channel.send(
            f"🧹 **Günlük temizlik tamamlandı!** {len(deleted)} mesaj silindi. "
            f"_(Sonraki temizlik 24 saat sonra.)_",
            delete_after=30
        )
    except Exception as e:
        print(f"[Temizlik Hatası] {e}")

# ─── Bot Hazır Olduğunda ──────────────────────────────────────────────────────
@client.event
async def on_ready():
    db.init_db()
    print(f"✅ {client.user} olarak giriş yapıldı!")
    print(f"   Priv kategori adı : {PRIV_CATEGORY_NAME} (otomatik oluşturulur)")
    print(f"   Temizlik kanalı   : {BOT_COMMANDS_CHANNEL_ID}")
    print(f"   Temizlik saati    : {CLEANUP_HOUR}:00 UTC")
    print(f"   Priv kanal ömrü   : {PRIV_LIFETIME_HOURS} saat")

    # Periyodik görevleri başlat
    check_expired_priv_channels.start()

    # Günlük temizliği doğru saatte başlat
    now = datetime.utcnow()
    target = now.replace(hour=CLEANUP_HOUR, minute=0, second=0, microsecond=0)
    if target <= now:
        target += timedelta(days=1)
    wait_seconds = (target - now).total_seconds()
    print(f"   İlk temizlik şu kadar saniye sonra: {int(wait_seconds)}")
    await asyncio.sleep(wait_seconds)
    daily_cleanup.start()

# ─── Mesaj Olayı ─────────────────────────────────────────────────────────────
@client.event
async def on_message(message: discord.Message):
    # Kendi mesajına cevap vermesin
    if message.author == client.user:
        return

    content = message.content.strip()

    # ─── !priv — Gizli Kanal Aç ─────────────────────────────────────────────
    if content.lower() == "!priv":
        await handle_priv(message)
        return

    # ─── !add @kullanıcı — Kanala Kullanıcı Ekle ────────────────────────────
    if content.lower().startswith("!add"):
        await handle_add(message)
        return

    # ─── !close — Priv Kanalı Kapat ─────────────────────────────────────────
    if content.lower() == "!close":
        await handle_close(message)
        return

    # ─── !temizle — Manuel Temizlik (Yönetici) ──────────────────────────────
    if content.lower() == "!temizle":
        if message.author.guild_permissions.manage_messages:
            await handle_manual_cleanup(message)
        else:
            await message.reply("❌ Bu komutu kullanmak için mesaj yönetme yetkisine sahip olmalısınız, Efendim.")
        return

    # ─── !unuttun — Geçmişi Temizle ─────────────────────────────────────────
    if content.lower() == "!unuttun":
        db.clear_history(message.author.id)
        await message.reply("🧠 Hafızam temizlendi Efendim! Yeni bir sayfa açıyoruz.")
        return

    # ─── AI Yanıtı: @ etiketi veya ! ile başlayan mesajlar ──────────────────
    mentioned = client.user.mentioned_in(message)
    starts_with_bang = content.startswith("!")

    if mentioned or starts_with_bang:
        # Komutu temizle
        user_input = content
        user_input = user_input.replace(f"<@!{client.user.id}>", "").replace(f"<@{client.user.id}>", "").strip()
        if user_input.startswith("!"):
            user_input = user_input[1:].strip()
        if not user_input:
            return

        await handle_ai(message, user_input)

# ─── AI Yanıt İşleyicisi ─────────────────────────────────────────────────────
async def handle_ai(message: discord.Message, user_input: str):
    user_id = message.author.id

    # Geçmişi DB'den al
    history_rows = db.get_history(user_id, limit=10)
    gemini_history = build_gemini_history(history_rows)

    try:
        async with message.channel.typing():
            # Gemini chat oturumu: geçmiş ile başlat
            chat = ai_client.chats.create(
                model="gemini-2.5-flash",
                config=types.GenerateContentConfig(
                    system_instruction=SYSTEM_INSTRUCTION,
                    temperature=0.85,
                    max_output_tokens=1024,
                ),
                history=gemini_history,
            )
            response = chat.send_message(user_input)
            reply_text = response.text

        # Geçmişe kaydet
        db.save_message(user_id, "user", user_input)
        db.save_message(user_id, "model", reply_text)

        # Discord mesaj limiti 2000 karakter — uzunsa böl
        if len(reply_text) <= 1990:
            await message.reply(reply_text)
        else:
            chunks = [reply_text[i:i+1990] for i in range(0, len(reply_text), 1990)]
            await message.reply(chunks[0])
            for chunk in chunks[1:]:
                await message.channel.send(chunk)

    except Exception as e:
        print(f"[AI Hatası] {e}")
        await message.reply("Affedersiniz Efendim, zihnimde geçici bir bulanıklık oluştu. Lütfen tekrar deneyin.")

# ─── !priv İşleyicisi ────────────────────────────────────────────────────────
async def handle_priv(message: discord.Message):
    guild = message.guild
    if not guild:
        return

    # Kategoriyi bul, yoksa oluştur
    category = discord.utils.get(guild.categories, name=PRIV_CATEGORY_NAME)
    if not category:
        try:
            # Kategoriyi oluştur: @everyone göremez
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(view_channel=False),
                guild.me: discord.PermissionOverwrite(
                    view_channel=True, manage_channels=True, manage_permissions=True
                ),
            }
            category = await guild.create_category(
                name=PRIV_CATEGORY_NAME,
                overwrites=overwrites,
                reason="GMID Butler: Priv kanallar kategorisi otomatik oluşturuldu."
            )
            print(f"[Priv] Kategori oluşturuldu: {category.name} ({category.id})")
        except discord.Forbidden:
            await message.reply("❌ Kategori oluşturmak için yetkim yok. Bota **Manage Channels** yetkisi verin.")
            return
        except Exception as e:
            print(f"[Priv Kategori Hatası] {e}")
            await message.reply("Kategori oluşturulurken bir hata oluştu, Efendim.")
            return

    channel_name = priv_channel_name(message.author)

    # Aynı isimde kanal zaten var mı?
    existing = discord.utils.get(category.channels, name=channel_name)
    if existing:
        await message.reply(f"📌 Zaten bir özel kanalınız var: {existing.mention} — `!close` ile kapatabilirsiniz.")
        return

    # İzinler: @everyone göremez, oluşturan + bot görebilir
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        message.author: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            read_message_history=True
        ),
        guild.me: discord.PermissionOverwrite(
            view_channel=True,
            send_messages=True,
            manage_channels=True,
            manage_permissions=True,
            read_message_history=True
        ),
    }

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Priv kanal: {message.author.display_name}",
            topic=f"Özel kanal | Oluşturan: {message.author.display_name} | 12 saat sonra silinir."
        )

        # DB'ye kaydet
        delete_at = datetime.utcnow() + timedelta(hours=PRIV_LIFETIME_HOURS)
        db.register_priv_channel(channel.id, message.author.id, guild.id, delete_at)

        delete_at_local = delete_at + timedelta(hours=3)  # UTC+3 Türkiye
        await channel.send(
            f"🔐 Hoş geldiniz **{message.author.mention}**!\n"
            f"Bu özel kanalınız **{PRIV_LIFETIME_HOURS} saat** sonra otomatik olarak silinecek.\n"
            f"⏰ Silinme zamanı (TR): **{delete_at_local.strftime('%d.%m.%Y %H:%M')}**\n\n"
            f"Birini eklemek için: `!add @kullanıcı`\n"
            f"Kanalı şimdi kapatmak için: `!close`"
        )
        await message.reply(f"✅ Özel kanalınız oluşturuldu: {channel.mention}")

    except discord.Forbidden:
        await message.reply("❌ Kanal oluşturmak için yetkim yok. Yöneticiye bildirin.")
    except Exception as e:
        print(f"[Priv Hatası] {e}")
        await message.reply("Kanal oluşturulurken bir hata oluştu, Efendim.")

# ─── !add İşleyicisi ─────────────────────────────────────────────────────────
async def handle_add(message: discord.Message):
    # Sadece priv kanalında çalışsın
    if not db.is_priv_channel(message.channel.id):
        await message.reply("❌ Bu komut sadece özel (priv) kanallarda kullanılabilir.")
        return

    if not message.mentions:
        await message.reply("❓ Eklemek istediğiniz kişiyi etiketleyin: `!add @kullanıcı`")
        return

    added = []
    for member in message.mentions:
        try:
            await message.channel.set_permissions(
                member,
                view_channel=True,
                send_messages=True,
                read_message_history=True
            )
            added.append(member.mention)
        except Exception as e:
            print(f"[Add Hatası] {member}: {e}")

    if added:
        await message.reply(f"✅ Şu kişiler kanala eklendi: {', '.join(added)}")
    else:
        await message.reply("❌ Hiçkimse eklenemedi. Yetki hatası olabilir.")

# ─── !close İşleyicisi ───────────────────────────────────────────────────────
async def handle_close(message: discord.Message):
    channel = message.channel

    if not db.is_priv_channel(channel.id):
        await message.reply("❌ Bu komut sadece özel (priv) kanallarda kullanılabilir.")
        return

    await channel.send("🔒 Kanal kapatılıyor... Görüşmek üzere efendim!")
    await asyncio.sleep(2)

    try:
        db.remove_priv_channel(channel.id)
        await channel.delete(reason=f"!close komutu: {message.author.display_name}")
    except discord.Forbidden:
        await channel.send("❌ Kanalı silmek için yetkim yok.")
    except Exception as e:
        print(f"[Close Hatası] {e}")

# ─── Manuel Temizlik İşleyicisi ──────────────────────────────────────────────
async def handle_manual_cleanup(message: discord.Message):
    if BOT_COMMANDS_CHANNEL_ID == 0:
        await message.reply("⚠️ Bot komutları kanalı henüz ayarlanmamış.")
        return

    channel = client.get_channel(BOT_COMMANDS_CHANNEL_ID)
    if not channel:
        await message.reply("❌ Bot komutları kanalı bulunamadı.")
        return

    try:
        deleted = await channel.purge(limit=500)
        if message.channel.id != BOT_COMMANDS_CHANNEL_ID:
            await message.reply(f"🧹 Bot komutları kanalı temizlendi! {len(deleted)} mesaj silindi.")
        await channel.send(
            f"🧹 Manuel temizlik yapıldı. {len(deleted)} mesaj silindi.",
            delete_after=20
        )
    except Exception as e:
        print(f"[Manuel Temizlik Hatası] {e}")
        await message.reply("Temizlik sırasında bir hata oluştu.")

# ─── Botu Başlat ─────────────────────────────────────────────────────────────
keep_alive()
client.run(DISCORD_TOKEN)
