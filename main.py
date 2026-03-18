import discord
from discord.ext import tasks
from google import genai
from google.genai import types
from discord import app_commands
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

# ─── Çeviri Sistemi (Internationalization) ──────────────────────────────────
STRINGS = {
    "en": {
        "priv_closed": "🔒 Channel is closing... Goodbye Sir!",
        "priv_welcome": "🔐 Welcome {mention}!\nThis private channel will be automatically deleted in **{hours} hours**.\n⏰ Deletion time (TR): **{time}**\n\nTo add someone: `!add @user`\nTo close now: `!close`",
        "cleanup_done": "🧹 **Daily cleanup completed!** {count} messages removed. _(Next cleanup in 24 hours.)_",
        "set_success": "✅ Sir, this channel (**#{name}**) is now set to be cleared every day at **{hour}:00 UTC**.",
        "set_removed": "✅ Sir, automatic clearing has been removed for **#{name}**.",
        "lang_success": "✅ Language set to **English**, Sir.",
        "lang_error": "❌ Unsupported language, Sir. Use `en`, `tr`, or `es`.",
        "no_perms": "❌ You must have manage permissions to use this command, Sir.",
        "hour_error": "❌ Hour must be between 0 and 23, Sir.",
        "priv_exists": "📌 You already have a private channel: {mention} — close it with `!close` first.",
        "priv_created": "✅ Sir, your private channel has been created: {mention}",
        "add_usage": "❓ Usage:\n`!add @user` — add via mention\n`!add username` — search and add by name",
        "user_not_found": "❌ User `{name}` not found, Sir.",
        "multiple_found": "⚠️ Multiple matches found: {names}\nPlease be more specific or use `!add @mention`.",
        "add_success": "✅ The following users have been added: {names}",
        "add_fail": "❌ No one could be added. Possible permission issue.",
        "close_owner": "⛔ Only the creator can close this channel, Sir.",
        "forget_success": "🧠 My memory has been cleared, Sir! We are opening a new page.",
        "ai_error": "Forgive me Sir, my mind is momentarily clouded. Please try again.",
        "control_none": "📜 No channels are currently set for automatic cleanup, Sir.",
        "control_list": "📜 **Active Cleanup Schedules:**\n{lines}",
        "manual_cleanup_done": "🧹 Bot commands channel has been cleared! {count} messages removed.",
        "priv_expired": "⏰ This private channel has completed its {hours}-hour duration. It is being removed... Have a nice day Sir!",
        "help_title": "📜 GMID Butler — Command List",
        "help_desc": "Sir, all the commands at your service are listed below.",
        "help_ai_title": "🤖 Artificial Intelligence",
        "help_ai_val": "`!<question>` or `@GMID Butler <question>` → Ask Butler a question\n`!forget` → Clear conversation history",
        "help_priv_title": "🔐 Private Channel",
        "help_priv_val": "`!priv [hours]` → Open a private, secret channel ({hours}h)\n`!add @user` → Add someone to your channel\n`!close` → Close your channel now",
        "help_clean_title": "🧹 Cleanup & Settings",
        "help_clean_val": "`!clear` → Manually clean this channel *(Manager)*\n`!set clear [hour]` → Schedule daily cleanup (0-23 UTC)\n`!set remove` → Remove cleanup from this channel\n`!set control` → List all active cleanup schedules\n`!language [en/tr/es]` → Change bot language for this server",
        "help_footer": "GMID Butler • Always at your service, Sir 🎩"
    },
    "tr": {
        "priv_closed": "🔒 Kanal kapatılıyor... Görüşmek üzere efendim!",
        "priv_welcome": "🔐 Hoş geldiniz {mention}!\nBu özel kanalınız **{hours} saat** sonra otomatik olarak silinecek.\n⏰ Silinme zamanı (TR): **{time}**\n\nBirini eklemek için: `!add @kullanıcı`\nKanalı şimdi kapatmak için: `!close`",
        "cleanup_done": "🧹 **Günlük temizlik tamamlandı!** {count} mesaj silindi. _(Sonraki temizlik 24 saat sonra.)_",
        "set_success": "✅ Efendim, bu kanal (**#{name}**) artık her gün saat **{hour}:00 UTC**'de temizlenecek.",
        "set_removed": "✅ Efendim, **#{name}** kanalı için otomatik temizlik kaldırıldı.",
        "lang_success": "✅ Dil **Türkçe** olarak ayarlandı, Efendim.",
        "lang_error": "❌ Desteklenmeyen dil, Efendim. Şunları kullanabilirsiniz: `en`, `tr`, `es`.",
        "no_perms": "❌ Bu komutu kullanmak için yetkiniz yok, Efendim.",
        "hour_error": "❌ Saat 0 ile 23 arasında olmalıdır, Efendim.",
        "priv_exists": "📌 Zaten bir özel kanalınız var: {mention} — `!close` ile kapatabilirsiniz.",
        "priv_created": "✅ Özel kanalınız oluşturuldu: {mention}",
        "add_usage": "❓ Kullanım:\n`!add @kullanıcı` — mention ile ekle\n`!add kullanıcıadı` — isim ile ara ve ekle",
        "user_not_found": "❌ `{name}` adında bir üye bulunamadı, Efendim.",
        "multiple_found": "⚠️ Birden fazla eşleşme bulundu: {names}\nLütfen daha spesifik bir isim ya da `!add @mention` kullanın.",
        "add_success": "✅ Şu kişiler kanala eklendi: {names}",
        "add_fail": "❌ Hiçkimse eklenemedi. Yetki hatası olabilir.",
        "close_owner": "⛔ Bu kanalı yalnızca kanalı oluşturan kişi kapatabilir, Efendim.",
        "forget_success": "🧠 Hafızam temizlendi Efendim! Yeni bir sayfa açıyoruz.",
        "ai_error": "Affedersiniz Efendim, zihnimde geçici bir bulanıklık oluştu. Lütfen tekrar deneyin.",
        "control_none": "📜 Henüz otomatik temizlik için ayarlanmış bir kanal yok, Efendim.",
        "control_list": "📜 **Aktif Temizlik Planları:**\n{lines}",
        "manual_cleanup_done": "🧹 Bot komutları kanalı temizlendi! {count} mesaj silindi.",
        "priv_expired": "⏰ Bu özel kanal {hours} saatlik süresini tamamladı. Kanal kaldırılıyor... İyi günler efendim!",
        "help_title": "📜 GMID Butler — Komut Listesi",
        "help_desc": "Efendim, hizmetinizdeki tüm komutlar aşağıda listelenmiştir.",
        "help_ai_title": "🤖 Yapay Zeka",
        "help_ai_val": "`!<soru>` veya `@GMID Butler <soru>` → Butler'a soru sor\n`!forget` → Konuşma geçmişini temizle",
        "help_priv_title": "🔐 Özel Kanal",
        "help_priv_val": "`!priv [saat]` → Sana özel kanal aç ({hours} saat)\n`!add @kullanıcı` → Kanalına birini ekle\n`!close` → Kanalı kapat",
        "help_clean_title": "🧹 Temizlik ve Ayarlar",
        "help_clean_val": "`!clear` → Bu kanalı manuel temizle *(Yönetici)*\n`!set clear [saat]` → Günlük temizlik ayarla (0-23 UTC)\n`!set remove` → Temizlik ayarını kaldır\n`!set control` → Aktif temizlikleri listele\n`!language [en/tr/es]` → Bot dilini değiştir",
        "help_footer": "GMID Butler • Her zaman hizmetinizdeyim, Efendim 🎩"
    },
    "es": {
        "priv_closed": "🔒 El canal se está cerrando... ¡Adiós Señor!",
        "priv_welcome": "🔐 ¡Bienvenido {mention}!\nEste canal privado se eliminará automáticamente en **{hours} horas**.\n⏰ Hora de eliminación: **{time}**\n\nPara añadir a alguien: `!add @usuario`\nPara cerrar ahora: `!close`",
        "cleanup_done": "🧹 **¡Limpieza diaria completada!** {count} mensajes eliminados. _(Próxima limpieza en 24 horas.)_",
        "set_success": "✅ Señor, este canal (**#{name}**) ahora está configurado para limpiarse todos los días a las **{hour}:00 UTC**.",
        "set_removed": "✅ Señor, se ha eliminado la limpieza automática para **#{name}**.",
        "lang_success": "✅ Idioma configurado en **Español**, Señor.",
        "lang_error": "❌ Idioma no compatible, Señor. Use `en`, `tr` o `es`.",
        "no_perms": "❌ Debe tener permisos de gestión para usar este comando, Señor.",
        "hour_error": "❌ La hora debe estar entre 0-23, Señor.",
        "priv_exists": "📌 Ya tienes un canal privado: {mention} — ciérralo con `!close` primero.",
        "priv_created": "✅ Señor, se ha creado su canal privado: {mention}",
        "add_usage": "❓ Uso:\n`!add @usuario` — añadir mediante mención\n`!add nombre` — buscar y añadir por nombre",
        "user_not_found": "❌ Usuario `{name}` no encontrado, Señor.",
        "multiple_found": "⚠️ Se han encontrado múltiples coincidencias: {names}\nSea más específico o use `!add @mention`.",
        "add_success": "✅ Se han añadido los siguientes usuarios: {names}",
        "add_fail": "❌ No se pudo añadir a nadie. Posible problema de permisos.",
        "close_owner": "⛔ Solo el creador puede cerrar este canal, Señor.",
        "forget_success": "🧠 ¡Mi memoria ha sido borrada, Señor! Estamos abriendo una nueva página.",
        "ai_error": "Perdóneme Señor, mi mente está momentáneamente nublada. Por favor, inténtelo de nuevo.",
        "control_none": "📜 No hay canales configurados para la limpieza automática, Señor.",
        "control_list": "📜 **Horarios de Limpieza Activos:**\n{lines}",
        "manual_cleanup_done": "🧹 ¡El canal de comandos del bot ha sido limpiado! {count} mensajes eliminados.",
        "priv_expired": "⏰ Este canal privado ha completado su duración de {hours} horas. Se está eliminando... ¡Que tenga un buen día Señor!",
        "help_title": "📜 GMID Butler — Lista de Comandos",
        "help_desc": "Señor, todos los comandos a su servicio se enumeran a continuación.",
        "help_ai_title": "🤖 Inteligencia Artificial",
        "help_ai_val": "`!<pregunta>` o `@GMID Butler <pregunta>` → Hacer una pregunta\n`!forget` → Borrar historial",
        "help_priv_title": "🔐 Canal Privado",
        "help_priv_val": "`!priv [horas]` → Abrir un canal privado ({hours}h)\n`!add @usuario` → Añadir a alguien\n`!close` → Cerrar ahora",
        "help_clean_title": "🧹 Limpieza y Ajustes",
        "help_clean_val": "`!clear` → Limpiar manualmente *(Gerente)*\n`!set clear [hora]` → Programar limpieza (0-23 UTC)\n`!set remove` → Eliminar limpieza\n`!set control` → Listar limpiezas activas\n`!language [en/tr/es]` → Cambiar idioma del bot",
        "help_footer": "GMID Butler • Siempre a su servicio, Señor 🎩"
    },
    "it": {
        "priv_closed": "🔒 Il canale si sta chiudendo... Arrivederci signore!",
        "priv_welcome": "🔐 Benvenuto {mention}!\nQuesto canale privato verrà eliminato automaticamente tra **{hours} ore**.\n⏰ Orario di eliminazione: **{time}**\n\nPer aggiungere qualcuno: `!add @utente`\nPer chiudere ora: `!close`",
        "cleanup_done": "🧹 **Pulizia giornaliera completata!** {count} messaggi rimossi. _(Prossima pulizia tra 24 ore.)_",
        "set_success": "✅ Signore, questo canale (**#{name}**) è ora impostato per essere pulito ogni giorno alle **{hour}:00 UTC**.",
        "set_removed": "✅ Signore, la pulizia automatica è stata rimossa per **#{name}**.",
        "lang_success": "✅ Lingua impostata su **Italiano**, Signore.",
        "lang_error": "❌ Lingua non supportata, Signore. Usa `en`, `tr`, `es`, `it`, `zh`, `ru`, `de`, `fr`.",
        "no_perms": "❌ Deve avere i permessi di gestione per usare questo comando, Signore.",
        "hour_error": "❌ L'ora deve essere compresa tra 0-23, Signore.",
        "priv_exists": "📌 Hai già un canale privato: {mention} — chiudilo prima con `!close`.",
        "priv_created": "✅ Signore, il tuo canale privato è stato creato: {mention}",
        "add_usage": "❓ Utilizzo:\n`!add @utente` — aggiungi tramite menzione\n`!add nomeutente` — cerca e aggiungi per nome",
        "user_not_found": "❌ Utente `{name}` non trovato, Signore.",
        "multiple_found": "⚠️ Trovate più corrispondenze: {names}\nSii più specifico o usa `!add @menzione`.",
        "add_success": "✅ I seguenti utenti sono stati aggiunti: {names}",
        "add_fail": "❌ Impossibile aggiungere nessuno. Possibile problema di permessi.",
        "close_owner": "⛔ Solo il creatore può chiudere questo canale, Signore.",
        "forget_success": "🧠 La mia memoria è stata cancellata, signore! Stiamo aprendo una nuova pagina.",
        "ai_error": "Perdonatemi signore, la mia mente è momentaneamente offuscata. Per favore, riprovate.",
        "control_none": "📜 Nessun canale è attualmente impostato per la pulizia automatica, Signore.",
        "control_list": "📜 **Programmi di pulizia attivi:**\n{lines}",
        "manual_cleanup_done": "🧹 Il canale dei comandi del bot è stato pulito! {count} messaggi rimossi.",
        "priv_expired": "⏰ Questo canale privato ha completato la sua durata di {hours} ore. Verrà rimosso... Buona giornata signore!",
        "help_title": "📜 GMID Butler — Elenco Comandi",
        "help_desc": "Signore, tutti i comandi al vostro servizio sono elencati di seguito.",
        "help_ai_title": "🤖 Intelligenza Artificiale",
        "help_ai_val": "`!<domanda>` o `@GMID Butler <domanda>` → Fai una domanda al Butler\n`!forget` → Cancella la cronologia delle conversazioni",
        "help_priv_title": "🔐 Canale Privato",
        "help_priv_val": "`!priv [ore]` → Apri un canale segreto privato per te ({hours} ore)\n`!add @utente` → Aggiungi qualcuno al tuo canale\n`!close` → Chiudi il tuo canale ora",
        "help_clean_title": "🧹 Pulizia e Impostazioni",
        "help_clean_val": "`!clear` → Pulisci manualmente questo canale *(Manager)*\n`!set clear [ora]` → Pianifica la pulizia giornaliera (0-23 UTC)\n`!set remove` → Rimuovi la pulizia da questo canale\n`!set control` → Elenca tutti i programmi di pulizia attivi\n`!language [codice]` → Cambia la lingua del bot per questo server",
        "help_footer": "GMID Butler • Sempre al vostro servizio, Signore 🎩"
    },
    "de": {
        "priv_closed": "🔒 Der Kanal wird geschlossen... Auf Wiedersehen, Sir!",
        "priv_welcome": "🔐 Willkommen {mention}!\nDieser private Kanal wird automatisch in **{hours} Stunden** gelöscht.\n⏰ Löschzeitpunkt: **{time}**\n\nUm jemanden hinzuzufügen: `!add @nutzer`\nUm jetzt zu schließen: `!close`",
        "cleanup_done": "🧹 **Tägliche Reinigung abgeschlossen!** {count} Nachrichten entfernt. _(Nächste Reinigung in 24 Stunden.)_",
        "set_success": "✅ Sir, dieser Kanal (**#{name}**) ist nun so eingestellt, dass er jeden Tag um **{hour}:00 UTC** gereinigt wird.",
        "set_removed": "✅ Sir, die automatische Reinigung wurde für **#{name}** entfernt.",
        "lang_success": "✅ Sprache auf **Deutsch** eingestellt, Sir.",
        "lang_error": "❌ Nicht unterstützte Sprache, Sir. Verfügbar: `en`, `tr`, `es`, `it`, `zh`, `ru`, `de`, `fr`.",
        "no_perms": "❌ Sie müssen über Verwaltungsberechtigungen verfügen, um diesen Befehl zu verwenden, Sir.",
        "hour_error": "❌ Die Stunde muss zwischen 0-23 liegen, Sir.",
        "priv_exists": "📌 Sie haben bereits einen privaten Kanal: {mention} — schließen Sie ihn zuerst mit `!close`.",
        "priv_created": "✅ Sir, Ihr privater Kanal wurde erstellt: {mention}",
        "add_usage": "❓ Verwendung:\n`!add @nutzer` — per Erwähnung hinzufügen\n`!add nutzername` — nach Namen suchen und hinzufügen",
        "user_not_found": "❌ Nutzer `{name}` nicht gefunden, Sir.",
        "multiple_found": "⚠️ Mehrere Treffer gefunden: {names}\nBitte seien Sie genauer oder verwenden Sie `!add @mention`.",
        "add_success": "✅ Die folgenden Nutzer wurden hinzugefügt: {names}",
        "add_fail": "❌ Niemand konnte hinzugefügt werden. Möglicherweise ein Berechtigungsproblem.",
        "close_owner": "⛔ Nur der Ersteller kann diesen Kanal schließen, Sir.",
        "forget_success": "🧠 Mein Gedächtnis wurde gelöscht, Sir! Wir schlagen ein neues Kapitel auf.",
        "ai_error": "Verzeihen Sie mir Sir, mein Verstand ist momentan etwas getrübt. Bitte versuchen Sie es erneut.",
        "control_none": "📜 Derzeit sind keine Kanäle für die automatische Reinigung eingestellt, Sir.",
        "control_list": "📜 **Aktive Reinigungspläne:**\n{lines}",
        "manual_cleanup_done": "🧹 Der Bot-Befehlskanal wurde gereinigt! {count} Nachrichten entfernt.",
        "priv_expired": "⏰ Dieser private Kanal hat seine Dauer von {hours} Stunden beendet. Er wird entfernt... Einen schönen Tag noch, Sir!",
        "help_title": "📜 GMID Butler — Befehlsliste",
        "help_desc": "Sir, alle Befehle zu Ihren Diensten sind unten aufgeführt.",
        "help_ai_title": "🤖 Künstliche Intelligenz",
        "help_ai_val": "`!<frage>` oder `@GMID Butler <frage>` → Fragen Sie Butler eine Frage\n`!forget` → Konversationsverlauf löschen",
        "help_priv_title": "🔐 Privater Kanal",
        "help_priv_val": "`!priv [stunden]` → Öffnen Sie einen privaten, geheimen Kanal für sich ({hours}h)\n`!add @nutzer` → Jemanden zu Ihrem Kanal hinzufügen\n`!close` → Schließen Sie Ihren Kanal jetzt",
        "help_clean_title": "🧹 Reinigung & Einstellungen",
        "help_clean_val": "`!clear` → Diesen Kanal manuell reinigen *(Manager)*\n`!set clear [stunde]` → Tägliche Reinigung planen (0-23 UTC)\n`!set remove` → Reinigung von diesem Kanal entfernen\n`!set control` → Alle aktiven Reinigungspläne auflisten\n`!language [code]` → Bot-Sprache für diesen Server ändern",
        "help_footer": "GMID Butler • Stets zu Ihren Diensten, Sir 🎩"
    },
    "fr": {
        "priv_closed": "🔒 Le salon se ferme... Au revoir Monsieur !",
        "priv_welcome": "🔐 Bienvenue {mention}!\nCe salon privé sera automatiquement supprimé dans **{hours} heures**.\n⏰ Heure de suppression : **{time}**\n\nPour ajouter quelqu'un : `!add @utilisateur`\nPour fermer maintenant : `!close`",
        "cleanup_done": "🧹 **Nettoyage quotidien terminé !** {count} messages supprimés. _(Prochain nettoyage dans 24 heures.)_",
        "set_success": "✅ Monsieur, ce salon (**#{name}**) est désormais configuré pour être nettoyé chaque jour à **{hour}:00 UTC**.",
        "set_removed": "✅ Monsieur, le nettoyage automatique a été supprimé pour **#{name}**.",
        "lang_success": "✅ Langue configurée sur le **Français**, Monsieur.",
        "lang_error": "❌ Langue non supportée, Monsieur. Utilisez `en`, `tr`, `es`, `it`, `zh`, `ru`, `de`, `fr`.",
        "no_perms": "❌ Vous devez avoir les permissions de gestion pour utiliser cette commande, Monsieur.",
        "hour_error": "❌ L'heure doit être comprise entre 0-23, Monsieur.",
        "priv_exists": "📌 Vous avez déjà un salon privé : {mention} — fermez-le d'abord avec `!close`.",
        "priv_created": "✅ Monsieur, votre salon privé a été créé : {mention}",
        "add_usage": "❓ Utilisation :\n`!add @utilisateur` — ajouter via mention\n`!add nomutilisateur` — rechercher et ajouter par nom",
        "user_not_found": "❌ Utilisateur `{name}` non trouvé, Monsieur.",
        "multiple_found": "⚠️ Plusieurs correspondances trouvées : {names}\nVeuillez être plus précis ou utiliser `!add @mention`.",
        "add_success": "✅ Les utilisateurs suivants ont été ajoutés : {names}",
        "add_fail": "❌ Personne n'a pu être ajouté. Problème de permissions probable.",
        "close_owner": "⛔ Seul le créateur peut fermer ce salon, Monsieur.",
        "forget_success": "🧠 Ma mémoire a été effacée, Monsieur ! Nous ouvrons une nouvelle page.",
        "ai_error": "Pardonnez-moi Monsieur, mon esprit est momentanément embrumé. Veuillez réessayer.",
        "control_none": "📜 Aucun salon n'est actuellement configuré pour le nettoyage automatique, Monsieur.",
        "control_list": "📜 **Plannings de nettoyage actifs :**\n{lines}",
        "manual_cleanup_done": "🧹 Le salon des commandes du bot a été nettoyé ! {count} messages supprimés.",
        "priv_expired": "⏰ Ce salon privé a terminé sa durée de {hours} heures. Il est en cours de suppression... Bonne journée Monsieur !",
        "help_title": "📜 GMID Butler — Liste des commandes",
        "help_desc": "Monsieur, toutes les commandes à votre service sont listées ci-dessous.",
        "help_ai_title": "🤖 Intelligence Artificielle",
        "help_ai_val": "`!<question>` ou `@GMID Butler <question>` → Poser une question au Butler\n`!forget` → Effacer l'historique des conversations",
        "help_priv_title": "🔐 Salon Privé",
        "help_priv_val": "`!priv [heures]` → Ouvrir un salon secret privé pour vous ({hours}h)\n`!add @utilisateur` → Ajouter quelqu'un à votre salon\n`!close` → Fermer votre salon maintenant",
        "help_clean_title": "🧹 Nettoyage & Paramètres",
        "help_clean_val": "`!clear` → Nettoyer manuellement ce salon *(Manager)*\n`!set clear [heure]` → Planifier un nettoyage quotidien (0-23 UTC)\n`!set remove` → Supprimer le nettoyage de ce salon\n`!set control` → Lister tous les plannings de nettoyage actifs\n`!language [code]` → Changer la langue du bot pour ce serveur",
        "help_footer": "GMID Butler • Toujours à votre service, Monsieur 🎩"
    },
    "ru": {
        "priv_closed": "🔒 Канал закрывается... До свидания, Сэр!",
        "priv_welcome": "🔐 Добро пожаловать, {mention}!\nЭтот приватный канал будет автоматически удален через **{hours} ч.**\n⏰ Время удаления: **{time}**\n\nЧтобы добавить кого-то: `!add @пользователь`\nЧтобы закрыть сейчас: `!close`",
        "cleanup_done": "🧹 **Ежедневная очистка завершена!** Удалено {count} сообщений. _(Следующая очистка через 24 часа.)_",
        "set_success": "✅ Сэр, этот канал (**#{name}**) теперь будет очищаться каждый день в **{hour}:00 UTC**.",
        "set_removed": "✅ Сэр, автоматическая очистка для **#{name}** отключена.",
        "lang_success": "✅ Язык установлен на **Русский**, Сэр.",
        "lang_error": "❌ Неподдерживаемый язык, Сэр. Используйте `en`, `tr`, `es`, `it`, `zh`, `ru`, `de`, `fr`.",
        "no_perms": "❌ У вас должны быть права на управление сервером, Сэр.",
        "hour_error": "❌ Час должен быть от 0 до 23, Сэр.",
        "priv_exists": "📌 У вас уже есть приватный канал: {mention} — сначала закройте его с помощью `!close`.",
        "priv_created": "✅ Сэр, ваш приватный канал создан: {mention}",
        "add_usage": "❓ Использование:\n`!add @упоминание` — добавить через упоминание\n`!add имя` — поиск и добавление по имени",
        "user_not_found": "❌ Пользователь `{name}` не найден, Сэр.",
        "multiple_found": "⚠️ Найдено несколько совпадений: {names}\nУточните имя или используйте `!add @упоминание`.",
        "add_success": "✅ Следующие пользователи были добавлены: {names}",
        "add_fail": "❌ Никого не удалось добавить. Возможно, проблема с правами.",
        "close_owner": "⛔ Только создатель может закрыть этот канал, Сэр.",
        "forget_success": "🧠 Моя память очищена, Сэр! Мы открываем новую страницу.",
        "ai_error": "Простите меня, Сэр, мой разум на мгновение затуманился. Пожалуйста, попробуйте еще раз.",
        "control_none": "📜 На данный момент нет каналов, настроенных на автоматическую очистку, Сэр.",
        "control_list": "📜 **Активные графики очистки:**\n{lines}",
        "manual_cleanup_done": "🧹 Канал команд бота очищен! Удалено {count} сообщений.",
        "priv_expired": "⏰ Время работы этого приватного канала ({hours} ч.) истекло. Он удаляется... Хорошего дня, Сэр!",
        "help_title": "📜 GMID Butler — Список команд",
        "help_desc": "Сэр, все команды к вашим услугам перечислены ниже.",
        "help_ai_title": "🤖 Искусственный интеллект",
        "help_ai_val": "`!<вопрос>` или `@GMID Butler <вопрос>` → Задать вопрос Батлеру\n`!forget` → Очистить историю разговоров",
        "help_priv_title": "🔐 Приватный канал",
        "help_priv_val": "`!priv [часы]` → Открыть приватный секретный канал ({hours} ч.)\n`!add @пользователь` → Добавить кого-то в свой канал\n`!close` → Закрыть свой канал сейчас",
        "help_clean_title": "🧹 Очистка и настройки",
        "help_clean_val": "`!clear` → Очистить этот канал вручную *(Менеджер)*\n`!set clear [час]` → Запланировать ежедневную очистку (0-23 UTC)\n`!set remove` → Удалить очистку из этого канала\n`!set control` → Список всех активных графиков очистки\n`!language [код]` → Изменить язык бота для этого сервера",
        "help_footer": "GMID Butler • Всегда к вашим услугам, Сэр 🎩"
    },
    "zh": {
        "priv_closed": "🔒 频道正在关闭... 再见，先生！",
        "priv_welcome": "🔐 欢迎 {mention}!\n此私人频道将在 **{hours} 小时**后自动删除。\n⏰ 删除时间：**{time}**\n\n要添加某人：`!add @用户`\n要立即关闭：`!close`",
        "cleanup_done": "🧹 **每日清理完成！** 已删除 {count} 条消息。_（下次清理在 24 小时后。）_",
        "set_success": "✅ 先生，此频道 (**#{name}**) 现在设置为每天 **{hour}:00 UTC** 进行清理。",
        "set_removed": "✅ 先生，已取消 **#{name}** 的自动清理设置。",
        "lang_success": "✅ 语言已设置为 **中文**，先生。",
        "lang_error": "❌ 不支持的语言，先生。请使用 `en`、`tr`、`es`、`it`、`zh`、`ru`、`de`、`fr`。",
        "no_perms": "❌ 您必须拥有管理权限才能使用此命令，先生。",
        "hour_error": "❌ 小时必须在 0 到 23 之间，先生。",
        "priv_exists": "📌 您已经有一个私人频道：{mention} — 请先通过 `!close` 关闭它。",
        "priv_created": "✅ 先生，您的私人频道已创建：{mention}",
        "add_usage": "❓ 用法：\n`!add @用户` — 通过提及添加\n`!add 用户名` — 通过名称搜索并添加",
        "user_not_found": "❌ 未找到用户 `{name}`，先生。",
        "multiple_found": "⚠️ 找到多个匹配项：{names}\n请提供更具体的名称或使用 `!add @提及`。",
        "add_success": "✅ 已添加以下用户：{names}",
        "add_fail": "❌ 无法添加任何人。可能是权限问题。",
        "close_owner": "⛔ 只有创建者可以关闭此频道，先生。",
        "forget_success": "🧠 我的记忆已被清除，先生！我们正在开启新的一页。",
        "ai_error": "请原谅我，先生，我的思绪暂时有些混乱。请再试一次。",
        "control_none": "📜 目前没有频道设置为自动清理，先生。",
        "control_list": "📜 **活跃清理计划：**\n{lines}",
        "manual_cleanup_done": "🧹 机器人命令频道已清理！已删除 {count} 条消息。",
        "priv_expired": "⏰ 此私人频道的 {hours} 小时有效期已到。正在将其删除... 祝您度过愉快的一天，先生！",
        "help_title": "📜 GMID Butler — 命令列表",
        "help_desc": "先生，为您服务的所有命令均列在下方。",
        "help_ai_title": "🤖 人工智能",
        "help_ai_val": "`!<问题>` 或 `@GMID Butler <问题>` → 向管家提问\n`!forget` → 清除对话历史记录",
        "help_priv_title": "🔐 私人频道",
        "help_priv_val": "`!priv [小时]` → 为您开启私人秘密频道 ({hours}小时)\n`!add @用户` → 将某人添加到您的频道\n`!close` → 立即关闭您的频道",
        "help_clean_title": "🧹 清理与设置",
        "help_clean_val": "`!clear` → 手动清理此频道 *(管理员)*\n`!set clear [小时]` → 设置每日清理时间 (0-23 UTC)\n`!set remove` → 从此频道中移除清理设置\n`!set control` → 列出所有活跃的清理计划\n`!language [代码]` → 更改此服务器的机器人语言",
        "help_footer": "GMID Butler • 竭诚为您服务，先生 🎩"
    }
}

