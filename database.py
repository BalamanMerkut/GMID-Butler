import sqlite3
import os
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "conversations.db")

def init_db():
    """Veritabanını başlat ve tabloları oluştur."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Konuşma geçmişi tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS conversation_history (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id TEXT NOT NULL,
            role TEXT NOT NULL,       -- 'user' veya 'model'
            content TEXT NOT NULL,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Geçici (priv) kanallar tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS priv_channels (
            channel_id INTEGER PRIMARY KEY,
            creator_id TEXT NOT NULL,
            guild_id INTEGER NOT NULL,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
            delete_at DATETIME NOT NULL
        )
    ''')

    # Kanal temizlik ayarları tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS cleanup_settings (
            channel_id INTEGER PRIMARY KEY,
            guild_id INTEGER NOT NULL,
            cleanup_hour INTEGER NOT NULL -- 0-23
        )
    ''')
    
    # Sunucu ayarları tablosu
    c.execute('''
        CREATE TABLE IF NOT EXISTS guild_settings (
            guild_id INTEGER PRIMARY KEY,
            language TEXT NOT NULL DEFAULT 'en'
        )
    ''')
    
    conn.commit()
    conn.close()

def save_message(user_id: str, role: str, content: str):
    """Kullanıcının mesajını kaydet. Kullanıcı başına son 20 mesajı tut."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO conversation_history (user_id, role, content) VALUES (?, ?, ?)",
        (str(user_id), role, content)
    )
    # En eski mesajları temizle - kullanıcı başına max 20 kayıt
    c.execute('''
        DELETE FROM conversation_history 
        WHERE user_id = ? AND id NOT IN (
            SELECT id FROM conversation_history 
            WHERE user_id = ? 
            ORDER BY id DESC LIMIT 20
        )
    ''', (str(user_id), str(user_id)))
    conn.commit()
    conn.close()

def get_history(user_id: str, limit: int = 10) -> list:
    """Kullanıcının son N konuşmasını döndür."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        SELECT role, content FROM conversation_history
        WHERE user_id = ?
        ORDER BY id DESC LIMIT ?
    ''', (str(user_id), limit))
    rows = c.fetchall()
    conn.close()
    # Eski → yeni sıraya çevir
    return list(reversed(rows))

def clear_history(user_id: str):
    """Kullanıcının tüm konuşma geçmişini temizle."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM conversation_history WHERE user_id = ?", (str(user_id),))
    conn.commit()
    conn.close()

# ─── Priv Kanal Fonksiyonları ───────────────────────────────────────────────

def register_priv_channel(channel_id: int, creator_id: str, guild_id: int, delete_at: datetime):
    """Yeni priv kanalını veritabanına kaydet."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO priv_channels (channel_id, creator_id, guild_id, delete_at) VALUES (?, ?, ?, ?)",
        (channel_id, str(creator_id), guild_id, delete_at.isoformat())
    )
    conn.commit()
    conn.close()

def remove_priv_channel(channel_id: int):
    """Priv kanalını veritabanından sil."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM priv_channels WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()

def get_expired_priv_channels() -> list:
    """Süresi dolmuş priv kanallarını döndür."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    now = datetime.utcnow().isoformat()
    c.execute(
        "SELECT channel_id, guild_id FROM priv_channels WHERE delete_at <= ?",
        (now,)
    )
    rows = c.fetchall()
    conn.close()
    return rows

def is_priv_channel(channel_id: int) -> bool:
    """Verilen kanal ID'si bir priv kanalı mı?"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT 1 FROM priv_channels WHERE channel_id = ?", (channel_id,))
    result = c.fetchone()
    conn.close()
    return result is not None

def get_priv_channel_owner(channel_id: int) -> str | None:
    """Priv kanalının sahibinin (creator) user ID'sini döndür. Kanal bulunamazsa None."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT creator_id FROM priv_channels WHERE channel_id = ?", (channel_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else None

# ─── Temizlik Ayarları Fonksiyonları ────────────────────────────────────────

def set_cleanup(channel_id: int, guild_id: int, hour: int):
    """Kanal için temizlik saatini ayarla."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO cleanup_settings (channel_id, guild_id, cleanup_hour) VALUES (?, ?, ?)",
        (channel_id, guild_id, hour)
    )
    conn.commit()
    conn.close()

def get_cleanup_settings() -> list:
    """Tüm temizlik ayarlarını döndür."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT channel_id, guild_id, cleanup_hour FROM cleanup_settings")
    rows = c.fetchall()
    conn.close()
    return rows

def remove_cleanup(channel_id: int):
    """Kanal temizlik ayarını sil."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM cleanup_settings WHERE channel_id = ?", (channel_id,))
    conn.commit()
    conn.close()

# ─── Sunucu Ayarları Fonksiyonları ──────────────────────────────────────────

def set_language(guild_id: int, lang: str):
    """Sunucu için dil ayarını yap."""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT OR REPLACE INTO guild_settings (guild_id, language) VALUES (?, ?)",
        (guild_id, lang.lower())
    )
    conn.commit()
    conn.close()

def get_language(guild_id: int) -> str:
    """Sunucunun dil ayarını döndür. Varsayılan 'en'."""
    if not guild_id:
        return 'en'
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT language FROM guild_settings WHERE guild_id = ?", (guild_id,))
    result = c.fetchone()
    conn.close()
    return result[0] if result else 'en'
