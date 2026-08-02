import discord
import logging
import os
from discord.ext import commands
from dotenv import load_dotenv

# Bot dosyasının bulunduğu klasör. Cog'lar font/görsel/veritabanı dosyalarını
# göreli yolla açtığı için çalışma dizinini buraya sabitliyoruz — böylece bot
# hangi dizinden başlatılırsa başlatılsın dosyalar bulunur.
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
os.chdir(BASE_DIR)

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
# discord.py'nin gürültülü bağlantı loglarını kıs
logging.getLogger("discord").setLevel(logging.WARNING)
logging.getLogger("discord.http").setLevel(logging.WARNING)

log = logging.getLogger("tonishbot")

TOKEN = os.getenv('DISCORD_TOKEN')
CEK_DISCORD_ID = int(os.getenv('CEK_DISCORD_ID', 0))

intents = discord.Intents.default()
intents.members = True
intents.message_content = True


class TonishBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!",
            intents=intents,
            help_command=None,
            # Varsayılan olarak @everyone/@here ve rol etiketlerini engelle.
            # Kasıtlı ping atan tek komut !duyuru; o kendi allowed_mentions'ını
            # açıkça belirtiyor.
            allowed_mentions=discord.AllowedMentions(everyone=False, roles=False, users=True),
        )
        self.cek_id = CEK_DISCORD_ID

    async def setup_hook(self):
        """
        Bot başlatılırken çalışacak kurulum fonksiyonu.
        Eklentileri (Cogs) burada yüklüyoruz.
        """
        log.info("--- TonishBot Başlatılıyor ---")

        cogs_dir = os.path.join(BASE_DIR, 'cogs')
        for filename in sorted(os.listdir(cogs_dir)):
            if filename.endswith('.py') and not filename.startswith('_'):
                try:
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    log.info("[+] Eklenti Yüklendi: %s", filename)
                except Exception:
                    log.exception("[-] Eklenti Yüklenemedi: %s", filename)

        log.info("--- Tüm Eklentiler İşlendi ---")

    async def on_ready(self):
        """Bot Discord'a başarıyla bağlandığında çalışır."""
        log.info("%s olarak giriş yapıldı! (ID: %s)", self.user, self.user.id)
        log.info("%d sunucuda aktif", len(self.guilds))

    async def on_command_error(self, ctx, error):
        """
        Global hata yakalayıcı.

        Bu olmadan eksik argüman / yetkisiz kullanım / bekleme süresi gibi durumlarda
        kullanıcıya hiçbir geri bildirim gitmiyor, hata sadece konsola düşüyordu.
        """
        # Komutun veya cog'un kendi hata yakalayıcısı varsa ona karışma
        if ctx.command and ctx.command.has_error_handler():
            return
        if ctx.cog and ctx.cog.has_error_handler():
            return

        # Yazım hatası / var olmayan komut — sessizce yok say
        if isinstance(error, commands.CommandNotFound):
            return

        if isinstance(error, commands.MissingRequiredArgument):
            kullanim = f"{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}".strip()
            return await ctx.send(
                f"⚠️ Eksik bilgi: **{error.param.name}**\n**Doğru kullanım:** `{kullanim}`"
            )

        if isinstance(error, (commands.BadArgument, commands.BadUnionArgument)):
            kullanim = f"{ctx.prefix}{ctx.command.qualified_name} {ctx.command.signature}".strip()
            return await ctx.send(
                f"⚠️ Girdiğin değer uygun değil.\n**Doğru kullanım:** `{kullanim}`"
            )

        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.send("Bu komut sadece sunucu içinde çalışır. 🏠")

        if isinstance(error, commands.MissingPermissions):
            return await ctx.send("Bu komutu kullanmak için yetkin yok. 🚫")

        if isinstance(error, commands.BotMissingPermissions):
            eksik = ", ".join(error.missing_permissions)
            return await ctx.send(f"Bu komutu çalıştıramıyorum, şu yetkilerim eksik: **{eksik}**")

        if isinstance(error, commands.CommandOnCooldown):
            kalan = int(error.retry_after)
            if kalan >= 3600:
                sure = f"{kalan // 3600} saat {(kalan % 3600) // 60} dakika"
            elif kalan >= 60:
                sure = f"{kalan // 60} dakika {kalan % 60} saniye"
            else:
                sure = f"{max(1, kalan)} saniye"
            return await ctx.send(f"⏳ Biraz soluklan! Tekrar kullanmak için **{sure}** beklemelisin.")

        # is_bot_owner gibi özel check'ler buraya düşer
        if isinstance(error, commands.CheckFailure):
            return await ctx.send(str(error) or "Bu komutu kullanamazsın. 🚫")

        # Komut içinde patlayan gerçek hata — logla, kullanıcıya ham hatayı gösterme
        orijinal = getattr(error, "original", error)
        log.exception(
            "'%s' komutunda beklenmedik hata (user=%s, channel=%s)",
            ctx.command, ctx.author.id, getattr(ctx.channel, "id", None),
            exc_info=orijinal,
        )
        try:
            await ctx.send("Beklenmedik bir hata oluştu. 😥 Yetkiliye haber verildi.")
        except discord.HTTPException:
            pass


bot = TonishBot()

if __name__ == "__main__":
    if not TOKEN:
        log.error("DISCORD_TOKEN bulunamadı. .env dosyasını kontrol edin.")
    else:
        # log_handler=None -> discord.py kendi logging kurulumunu ezmesin
        bot.run(TOKEN, log_handler=None)