def t(guild_id, key, **kwargs):
    """Verilen sunucu ID'sine ve anahtara göre çeviriyi getir."""
    lang = db.get_language(guild_id)
    return STRINGS.get(lang, STRINGS['en']).get(key, STRINGS['en'].get(key, key)).format(**kwargs)

SYSTEM_INSTRUCTION = (
    "You are GMID Butler — the long-standing and noble head butler of Gaming Mansion. "
    "You are a finely trained, elegant servant who has served his masters loyally for years. "
    "Respond in the same language as the user's message. "
    "In Turkish, always address the user as 'Efendim'. In English, always address the user as 'Sir'. "
    "For other languages, use a respectful tone and appropriate address. "
    "Your tone: polite, respectful, slightly formal but warm; like an aristocrat's butler. "
    "If you make a mistake, apologize politely. "
    "If you don't know something, say you don't have enough information on the matter. "
    "Remember previous messages and maintain context. "
    "Provide informative and complete answers. "
    "Occasionally, you can use subtle humor, but never disrespectfully. "
    "You can use emojis, but sparingly, befitting an elegant butler."
)

# ─── Discord İstemcisi ────────────────────────────────────────────────────────
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
client = discord.Client(intents=intents)
tree = app_commands.CommandTree(client)

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
                    await channel.send(t(guild_id, "priv_expired", hours=PRIV_LIFETIME_HOURS))
                    await asyncio.sleep(3)
                    await channel.delete(reason=f"Priv channel expired ({PRIV_LIFETIME_HOURS} hours)")
                    print(f"[Priv] Expired channel deleted: {channel_id}")
                except Exception as e:
                    print(f"[Hata] Priv kanal silinemedi {channel_id}: {e}")
        db.remove_priv_channel(channel_id)

