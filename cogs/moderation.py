import discord
from discord.ext import commands
from datetime import timedelta
import os

class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    def is_bot_owner():
        """
        Özel yetki kontrolü dekoratörü.
        Sadece bot sahibi (CEK_DISCORD_ID) komutu kullanabilir.
        """
        async def predicate(ctx):
            if ctx.author.id != ctx.bot.cek_id:
                raise commands.CheckFailure("Bu komutu sadece bot sahibi kullanabilir.")
            return True
        return commands.check(predicate)

    def parse_duration(self, duration_str):
        """
        Süre stringini (örn: 10m, 1h) timedelta objesine çevirir.
        s: saniye, m: dakika, h: saat, d: gün
        """
        unit = duration_str[-1].lower()
        amount = int(duration_str[:-1])
        if unit == 's': return timedelta(seconds=amount)
        elif unit == 'm': return timedelta(minutes=amount)
        elif unit == 'h': return timedelta(hours=amount)
        elif unit == 'd': return timedelta(days=amount)
        else: raise ValueError("Geçersiz birim")

    @commands.command(name="cektimeout")
    @is_bot_owner()
    async def cektimeout(self, ctx, member: discord.Member, duration_str: str, *, reason="cek tarafından susturuldu"):
        """Kullanıcıya zaman aşımı (timeout) uygular."""
        try:
            duration = self.parse_duration(duration_str)
            await member.timeout(duration, reason=reason)
            await ctx.send(f"✅ {member.display_name} susturuldu ({duration_str}).")
        except Exception as e:
            await ctx.send(f"Hata: {e}")

    @commands.command(name="cekban")
    @is_bot_owner()
    async def cekban(self, ctx, member: discord.Member, *, reason="cek tarafından banlandı"):
        """Kullanıcıyı sunucudan yasaklar (Ban)."""
        await member.ban(reason=reason)
        await ctx.send(f"✅ {member.display_name} yasaklandı.")

    @commands.command(name="cekkick")
    @is_bot_owner()
    async def cekkick(self, ctx, member: discord.Member, *, reason="cek tarafından atıldı"):
        """Kullanıcıyı sunucudan atar (Kick)."""
        await member.kick(reason=reason)
        await ctx.send(f"✅ {member.display_name} atıldı.")

    @commands.command(name="cekrolver")
    @is_bot_owner()
    async def cekrolver(self, ctx, member: discord.Member, role: discord.Role):
        """Kullanıcıya belirtilen rolü verir."""
        if role in member.roles:
            await ctx.send(f"Zaten {role.name} rolüne sahip.")
        else:
            await member.add_roles(role)
            await ctx.send(f"✅ {role.name} rolü verildi.")

    @commands.command(name="cekrolal")
    @is_bot_owner()
    async def cekrolal(self, ctx, member: discord.Member, role: discord.Role):
        """Kullanıcıdan belirtilen rolü alır."""
        if role not in member.roles:
            await ctx.send(f"Zaten {role.name} rolüne sahip değil.")
        else:
            await member.remove_roles(role)
            await ctx.send(f"✅ {role.name} rolü alındı.")

    @commands.command(name="temizle")
    @is_bot_owner()
    async def temizle(self, ctx, channel: discord.TextChannel, limit: int):
        """Belirtilen kanaldaki mesajları siler."""
        if limit > 2000: return await ctx.send("Limit 2000'den fazla olamaz.")
        deleted = await channel.purge(limit=limit)
        await ctx.send(f"✅ {len(deleted)} mesaj silindi.", delete_after=5)

async def setup(bot):
    await bot.add_cog(Moderation(bot))
