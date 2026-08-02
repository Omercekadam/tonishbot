import discord
from discord.ext import commands
from discord.ui import View, Button
import logging
import os
import re

log = logging.getLogger(__name__)

# Ticket kanalının topic'inde sahibin ID'si bu formatta saklanır
TOPIC_PREFIX = "Ticket sahibi:"
_TOPIC_RE = re.compile(rf"{re.escape(TOPIC_PREFIX)}\s*(\d+)")

CLOSE_BUTTON_ID = "kalici_ticket_kapat_butonu"


def parse_ticket_owner_id(topic: str | None) -> int | None:
    """Kanal topic'inden ticket sahibinin Discord ID'sini çıkarır."""
    if not topic:
        return None
    match = _TOPIC_RE.search(topic)
    return int(match.group(1)) if match else None


def build_closed_view() -> View:
    """
    Kapatılmış ticket için devre dışı buton görünümü üretir.

    Kalıcı (add_view ile kaydedilmiş) view instance'ı paylaşılan tekil bir nesnedir;
    üzerindeki butonu doğrudan değiştirmek tüm ticket'ları etkiler. Bu yüzden mesajı
    güncellerken her seferinde yeni bir view oluşturuyoruz.
    """
    view = View(timeout=None)
    view.add_item(
        Button(
            label="Kapatıldı",
            style=discord.ButtonStyle.secondary,
            emoji="🔒",
            disabled=True,
            custom_id=CLOSE_BUTTON_ID,
        )
    )
    return view


