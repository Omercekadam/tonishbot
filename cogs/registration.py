import discord
from discord.ext import commands
from discord.ui import View, Button, Modal, TextInput, Select
import logging
import os
import io
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

# Discord takma adı (nickname) uzunluk sınırı
NICK_LIMIT = 32

# ROLLER
# Kullanıcıların seçebileceği roller ve özellikleri
ROLE_OPTIONS = {
    1430626208521126041: {"label": "Developer", "emoji": "💻", "description": "Oyun geliştirme ile ilgileniyorum."},
    1430627371353903115: {"label": "Artist (2D/3D)", "emoji": "🎨", "description": "2D/3D Görsel sanatlar ile ilgileniyorum."},
    1430627405600391208: {"label": "Level Designer", "emoji": "👾", "description": "Oyun tasarımı ile ilgileniyorum."},
    1430627431152091327: {"label": "Storyteller", "emoji": "✏️", "description": "Hikaye anlatımı ile ilgileniyorum."},
    1430627474206625924: {"label": "UI/UX Designer", "emoji": "🚥", "description": "UI/UX tasarımı ile ilgileniyorum."},
    1430627494805110784: {"label": "Sound Artist", "emoji": "🎤", "description": "Ses ve müzik ile ilgileniyorum."},
    1430627516778942484: {"label": "Playtester", "emoji": "🕹️", "description": "Oyun testi ve QA ile ilgileniyorum."},
    1430627543849111763: {"label": "Gamer", "emoji": "🎮", "description": "Oyuncuyum ve oyun oynamayı seviyorum."},
    1430627564829020340: {"label": "Mentor", "emoji": "👑", "description": "Diğer geliştiricilere rehberlik ediyorum."},
    1430627593274785862: {"label": "Duyuru AL", "emoji": "🔔", "description": "Tüm etkinlikleri takip etmek istiyorum."},
}


def build_nickname(isim: str, nickname: str, soyisim: str, limit: int = NICK_LIMIT) -> str:
    """
    'İsim 'Nick' Soyisim' formatında takma ad üretir.
    Discord'un 32 karakter sınırını aşmayacak şekilde kademeli olarak kısaltır:
    tam ad -> soyisimsiz -> isimsiz -> sadece nickname -> zorla kırpma.
    """
    isim, nickname, soyisim = isim.strip(), nickname.strip(), soyisim.strip()

    for aday in (
        f"{isim} '{nickname}' {soyisim}",
        f"{isim} '{nickname}'",
        f"'{nickname}' {soyisim}",
        nickname,
    ):
        aday = " ".join(aday.split())
        if aday and len(aday) <= limit:
            return aday

    return (nickname[:limit].strip() or isim[:limit].strip() or "Uye")