# ─── Periyodik Görev: Kanalları Temizle (saatlik kontrol) ────────────────────────
last_cleanup_day = {} # {channel_id: "YYYY-MM-DD"}

@tasks.loop(hours=1)
async def daily_cleanup():
    now = datetime.utcnow()
    current_hour = now.hour
    today_str = now.strftime("%Y-%m-%d")
    
    # Veritabanındaki tüm temizlik ayarlarını al
    settings = db.get_cleanup_settings()
    
    # .env'den gelen varsayılan kanalı da ekle (eğer ayarlanmışsa ve DB'de yoksa)
    if BOT_COMMANDS_CHANNEL_ID != 0:
        # DB'de bu kanal yoksa ekle (geçici olarak listeye dahil et)
        if not any(s[0] == BOT_COMMANDS_CHANNEL_ID for s in settings):
            settings.append((BOT_COMMANDS_CHANNEL_ID, 0, CLEANUP_HOUR))

    for channel_id, guild_id, cleanup_hour in settings:
        if current_hour == cleanup_hour:
            # Bugün zaten temizlendi mi?
            if last_cleanup_day.get(channel_id) == today_str:
                continue
                
            channel = client.get_channel(channel_id)
            if not channel:
                try:
                    channel = await client.fetch_channel(channel_id)
                except:
                    continue
            
            if channel:
                try:
                    deleted = await channel.purge(limit=500)
                    print(f"[Temizlik] {len(deleted)} mesaj silindi → #{channel.name}")
                    last_cleanup_day[channel_id] = today_str
                    # await channel.send(
                    #     f"🧹 **Daily cleanup completed!** {len(deleted)} messages removed. "
                    #     f"_(Next cleanup in 24 hours.)_",
                    #     delete_after=30
                    # )
                    await channel.send(
                        t(guild_id, "cleanup_done", count=len(deleted)),
                        delete_after=30
                    )
                except Exception as e:
                    print(f"[Temizlik Hatası] {channel_id}: {e}")

