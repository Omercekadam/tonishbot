import discord
from discord.ext import commands
import os
import pytz
from datetime import datetime

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        # Kanal ID'lerini ortam değişkenlerinden alıyoruz
        self.admin_command_channel_id = int(os.getenv('ADMIN_COMMAND_CHANNEL_ID', 0))
        self.announcement_channel_id = int(os.getenv('ANNOUNCEMENT_CHANNEL_ID', 0))
        self.event_counter_channel_id = int(os.getenv('EVENT_COUNTER_CHANNEL_ID', 0))

    @commands.command()
    async def link(self, ctx):
        """
        Sosyal medya linklerini paylaşan komut.
        Kullanım: !link
        """
        # Linkleri değişkenlere ata
        uyeolma_link = "https://sks.nisantasi.edu.tr/uye-talep"
        instagram_link = "https://www.instagram.com/nishdott"
        linkedin_link = "https://www.linkedin.com/company/nishdot/about"
        whatsapp_link = "https://chat.whatsapp.com/DiufgZg3t1C2a4Y5L4iOLi"
        discord_link = "https://discord.gg/ddumxQaG"

        # Mesaj içeriğini oluştur
        message_content = (
            f"**Sosyal medya hesaplarımız:**\n\n"
            f"**Kulübümüze üye olmak için:** <{uyeolma_link}>\n"
            f"**İnstagram:** <{instagram_link}>\n"
            f"**Whatsapp:** <{whatsapp_link}>\n"
            f"**Linkedin:** <{linkedin_link}>\n"
            f"**Discord:** <{discord_link}>\n"
        )
        await ctx.send(message_content)

    @commands.command()
    async def bilgi(self, ctx):
        """
        Kulüp hakkında genel bilgi veren komut.
        Kullanım: !bilgi
        """
        message_content = (
            "İstanbul Nişantaşı Üniversitesi Dijital Oyun Tasarımı Kulübü yani kısaca **Nishdot**,\n "
            "Oyun geliştirmeyi, oyun tasarlamayı ve bu süreçte ekip çalışmasını öğrenmek isteyen herkes için kuruldu. "
            "Amacımız; fikirlerinizi hayata geçirebileceğiniz, yeni beceriler kazanabileceğiniz ve oyun dünyasına adım atabileceğiniz bir topluluk oluşturmak. "
            "Burada birlikte öğreniyor, üretiyor ve oyunların arkasındaki yaratıcı süreci keşfediyoruz!\n"
            "Sunucu botumuz tonish ile etkileşime geçmek için '!yardim' yazarak bilgi alabilirsiniz."
        )
        await ctx.send(message_content)

    @commands.command()
    async def yardim(self, ctx):
        """
        Botun komutlarını listeleyen yardım menüsü.
        Kullanım: !yardim
        """
        message_content = (
            "**Tonishbot Komutları:**\n\n"
            "**!link:**\n📱Nishdot'un tüm hesaplarına ulaşmak için kullanabileceğiniz komut.\n\n"
            "**!oyun:**\n🎰Tonishbot üzerinden oynayıp sunucunun sanal ekonomisine dahil olabileceğiniz eğlenceli oyunları görebileceğiniz komut.\n\n"
            "**!ekonomi:**\n💸Tonishbot üzerinden sunucumuzda oynadığınız oyunlar ile kazandığınız coinleri ve liderlik tablosunu görebileceğiniz komut.\n\n" 
            "**!yk:**\n👨‍💼👩‍💼Nishdot yönetim kurulunu görüntülemek için kullanabileceğiniz komut.\n\n"
        )
        await ctx.send(message_content)

    @commands.command()
    async def yk(self, ctx):
        """
        Yönetim kurulu listesini gösterir.
        Kullanım: !yk
        """
        message_content = (
            "**Nishdot Yönetim Kurulu:**\n\n\n"
            "**Başkan:** \nYurdakul Efe Arıkan\n\n"
            "**Başkan Vekili:** \nMehmet Boran Bulut\n\n"
            "**Başkan Yardımcısı:** \nÖmer Soysal\n\n"
            "**Genel Sekreter:** \nEbru Karademir\n\n"
            "**Organizasyon Sorumlusu:** \nOğulcan Danişment\n\n"
            "**Sosyal Medya Koordinatörü:** \nFeyzanur Sarı\n\n"
            "**Etkinlik Sorumlusu:** \nKaan Mersin\nKerem Çetin\n\n"
        )
        await ctx.send(message_content)

    @commands.command()
    @commands.has_permissions(administrator=True) 
    async def duyuru(self, ctx, *, message: str):
        """
        Belirlenen duyuru kanalına gömülü (embed) mesaj gönderir.
        Sadece yöneticiler kullanabilir.
        Kullanım: !duyuru @everyone Mesajınız...
        """
        # Sadece admin komut kanalında çalışsın
        if ctx.channel.id != self.admin_command_channel_id:
            try:
                await ctx.send(f"Duyuru komutu sadece <#{self.admin_command_channel_id}> kanalında kullanılabilir.", delete_after=10)
                await ctx.message.delete(delay=10)
            except: pass
            return

        target_channel = self.bot.get_channel(self.announcement_channel_id)
        if not target_channel:
            await ctx.send("Duyuru kanalı bulunamadı.", ephemeral=True)
            return
        
        ping_content = None         
        description_content = message 

        # Etiketleri (ping) mesajdan ayır
        if message.startswith("<@&"):
            end_index = message.find('>')
            if end_index != -1:
                ping_content = message[:end_index+1]
                description_content = message[end_index+1:].lstrip() 
        elif message.startswith("@everyone"):
            ping_content = "@everyone"
            description_content = message.replace("@everyone", "", 1).lstrip()
        elif message.startswith("@here"):
            ping_content = "@here"
            description_content = message.replace("@here", "", 1).lstrip()

        # Embed oluştur
        embed = discord.Embed(
            title="📣 Yeni Duyuru!",
            description=description_content,   
            color=0xFFEA00
        )
        
        # Duyuruyu yapan kişinin bilgileri
        if ctx.author.avatar:
            embed.set_author(name=f"Duyuran: {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
        else:
            embed.set_author(name=f"Duyuran: {ctx.author.display_name}")

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url)
        
        if self.bot.user.avatar:
            embed.set_footer(text=f"{ctx.guild.name} | TonishBot", icon_url=self.bot.user.avatar.url)
        else:
            embed.set_footer(text=f"{ctx.guild.name} | TonishBot")
            
        embed.timestamp = discord.utils.utcnow()
        
        try:
            await target_channel.send(content=ping_content, embed=embed)
            await ctx.send("✅ Duyurun başarıyla gönderildi.", ephemeral=True, delete_after=10)
            await ctx.message.delete()
        except Exception as e:
            await ctx.send(f"Hata: {e}")

    @commands.command()
    @commands.has_permissions(administrator=True)
    async def etkinliksayaci(self, ctx, tarih_str: str, saat_str: str, etkinlik_adi: str, *, aciklama: str):
        """
        Etkinlikler için geri sayım sayacı oluşturur.
        Kullanım: !etkinliksayaci "28.10.2025" "19:00" "Başlık" "Açıklama"
        """
        if ctx.channel.id != self.admin_command_channel_id:
            await ctx.send(f"Bu komut sadece <#{self.admin_command_channel_id}> kanalında kullanılabilir.", delete_after=10)
            await ctx.message.delete(delay=10)
            return

        target_channel = self.bot.get_channel(self.event_counter_channel_id)
        if not target_channel:
            await ctx.send("Etkinlik kanalı bulunamadı.", ephemeral=True)
            return

        try:
            # Zaman dilimi ayarlaması (Türkiye Saati)
            turkey_tz = pytz.timezone("Europe/Istanbul")
            dt_str = f"{tarih_str} {saat_str}"
            local_dt = datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
            aware_dt = turkey_tz.localize(local_dt)
            timestamp_unix = int(aware_dt.timestamp())
        except ValueError:
            await ctx.send("Hata: Tarih formatı yanlış. Örnek: `!etkinliksayaci \"28.10.2025\" \"19:00\" ...`", delete_after=20)
            return

        embed = discord.Embed(
            title=f"🗓️ {etkinlik_adi}", 
            description=aciklama,  
            color=0xeb596d 
        )
        # Discord'un timestamp formatını kullanarak dinamik zaman gösterimi
        embed.add_field(name="Etkinlik Zamanı", value=f"<t:{timestamp_unix}:F>", inline=False)
        embed.add_field(name="Kalan Süre", value=f"<t:{timestamp_unix}:R>", inline=False)

        if ctx.guild.icon:
            embed.set_thumbnail(url=ctx.guild.icon.url) 
        
        embed.set_footer(text=f"{ctx.guild.name} Etkinlik Takvimi")
        embed.timestamp = discord.utils.utcnow()

        await target_channel.send(embed=embed)
        await ctx.send("✅ Etkinlik sayacı gönderildi.", ephemeral=True, delete_after=10)
        await ctx.message.delete()

# Botun bu eklentiyi yüklemesi için gereken fonksiyon
async def setup(bot):
    await bot.add_cog(General(bot))