class RegistrationModal(Modal, title="TonishBot Kayıt Paneli"):
    """
    Kullanıcı kayıt formu (Modal).
    İsim, soyisim ve nickname bilgilerini alır; form GÖNDERİLDİĞİNDE
    takma adı ayarlar ve rolleri günceller.
    """
    form_isim = TextInput(label="İsminiz", placeholder="İsim", max_length=20)
    form_soyisim = TextInput(label="Soyisminiz", placeholder="Soyisim", max_length=20)
    form_nickname = TextInput(label="Nickname", placeholder="Tonish", max_length=20)

    def __init__(self, topluluk_rol_id: int, kayitsiz_rol_id: int):
        super().__init__()
        self.topluluk_rol_id = topluluk_rol_id
        self.kayitsiz_rol_id = kayitsiz_rol_id

    async def on_submit(self, interaction: discord.Interaction):
        """Form gönderildiğinde çalışır. Roller SADECE burada değişir."""
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        if interaction.guild is None or not isinstance(member, discord.Member):
            return await interaction.followup.send(
                "Bu form sadece sunucu içinden doldurulabilir.", ephemeral=True
            )

        new_nick = build_nickname(
            self.form_isim.value, self.form_nickname.value, self.form_soyisim.value
        )

        sonuclar = []

        # 1) Takma adı ayarla
        try:
            await member.edit(nick=new_nick, reason="TonishBot kayıt formu")
            sonuclar.append(f"İsmin **{new_nick}** olarak ayarlandı.")
        except discord.Forbidden:
            sonuclar.append(
                "⚠️ İsmini değiştiremedim (yetkim yetmiyor veya rolün benden yüksek). "
                f"Kendin şu şekilde ayarlayabilirsin: **{new_nick}**"
            )
        except discord.HTTPException:
            log.exception("Nickname ayarlanamadı (user_id=%s)", member.id)
            sonuclar.append("⚠️ İsmin ayarlanırken bir sorun oldu.")

        # 2) Rolleri güncelle (Kayıtsız rolünü al, Topluluk rolünü ver)
        try:
            kayitsiz = interaction.guild.get_role(self.kayitsiz_rol_id)
            topluluk = interaction.guild.get_role(self.topluluk_rol_id)

            if kayitsiz and kayitsiz in member.roles:
                await member.remove_roles(kayitsiz, reason="TonishBot kayıt tamamlandı")
            if topluluk and topluluk not in member.roles:
                await member.add_roles(topluluk, reason="TonishBot kayıt tamamlandı")

            if topluluk:
                sonuclar.append(f"**{topluluk.name}** rolü verildi.")
        except discord.Forbidden:
            log.warning("Kayıt rolleri verilemedi, bot yetkisi yetersiz (user_id=%s)", member.id)
            sonuclar.append("⚠️ Rollerin verilemedi, bir yetkiliye haber ver.")
        except discord.HTTPException:
            log.exception("Kayıt rolleri güncellenemedi (user_id=%s)", member.id)
            sonuclar.append("⚠️ Rollerin güncellenirken bir sorun oldu.")

        await interaction.followup.send(
            "✅ Kaydın tamamlandı!\n" + "\n".join(f"• {s}" for s in sonuclar),
            ephemeral=True,
        )

    async def on_error(self, interaction: discord.Interaction, error: Exception):
        log.exception("Kayıt formu hatası", exc_info=error)
        mesaj = "Kayıt sırasında beklenmedik bir hata oluştu. Bir yetkiliye haber ver."
        if interaction.response.is_done():
            await interaction.followup.send(mesaj, ephemeral=True)
        else:
            await interaction.response.send_message(mesaj, ephemeral=True)


class RegistrationView(View):
    """
    Kayıt butonu görünümü (kalıcı — bot yeniden başlasa da çalışır).
    Kullanıcı butona bastığında RegistrationModal açılır; roller form
    gönderildiğinde modal içinde verilir.
    """
    def __init__(self, topluluk_rol_id: int, kayitsiz_rol_id: int):
        super().__init__(timeout=None)  # Zaman aşımı yok (Sürekli aktif)
        self.topluluk_rol_id = topluluk_rol_id
        self.kayitsiz_rol_id = kayitsiz_rol_id

    @discord.ui.button(label="Kayıt Olmak İçin Tıkla", style=discord.ButtonStyle.green, custom_id="kalici_kayit_butonu", emoji="👋")
    async def register_button_callback(self, interaction: discord.Interaction, button: Button):
        if interaction.guild is None:
            return await interaction.response.send_message(
                "Bu buton sadece sunucu içinde çalışır.", ephemeral=True
            )
        await interaction.response.send_modal(
            RegistrationModal(self.topluluk_rol_id, self.kayitsiz_rol_id)
        )