class TicketCloseView(View):
    """
    Ticket kapatma butonu görünümü (kalıcı).
    Ticket kanalı içinde görünür.
    """
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticketi Kapat", style=discord.ButtonStyle.danger, custom_id=CLOSE_BUTTON_ID, emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        """Ticket kapatma butonuna basıldığında çalışır."""
        await interaction.response.defer()
        channel = interaction.channel

        # Kanalın gerçekten bir ticket kanalı olup olmadığını kontrol et
        owner_id = parse_ticket_owner_id(getattr(channel, "topic", None))
        if owner_id is None:
            return await interaction.followup.send("Bu bir ticket kanalı değil.", ephemeral=True)

        # --- Yetki kontrolü: sadece ticket sahibi, moderatör veya kanal yöneticisi ---
        mod_role_id = int(os.getenv('MODERATOR_ROLU_ID', 0))
        actor = interaction.user

        is_owner = actor.id == owner_id
        is_mod = any(r.id == mod_role_id for r in getattr(actor, "roles", []))
        is_manager = getattr(actor.guild_permissions, "manage_channels", False)

        if not (is_owner or is_mod or is_manager):
            return await interaction.followup.send(
                "Bu ticketi sadece sahibi veya bir yetkili kapatabilir.", ephemeral=True
            )

        # --- Yazma iznini TICKET SAHİBİNDEN al (butona basandan değil) ---
        owner = interaction.guild.get_member(owner_id)
        if owner:
            try:
                await channel.set_permissions(
                    owner, view_channel=True, send_messages=False,
                    reason=f"Ticket {actor} tarafından kapatıldı",
                )
            except discord.Forbidden:
                log.warning("Ticket izinleri güncellenemedi, yetki yetersiz (channel_id=%s)", channel.id)
                return await interaction.followup.send(
                    "Kanal izinlerini değiştiremedim — botun yetkisi yetersiz.", ephemeral=True
                )
            except discord.HTTPException:
                log.exception("Ticket izinleri güncellenemedi (channel_id=%s)", channel.id)
                return await interaction.followup.send(
                    "Ticket kapatılırken bir sorun oldu, tekrar dene.", ephemeral=True
                )
        else:
            log.info("Ticket sahibi sunucuda bulunamadı (owner_id=%s)", owner_id)

        # Butonu devre dışı göster — paylaşılan kalıcı view'a dokunmadan
        try:
            await interaction.message.edit(view=build_closed_view())
        except discord.HTTPException:
            log.exception("Ticket mesajı güncellenemedi (channel_id=%s)", channel.id)

        await interaction.followup.send(f"🔒 Ticket {actor.mention} tarafından kapatıldı.")


class TicketCreationView(View):
    """
    Ticket oluşturma butonu görünümü.
    Kullanıcılar bu butona basarak yeni bir destek talebi oluşturur.
    """
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticket Oluştur", style=discord.ButtonStyle.primary, emoji="📩", custom_id="kalici_ticket_tusu")
    async def create_ticket(self, interaction: discord.Interaction, button: Button):
        """Ticket oluşturma butonuna basıldığında çalışır."""
        await interaction.response.defer(ephemeral=True)

        if interaction.guild is None:
            return await interaction.followup.send("Bu buton sadece sunucuda çalışır.", ephemeral=True)

        # Gerekli ID'leri al
        cat_id = int(os.getenv('TICKET_CATEGORY_ID', 0))
        mod_role_id = int(os.getenv('MODERATOR_ROLU_ID', 0))

        category = interaction.guild.get_channel(cat_id)
        mod_role = interaction.guild.get_role(mod_role_id)

        if not category or not mod_role:
            log.error(
                "Ticket ayarları eksik: TICKET_CATEGORY_ID=%s (bulundu=%s), MODERATOR_ROLU_ID=%s (bulundu=%s)",
                cat_id, bool(category), mod_role_id, bool(mod_role),
            )
            return await interaction.followup.send("Sistem ayarları eksik.", ephemeral=True)

        # Kanal ismini belirle (ticket-kullaniciID)
        ch_name = f"ticket-{interaction.user.id}"

        # Zaten açık bir ticket var mı kontrol et
        existing = discord.utils.get(interaction.guild.text_channels, name=ch_name, category=category)
        if existing:
            return await interaction.followup.send(f"Zaten açık: {existing.mention}", ephemeral=True)

        # İzinleri ayarla (Sadece kullanıcı, modlar ve bot görebilir)
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            mod_role: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            interaction.guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        # Kanalı oluştur
        try:
            new_ch = await interaction.guild.create_text_channel(
                ch_name,
                category=category,
                overwrites=overwrites,
                topic=f"{TOPIC_PREFIX} {interaction.user.id}",
                reason=f"{interaction.user} destek talebi açtı",
            )
        except discord.Forbidden:
            log.warning("Ticket kanalı oluşturulamadı, yetki yetersiz (guild_id=%s)", interaction.guild.id)
            return await interaction.followup.send(
                "Ticket kanalı oluşturamadım — botun yetkisi yetersiz. Bir yetkiliye haber ver.",
                ephemeral=True,
            )
        except discord.HTTPException:
            log.exception("Ticket kanalı oluşturulamadı (guild_id=%s)", interaction.guild.id)
            return await interaction.followup.send(
                "Ticket oluşturulurken bir sorun oldu, birazdan tekrar dene.", ephemeral=True
            )

        # Karşılama mesajı ve kapatma butonunu gönder
        embed = discord.Embed(title="Destek Talebi", description=f"Merhaba {interaction.user.mention}, yetkililer birazdan burada olacak.", color=discord.Color.green())
        await new_ch.send(f"{interaction.user.mention} {mod_role.mention}", embed=embed, view=TicketCloseView())
        await interaction.followup.send(f"Oluşturuldu: {new_ch.mention}", ephemeral=True)


class Tickets(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Bot yeniden başladığında butonların çalışmaya devam etmesi için view'ları ekle."""
        self.bot.add_view(TicketCreationView())
        self.bot.add_view(TicketCloseView())

    @commands.command()
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def ticketkur(self, ctx):
        """Ticket oluşturma mesajını kanala gönderir (Admin)."""
        embed = discord.Embed(title="Destek Talebi", description="Ticket oluşturmak için butona basın.", color=0xeb596d)
        await ctx.send(embed=embed, view=TicketCreationView())
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass


async def setup(bot):
    await bot.add_cog(Tickets(bot))