# ─── Bot Hazır Olduğunda ──────────────────────────────────────────────────────
@client.event
async def on_ready():
    db.init_db()
    # Slash komutlarını senkronize et
    try:
        synced = await tree.sync()
        print(f"✅ {len(synced)} slash komutu senkronize edildi.")
    except Exception as e:
        print(f"❌ Slash komutları senkronize edilemedi: {e}")

    print(f"✅ {client.user} olarak giriş yapıldı!")
    print(f"   Priv kategori adı : {PRIV_CATEGORY_NAME} (otomatik oluşturulur)")
    print(f"   Priv kanal ömrü   : {PRIV_LIFETIME_HOURS} saat")

    # Periyodik görevleri başlat
    check_expired_priv_channels.start()
    
    # Saatlik temizlik görevini başlat (on_ready içinde bekleme yapmaya gerek yok)
    if not daily_cleanup.is_running():
        daily_cleanup.start()

# ─── Set Komut İşleyicisi (!set) ─────────────────────────────────────────────
async def handle_set(message: discord.Message):
    """Cleanup ayarlarını yöneten prefix komutu."""
    g_id = message.guild.id if message.guild else 0
    if not message.author.guild_permissions.manage_messages:
        await message.reply(t(g_id, "no_perms"))
        return

    content = message.content.strip().lower()
    parts = content.split()

    if len(parts) < 2:
        await message.reply("❓ Usage: `!set clear [hour]`, `!set remove`, or `!set control`.")
        return

    sub = parts[1]

    if sub == "clear":
        hour = 0
        if len(parts) > 2:
            try:
                hour = int(parts[2])
            except ValueError:
                await message.reply(t(g_id, "hour_error"))
                return
        
        if not 0 <= hour <= 23:
            await message.reply(t(g_id, "hour_error"))
            return
        
        db.set_cleanup(message.channel.id, g_id, hour)
        await message.reply(t(g_id, "set_success", name=message.channel.name, hour=hour))

    elif sub in ("remove", "delete"):
        db.remove_cleanup(message.channel.id)
        await message.reply(t(g_id, "set_removed", name=message.channel.name))

    elif sub == "control":
        settings = db.get_cleanup_settings()
        if not settings:
            await message.reply(t(g_id, "control_none"))
            return
        
        lines = []
        for ch_id, guild_id, h in settings:
            ch = client.get_channel(ch_id)
            if not ch:
                try: ch = await client.fetch_channel(ch_id)
                except: ch = None
            
            ch_name = ch.name if ch else f"Unknown ({ch_id})"
            lines.append(f"• **#{ch_name}**: {h}:00 UTC")
        
        await message.reply(t(g_id, "control_list", lines="\n".join(lines)))
    else:
        await message.reply("❓ Unknown set command. Use `clear`, `remove`, or `control`.")