class RoleSelect(Select):
    """
    Rol seçim menüsü (Dropdown).
    Kullanıcıların ilgi alanlarına göre rol seçmesini sağlar.
    """
    def __init__(self):
        # Seçenekleri ROLE_OPTIONS sözlüğünden oluştur
        options = [
            discord.SelectOption(label=d["label"], value=str(rid), emoji=d["emoji"], description=d["description"])
            for rid, d in ROLE_OPTIONS.items()
        ]
        super().__init__(custom_id="kalici_rol_secme_menusu", placeholder="Rolleri seçin...", min_values=0, max_values=len(options), options=options)

    async def callback(self, interaction: discord.Interaction):
        """Kullanıcı seçim yaptığında çalışır."""
        await interaction.response.defer(ephemeral=True)

        member = interaction.user
        if interaction.guild is None or not isinstance(member, discord.Member):
            return await interaction.followup.send(
                "Bu menü sadece sunucu içinde çalışır.", ephemeral=True
            )

        selected_ids = set(int(v) for v in self.values)

        to_add, to_remove = [], []
        # Seçilen rolleri ver, seçilmeyenleri (eğer varsa) al
        for rid in ROLE_OPTIONS.keys():
            role = interaction.guild.get_role(rid)
            if not role:
                continue
            if rid in selected_ids and role not in member.roles:
                to_add.append(role)
            elif rid not in selected_ids and role in member.roles:
                to_remove.append(role)

        try:
            if to_add:
                await member.add_roles(*to_add, reason="Rol menüsü seçimi")
            if to_remove:
                await member.remove_roles(*to_remove, reason="Rol menüsü seçimi")
        except discord.Forbidden:
            log.warning("Rol menüsü rolleri güncelleyemedi, yetki yetersiz (user_id=%s)", member.id)
            return await interaction.followup.send(
                "Rollerini güncelleyemedim — botun yetkisi yetersiz. Bir yetkiliye haber ver.",
                ephemeral=True,
            )
        except discord.HTTPException:
            log.exception("Rol menüsü güncellemesi başarısız (user_id=%s)", member.id)
            return await interaction.followup.send(
                "Rollerin güncellenirken bir sorun oldu, birazdan tekrar dene.", ephemeral=True
            )

        if not to_add and not to_remove:
            return await interaction.followup.send("Rollerinde bir değişiklik yok.", ephemeral=True)

        parcalar = []
        if to_add:
            parcalar.append("Eklendi: " + ", ".join(r.name for r in to_add))
        if to_remove:
            parcalar.append("Kaldırıldı: " + ", ".join(r.name for r in to_remove))
        await interaction.followup.send("Rollerin güncellendi!\n" + "\n".join(parcalar), ephemeral=True)


class RoleSelectView(View):
    """Rol seçim menüsünü barındıran görünüm (kalıcı)."""
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())


