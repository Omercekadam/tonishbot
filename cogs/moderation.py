import discord
from discord.ext import commands
from datetime import timedelta
import logging

log = logging.getLogger(__name__)

# Discord'un timeout üst sınırı 28 gündür
MAX_TIMEOUT = timedelta(days=28)

# Tek seferde silinebilecek en fazla mesaj
MAX_PURGE = 2000


def is_bot_owner():
    """
    Özel yetki kontrolü dekoratörü.
    Sadece bot sahibi (CEK_DISCORD_ID) komutu kullanabilir.
    """
    async def predicate(ctx):
        if not ctx.bot.cek_id or ctx.author.id != ctx.bot.cek_id:
            raise commands.CheckFailure("Bu komutu sadece bot sahibi kullanabilir.")
        return True
    return commands.check(predicate)


def parse_duration(duration_str: str) -> timedelta:
    """
    Süre stringini (örn: 10m, 1h) timedelta objesine çevirir.
    s: saniye, m: dakika, h: saat, d: gün
    """
    if not duration_str or len(duration_str) < 2:
        raise ValueError("Süre boş veya çok kısa")

    unit = duration_str[-1].lower()
    try:
        amount = int(duration_str[:-1])
    except ValueError:
        raise ValueError(f"'{duration_str[:-1]}' bir sayı değil")

    if amount <= 0:
        raise ValueError("Süre 0'dan büyük olmalı")

    birimler = {'s': 'seconds', 'm': 'minutes', 'h': 'hours', 'd': 'days'}
    if unit not in birimler:
        raise ValueError(f"Geçersiz birim '{unit}' — s/m/h/d kullan")

    return timedelta(**{birimler[unit]: amount})


class Moderation(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    @commands.command(name="cektimeout")
    @commands.guild_only()
    @is_bot_owner()
    async def cektimeout(self, ctx, member: discord.Member, duration_str: str, *, reason="cek tarafından susturuldu"):
        """Kullanıcıya zaman aşımı (timeout) uygular. Örnek: !cektimeout @kisi 10m"""
        try:
            duration = parse_duration(duration_str)
        except ValueError as e:
            return await ctx.send(f"⚠️ Süre hatalı: {e}\n**Örnek:** `!cektimeout @kisi 10m`")

        if duration > MAX_TIMEOUT:
            return await ctx.send("⚠️ Discord en fazla **28 gün** timeout'a izin veriyor.")

        try:
            await member.timeout(duration, reason=reason)
        except discord.Forbidden:
            return await ctx.send(f"⚠️ {member.display_name} kullanıcısını susturamam — rolü benden yüksek veya yetkim yok.")
        except discord.HTTPException:
            log.exception("Timeout uygulanamadı (user_id=%s)", member.id)
            return await ctx.send("Timeout uygulanırken bir sorun oldu, tekrar dene.")

        await ctx.send(f"✅ {member.display_name} susturuldu ({duration_str}).")

    @commands.command(name="cekban")
    @commands.guild_only()
    @is_bot_owner()
    async def cekban(self, ctx, member: discord.Member, *, reason="cek tarafından banlandı"):
        """Kullanıcıyı sunucudan yasaklar (Ban)."""
        try:
            await member.ban(reason=reason)
        except discord.Forbidden:
            return await ctx.send(f"⚠️ {member.display_name} yasaklanamadı — rolü benden yüksek veya ban yetkim yok.")
        except discord.HTTPException:
            log.exception("Ban başarısız (user_id=%s)", member.id)
            return await ctx.send("Yasaklama sırasında bir sorun oldu, tekrar dene.")

        await ctx.send(f"✅ {member.display_name} yasaklandı.")

    @commands.command(name="cekkick")
    @commands.guild_only()
    @is_bot_owner()
    async def cekkick(self, ctx, member: discord.Member, *, reason="cek tarafından atıldı"):
        """Kullanıcıyı sunucudan atar (Kick)."""
        try:
            await member.kick(reason=reason)
        except discord.Forbidden:
            return await ctx.send(f"⚠️ {member.display_name} atılamadı — rolü benden yüksek veya kick yetkim yok.")
        except discord.HTTPException:
            log.exception("Kick başarısız (user_id=%s)", member.id)
            return await ctx.send("Atma işlemi sırasında bir sorun oldu, tekrar dene.")

        await ctx.send(f"✅ {member.display_name} atıldı.")

    @commands.command(name="cekrolver")
    @commands.guild_only()
    @is_bot_owner()
    async def cekrolver(self, ctx, member: discord.Member, role: discord.Role):
        """Kullanıcıya belirtilen rolü verir."""
        if role in member.roles:
            return await ctx.send(f"Zaten {role.name} rolüne sahip.")

        try:
            await member.add_roles(role, reason=f"{ctx.author} tarafından verildi")
        except discord.Forbidden:
            return await ctx.send(f"⚠️ {role.name} rolünü veremem — rol benden yüksek veya yetkim yok.")
        except discord.HTTPException:
            log.exception("Rol verilemedi (user_id=%s, role_id=%s)", member.id, role.id)
            return await ctx.send("Rol verilirken bir sorun oldu, tekrar dene.")

        await ctx.send(f"✅ {role.name} rolü verildi.")

    @commands.command(name="cekrolal")
    @commands.guild_only()
    @is_bot_owner()
    async def cekrolal(self, ctx, member: discord.Member, role: discord.Role):
        """Kullanıcıdan belirtilen rolü alır."""
        if role not in member.roles:
            return await ctx.send(f"Zaten {role.name} rolüne sahip değil.")

        try:
            await member.remove_roles(role, reason=f"{ctx.author} tarafından alındı")
        except discord.Forbidden:
            return await ctx.send(f"⚠️ {role.name} rolünü alamam — rol benden yüksek veya yetkim yok.")
        except discord.HTTPException:
            log.exception("Rol alınamadı (user_id=%s, role_id=%s)", member.id, role.id)
            return await ctx.send("Rol alınırken bir sorun oldu, tekrar dene.")

        await ctx.send(f"✅ {role.name} rolü alındı.")

    @commands.command(name="temizle")
    @commands.guild_only()
    @is_bot_owner()
    async def temizle(self, ctx, channel: discord.TextChannel, limit: int):
        """Belirtilen kanaldaki mesajları siler."""
        if limit <= 0:
            return await ctx.send("Limit 0'dan büyük olmalı.")
        if limit > MAX_PURGE:
            return await ctx.send(f"Limit {MAX_PURGE}'den fazla olamaz.")

        try:
            deleted = await channel.purge(limit=limit)
        except discord.Forbidden:
            return await ctx.send(f"⚠️ {channel.mention} kanalında mesaj silme yetkim yok.")
        except discord.HTTPException:
            log.exception("Mesajlar silinemedi (channel_id=%s)", channel.id)
            return await ctx.send("Mesajlar silinirken bir sorun oldu. (14 günden eski mesajlar toplu silinemez.)")

        await ctx.send(f"✅ {len(deleted)} mesaj silindi.", delete_after=5)


async def setup(bot):
    await bot.add_cog(Moderation(bot))