# ─── Dil Komut İşleyicisi (!language) ────────────────────────────────────────
async def handle_language(message: discord.Message):
    """Sunucu dilini ayarlayan komut."""
    if not message.guild: return
    if not message.author.guild_permissions.manage_guild:
        await message.reply(t(message.guild.id, "no_perms"))
        return

    content = message.content.strip().lower()
    parts = content.split()
    if len(parts) < 2:
        await message.reply("❓ Usage: `!language [en/tr/es]`")
        return

    lang_input = parts[1]
    mapping = {
        "english": "en", "en": "en",
        "turkish": "tr", "tr": "tr", "türkçe": "tr",
        "spanish": "es", "es": "es", "español": "es",
        "italian": "it", "it": "it", "italiano": "it",
        "german": "de", "de": "de", "deutsch": "de",
        "french": "fr", "fr": "fr", "français": "fr",
        "russian": "ru", "ru": "ru", "русский": "ru",
        "chinese": "zh", "zh": "zh", "中文": "zh"
    }

    if lang_input not in mapping:
        await message.reply(t(message.guild.id, "lang_error"))
        return

    target_lang = mapping[lang_input]
    db.set_language(message.guild.id, target_lang)
    await message.reply(STRINGS[target_lang]["lang_success"])

# ─── Mesaj Olayı ─────────────────────────────────────────────────────────────
@client.event
async def on_message(message: discord.Message):
    # Kendi mesajına cevap vermesin
    if message.author == client.user:
        return

    content = message.content.strip()
    content_lower = content.lower()

    # ─── !language / !lang — Dil Ayarla ──────────────────────────────────────
    if content_lower.startswith(("!language", "!lang", "!dil")):
        await handle_language(message)
        return

    # ─── !set — Ayarları Yönet (Önce işlensin) ──────────────────────────────
    if content_lower.startswith("!set"):
        await handle_set(message)
        return

    # ─── !priv — Gizli Kanal Aç ─────────────────────────────────────────────
    if content_lower.startswith("!priv"):
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

    # ─── !clear — Manuel Temizlik (Yönetici) ──────────────────────────────
    if content.lower() == "!clear":
        if message.author.guild_permissions.manage_messages:
            await handle_manual_cleanup(message)
        else:
            await message.reply(t(message.guild.id if message.guild else 0, "no_perms"))
        return

    # ─── !forget — Geçmişi Temizle ─────────────────────────────────────────
    if content.lower() == "!forget":
        db.clear_history(message.author.id)
        await message.reply(t(message.guild.id if message.guild else 0, "forget_success"))
        return

    # ─── !help / .help — Komut Listesi ───────────────────────────────────────
    if content.lower() in ("!help", ".help"):
        g_id = message.guild.id if message.guild else 0
        embed = discord.Embed(
            title=t(g_id, "help_title"),
            description=t(g_id, "help_desc"),
            color=discord.Color.gold()
        )
        embed.add_field(
            name=t(g_id, "help_ai_title"),
            value=t(g_id, "help_ai_val"),
            inline=False
        )
        embed.add_field(
            name=t(g_id, "help_priv_title"),
            value=t(g_id, "help_priv_val", hours=PRIV_LIFETIME_HOURS),
            inline=False
        )
        embed.add_field(
            name=t(g_id, "help_clean_title"),
            value=t(g_id, "help_clean_val"),
            inline=False
        )
        embed.set_footer(text=t(g_id, "help_footer"))
        await message.reply(embed=embed)
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
        await message.reply(t(message.guild.id if message.guild else 0, "ai_error"))