class Registration(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Gerekli ID'leri al
        self.kayit_kanali_id = int(os.getenv('KAYIT_KANALI_ID', 0))
        self.welcome_channel_id = int(os.getenv('WELCOME_CHANNEL_ID', 0))
        self.topluluk_rolu_id = int(os.getenv('TOPLULUK_ROLU_ID', 0))
        self.kayitsiz_role_id = int(os.getenv('KAYITSIZ_ROLE_ID', 0))

    async def cog_load(self):
        """
        Bot yeniden başladığında eski mesajlardaki butonların çalışmaya devam etmesi
        için kalıcı view'ları kaydet. Bu olmadan restart sonrası tüm kayıt ve rol
        butonları 'This interaction failed' verir.
        """
        self.bot.add_view(RegistrationView(self.topluluk_rolu_id, self.kayitsiz_role_id))
        self.bot.add_view(RoleSelectView())

    def create_welcome_image(self, member_name, guild_name, avatar_bytes):
        """
        Pillow kütüphanesi ile hoş geldin görseli oluşturur.
        Bu işlem işlemciyi yorabilir, bu yüzden executor ile çalıştırılmalıdır.
        """
        try:
            background = Image.open("background.png").convert("RGBA")
            font_user = ImageFont.truetype("usernamefont.otf", 70)
            font_welcome = ImageFont.truetype("welcomefont.ttf", 30)

            # Avatarı işle
            avatar_image = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
            avatar_image = avatar_image.resize((140, 140))

            # Yuvarlak maske oluştur
            mask = Image.new("L", (140, 140), 0)
            ImageDraw.Draw(mask).ellipse((0, 0, 140, 140), fill=255)

            # Avatarı arka plana yapıştır
            draw_surface = background.copy()
            draw_surface.paste(avatar_image, (75, 55), mask)

            # Yazıları ekle
            draw = ImageDraw.Draw(draw_surface)
            draw.text((230, 65), member_name, font=font_user, fill="#0F0F0F")
            draw.text((230, 145), f"{guild_name}'a Hosgeldin", font=font_welcome, fill="#EEEEEE")

            # Görseli belleğe kaydet
            buffer = io.BytesIO()
            draw_surface.save(buffer, "PNG")
            buffer.seek(0)
            return buffer
        except Exception:
            log.exception("Hoş geldin görseli oluşturulamadı")
            return None

    @commands.Cog.listener()
    async def on_member_join(self, member):
        """Sunucuya yeni biri katıldığında çalışır."""
        # Otomatik olarak 'Kayıtsız' rolünü ver
        try:
            role = member.guild.get_role(self.kayitsiz_role_id)
            if role:
                await member.add_roles(role, reason="Yeni üye - otomatik kayıtsız rolü")
        except discord.HTTPException:
            log.exception("Otomatik kayıtsız rolü verilemedi (user_id=%s)", member.id)

        # Hoş geldin mesajı ve görseli gönder
        channel = self.bot.get_channel(self.welcome_channel_id)
        if channel:
            buffer = None
            try:
                avatar_bytes = await member.display_avatar.read()
                # Görsel oluşturma işlemini ana döngüyü bloklamadan yap (Executor)
                buffer = await self.bot.loop.run_in_executor(
                    None, self.create_welcome_image, member.display_name, member.guild.name, avatar_bytes
                )
            except Exception:
                log.exception("Hoş geldin görseli hazırlanamadı (user_id=%s)", member.id)

            try:
                if buffer:
                    await channel.send(
                        f"Sunucumuza hoş geldin, {member.mention}! :tada:",
                        file=discord.File(buffer, "welcome.png"),
                    )
                else:
                    await channel.send(f"Aramıza hoş geldin, {member.mention}! :tada:")
            except discord.HTTPException:
                log.exception("Hoş geldin mesajı gönderilemedi (user_id=%s)", member.id)

        # Kayıt kanalına bilgilendirme mesajı at
        k_channel = self.bot.get_channel(self.kayit_kanali_id)
        if k_channel:
            try:
                view = RegistrationView(self.topluluk_rolu_id, self.kayitsiz_role_id)
                await k_channel.send(
                    f"Aramıza hoş geldin, {member.mention}! Kayıt olmak için butona bas.", view=view
                )
            except discord.HTTPException:
                log.exception("Kayıt mesajı gönderilemedi (user_id=%s)", member.id)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def kayittest(self, ctx):
        """Kayıt butonunu test etmek için komut (Admin)."""
        view = RegistrationView(self.topluluk_rolu_id, self.kayitsiz_role_id)
        await ctx.send("Kayıt testi:", view=view)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def kayital(self, ctx):
        """Kayıt butonunu kanala gönderir (Admin)."""
        view = RegistrationView(self.topluluk_rolu_id, self.kayitsiz_role_id)
        await ctx.send("Kayıt ol:", view=view)

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def rolmenusu(self, ctx):
        """Rol seçim menüsünü kanala gönderir (Admin)."""
        embed = discord.Embed(title="Rol Seçimi", description="İlgilendiğiniz alanları seçin.", color=discord.Color.magenta())
        await ctx.send(embed=embed, view=RoleSelectView())
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def rolbilgi(self, ctx):
        """Rollerin açıklamalarını listeler (Admin)."""
        embed = discord.Embed(title="Rol Bilgileri", color=0xFEE75C)
        for rid, d in ROLE_OPTIONS.items():
            embed.add_field(name=f"{d['emoji']} {d['label']}", value=d['description'], inline=False)
        await ctx.send(embed=embed)
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(Registration(bot))
