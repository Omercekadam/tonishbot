import discord
from discord.ext import commands
from discord.ui import View, Button
import os

class TicketCloseView(View):
    """
    Ticket kapatma butonu görünümü.
    Ticket kanalı içinde görünür.
    """
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="Ticketi Kapat", style=discord.ButtonStyle.danger, custom_id="kalici_ticket_kapat_butonu", emoji="🔒")
    async def close_ticket(self, interaction: discord.Interaction, button: Button):
        """Ticket kapatma butonuna basıldığında çalışır."""
        await interaction.response.defer()
        channel = interaction.channel
        
        # Kanalın gerçekten bir ticket kanalı olup olmadığını kontrol et
        if not channel.topic or "Ticket sahibi:" not in channel.topic:
            return await interaction.followup.send("Bu bir ticket kanalı değil.", ephemeral=True)

        # Yetki kontrolü (Basitleştirilmiş)
        # Gerçek uygulamada moderatör rolü kontrolü yapılmalı
        
        # Kullanıcının yazma iznini kapat
        await channel.set_permissions(interaction.user, send_messages=False)
        
        # Butonu güncelle
        button.disabled = True
        button.label = "Kapatıldı"
        await interaction.message.edit(view=self)
        await interaction.followup.send("Ticket kapatıldı.")

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
        
        # Gerekli ID'leri al
        cat_id = int(os.getenv('TICKET_CATEGORY_ID', 0))
        mod_role_id = int(os.getenv('MODERATOR_ROLU_ID', 0))
        
        category = interaction.guild.get_channel(cat_id)
        mod_role = interaction.guild.get_role(mod_role_id)
        
        if not category or not mod_role:
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
        new_ch = await interaction.guild.create_text_channel(ch_name, category=category, overwrites=overwrites, topic=f"Ticket sahibi: {interaction.user.id}")
        
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
    @commands.has_permissions(administrator=True)
    async def ticketkur(self, ctx):
        """Ticket oluşturma mesajını kanala gönderir (Admin)."""
        embed = discord.Embed(title="Destek Talebi", description="Ticket oluşturmak için butona basın.", color=0xeb596d)
        await ctx.send(embed=embed, view=TicketCreationView())
        await ctx.message.delete()

async def setup(bot):
    await bot.add_cog(Tickets(bot))