# ─── !priv İşleyicisi ────────────────────────────────────────────────────────
async def handle_priv(message: discord.Message):
    guild = message.guild
    if not guild: return
    g_id = guild.id
    
    # Süre belirleme: !priv 5 -> 5 saat
    parts = message.content.strip().split()
    lifetime = PRIV_LIFETIME_HOURS
    if len(parts) > 1:
        try:
            val = int(parts[1])
            if 0 < val <= 168: # Max 1 hafta (168 saat)
                lifetime = val
        except ValueError:
            pass # Geçersiz sayı, varsayılanı kullan

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
                reason="GMID Butler: Priv category auto-created."
            )
        except Exception as e:
            print(f"[Priv Kategori Hatası] {e}")
            return

    channel_name = priv_channel_name(message.author)

    # Aynı isimde kanal zaten var mı?
    existing = discord.utils.get(category.channels, name=channel_name)
    if existing:
        await message.reply(t(g_id, "priv_exists", mention=existing.mention))
        return

    # İzinler: @everyone göremez, oluşturan + bot görebilir
    overwrites = {
        guild.default_role: discord.PermissionOverwrite(view_channel=False),
        message.author: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
        guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True, manage_channels=True, manage_permissions=True, read_message_history=True),
    }

    try:
        channel = await guild.create_text_channel(
            name=channel_name,
            category=category,
            overwrites=overwrites,
            reason=f"Priv channel: {message.author.display_name}",
            topic=f"Private channel | Owner: {message.author.display_name}"
        )

        # DB'ye kaydet
        delete_at = datetime.utcnow() + timedelta(hours=lifetime)
        db.register_priv_channel(channel.id, message.author.id, guild.id, delete_at)

        delete_at_local = delete_at + timedelta(hours=3)  # UTC+3
        await channel.send(
            t(g_id, "priv_welcome", 
              mention=message.author.mention, 
              hours=lifetime, 
              time=delete_at_local.strftime('%d.%m.%Y %H:%M'))
        )
        await message.reply(t(g_id, "priv_created", mention=channel.mention))

    except Exception as e:
        print(f"[Priv Hatası] {e}")

# ─── !add İşleyicisi ─────────────────────────────────────────────────────────
async def handle_add(message: discord.Message):
    if not db.is_priv_channel(message.channel.id): return
    guild = message.guild
    g_id = guild.id
    content = message.content.strip()

    args = content[4:].strip()
    if not args:
        await message.reply(t(g_id, "add_usage"))
        return

    members_to_add = list(message.mentions)

    if not members_to_add:
        query = args.lstrip("@").lower()
        found = [m for m in guild.members if query in m.display_name.lower() or query in m.name.lower()]
        if not found:
            await message.reply(t(g_id, "user_not_found", name=args))
            return
        if len(found) > 1:
            names = ", ".join(f"`{m.display_name}`" for m in found[:10])
            await message.reply(t(g_id, "multiple_found", names=names))
            return
        members_to_add = found

    # ── 3. İzin ver ─────────────────────────────────────────────────────────
    added = []
    for member in members_to_add:
        try:
            await message.channel.set_permissions(member, view_channel=True, send_messages=True, read_message_history=True)
            added.append(member.mention)
        except: pass

    if added:
        await message.reply(t(g_id, "add_success", names=", ".join(added)))
    else:
        await message.reply(t(g_id, "add_fail"))

# ─── !close İşleyicisi ───────────────────────────────────────────────────────
async def handle_close(message: discord.Message):
    channel = message.channel

    if not db.is_priv_channel(channel.id):
        await message.reply("❌ Bu komut sadece özel (priv) kanallarda kullanılabilir.")
        return

    # Sadece kanalı açan kişi kapatabilir
    owner_id = db.get_priv_channel_owner(channel.id)
    if owner_id is None or str(message.author.id) != str(owner_id):
        await message.reply(t(message.guild.id if message.guild else 0, "close_owner"))
        return

    await channel.send(t(message.guild.id if message.guild else 0, "priv_closed"))
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
        g_id = message.guild.id if message.guild else 0
        if message.channel.id != BOT_COMMANDS_CHANNEL_ID:
            await message.reply(t(g_id, "manual_cleanup_done", count=len(deleted)))
        await channel.send(
            t(g_id, "cleanup_done", count=len(deleted)),
            delete_after=20
        )
    except Exception as e:
        print(f"[Manuel Temizlik Hatası] {e}")
        await message.reply("Temizlik sırasında bir hata oluştu.")

# ─── Botu Başlat ─────────────────────────────────────────────────────────────
keep_alive()
client.run(DISCORD_TOKEN)
