import discord
from discord.ext import commands
import logging
import os
import pytz
import random
from datetime import datetime

log = logging.getLogger(__name__)

class General(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.admin_command_channel_id = int(os.getenv('ADMIN_COMMAND_CHANNEL_ID', 0))
        self.announcement_channel_id = int(os.getenv('ANNOUNCEMENT_CHANNEL_ID', 0))
        self.event_counter_channel_id = int(os.getenv('EVENT_COUNTER_CHANNEL_ID', 0))

    @commands.command()
    @commands.guild_only()
    async def link(self, ctx):
        """
        Sosyal medya linklerini paylaşan komut.
        Kullanım: !link
        """

        uyeolma_link = "https://sks.nisantasi.edu.tr/uye-talep"
        instagram_link = "https://www.instagram.com/nishdott"
        tiktok_link = "https://www.tiktok.com/@nishdott"
        linkedin_link = "https://www.linkedin.com/company/nishdot/about"
        whatsapp_link = "https://chat.whatsapp.com/DiufgZg3t1C2a4Y5L4iOLi"
        discord_link = "https://discord.com/invite/fch8HnsKwE"
        youtube_link = "https://www.youtube.com/@nishdot"

        embed = discord.Embed(
            title="📱 Nishdot Sosyal Medya ve İletişim",
            description="Kulübümüze ait tüm resmi hesaplara ve üyelik formuna aşağıdan ulaşabilirsiniz.",
            color=discord.Color.orange() 
        )

        embed.add_field(
            name="📝 Üyelik",
            value=f"Kulübümüze resmen üye olmak için:\n👉 **[Başvuru Formuna Git]({uyeolma_link})**",
            inline=False
        )
        embed.add_field(
            name="🌐 Sosyal Medya",
            value=f"📸 **[Instagram]({instagram_link})**\n"
                  f"🎵 **[TikTok]({tiktok_link})**\n"
                  f"💼 **[LinkedIn]({linkedin_link})**\n"
                  f"▶️ **[YouTube]({youtube_link})**",
            inline=True
        )
        embed.add_field(
            name="💬 İletişim & Topluluk",
            value=f"📞 **[WhatsApp]({whatsapp_link})**\n"
                  f"👾 **[Discord]({discord_link})**",
            inline=True
        )

        embed.set_footer(text=f"{ctx.guild.name} Linkler")
        
        await ctx.send(embed=embed)

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

    @commands.command(name="yardim", aliases=["help", "komutlar", "komut","kodlar","yardım"])
    @commands.guild_only()
    async def yardim(self, ctx):
        """
        Botun komutlarını listeleyen yardım menüsü.
        Kullanım: !yardim
        """
        
        embed = discord.Embed(
            title="🤖 Tonishbot Komutları",
            description="Tonishbot ile kullanabileceğiniz tüm temel komutlar aşağıda listelenmiştir.",
            color=discord.Color.blue()
        )
        embed.add_field(
            name="🤖 @Tonish",
            value="Tonish'in yapay zekası ile konuşmak ve onunla etkileşime geçmek için @Tonish yazarak onu etiketleyip sohbet edebilirsiniz.",
            inline=False
        )
        embed.add_field(
            name="📱 !link",
            value="Nishdot'un tüm hesaplarına ulaşmak için kullanabileceğiniz komut.",
            inline=False
        )
        embed.add_field(
            name="🎰 !oyun",
            value="Tonishbot üzerinden oynayıp sunucunun sanal ekonomisine dahil olabileceğiniz eğlenceli oyunları görebileceğiniz komut.",
            inline=False
        )
        embed.add_field(
            name="💸 !ekonomi",
            value="Tonishbot üzerinden sunucumuzda oynadığınız oyunlar ile kazandığınız coinleri ve liderlik tablosunu görebileceğiniz komut.",
            inline=False
        )
        embed.add_field(
            name="👨‍💼👩‍💼 !yk",
            value="Nishdot yönetim kurulunu görüntülemek için kullanabileceğiniz komut.",
            inline=False
        )
        embed.add_field(
            name="🖤 !steam",
            value="Tonish'in Steam entegrasyonu ile kullanabileceğiniz havalı komutlar.",
            inline=False
        )
        embed.add_field(
            name="💭 !oyunfikri",
            value="'Ne yapsak?' diye düşündüğünüzde ya da sadece ufak fikirler üretmek istediğinizde size binlerce farklı kombinasyonla oyun fikri üretebileceğiniz bir makine yaratır.",
            inline=False
        )
        embed.add_field(
            name="🎮 !benzeroner [oyun adı]",
            value="Tonish bahsettiğiniz oyunu baz alarak size oynayabileceğiniz 3 adet farklı oyun önerir.",
            inline=False
        )
        embed.add_field(
            name="💬 !sor [soru]",
            value="Tonish'e doğrudan soru sorarsınız. `!sohbetisifirla` ile aranızdaki sohbet geçmişini silebilirsiniz.",
            inline=False
        )
        embed.add_field(
            name="ℹ️ !bilgi",
            value="Nishdot'un ne olduğunu ve ne yaptığını anlatan komut.",
            inline=False
        )

        embed.set_footer(text=f"{ctx.guild.name} Yardım Menüsü")
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def oyun(self, ctx):
        """
        Tonishbot üzerinden oynanan oyunların bilgisini veren komut"""

        embed = discord.Embed(
            title="🎮Oyun Komutları🕹️",
            description="Tonish üzerinden oyun oynarak Tonishcoin kazanabileceğiniz ve sunucu ekonomisine katılabileceğiniz komutlar.",
            color=discord.Color.pink()
        )
        
        embed.add_field(
            name="!blackjack ya da !bj",
            value="♠️Blackjack oynayabileceğiniz komut.",
            inline=False
        )
        embed.add_field(
            name="!slot",
            value="🎰Bir slot makinesi yaratıp slot oynayabileceğiniz komut.",
            inline=False
        )
        embed.add_field(
            name="!hacker (veya !sistemkirici)",
            value="🔒Hacker oyunu oynayarak kilitli kasanın içindeki tonishcoini alabileceğiniz oyun.\n"
                  "`!tahmin 12345` ile tahmin yapar, `!vazgec` ile görevden çıkarsınız.",
            inline=False
        )
        embed.add_field(
            name="!zindan",
            value="🐲Zindanlardaki düşmanları öldürerek ödül kazanabileceğiniz D&D benzeri oyun.",
            inline=False
        )
        embed.add_field(
            name="!bilmece",
            value="🎮Oyunlarla emoji bilmece oyunu oynayarak tonishcoini kazanabileceğiniz oyun.",
            inline=False
        )
        embed.add_field(
            name="!ekonomi",
            value="💰Sunucudaki ekonomi sistemi hakkında bilgi alabileceğiniz komut.",
            inline=False
        )
        embed.set_footer(text=f"{ctx.guild.name} Oyun Sistemi")
        await ctx.send(embed=embed)

    @commands.command(name="ekonomi", aliases=["eco","economi","liderlikbilgi","ekonomibilgi"])
    @commands.guild_only()
    async def ekonomi(self, ctx):
        """Ekonomi sistemiyle ilgili temel komutları listeler."""
        
        embed = discord.Embed(
            title="💰 Ekonomi Komutları 💰",
            description="Sunucudaki tonish coin sistemini yönetmek ve kullanmak için gereken tüm komutlar:",
            color=discord.Color.green()
        )
        embed.add_field(
            name="!bakiye (veya !tonishcoin, !cuzdan)",
            value="Kendi bakiyeni veya etiketlediğin birinin bakiyesini kontrol edersin.\n"
                "**Kullanım:** `!bakiye` veya `!bakiye @kullanıcı`",
            inline=False
        )       
        embed.add_field(
            name="!gunluk",
            value="Her 24 saatte bir **50 tonish coin** hediye almanı sağlar. \n"
                "Günün ödülünü almayı unutma!",
            inline=False
        )    
        embed.add_field(
            name="!liderlik (veya !top, !zenginler, !leaderboard)",
            value="Sunucudaki en zengin 5 kişinin görsel liderlik tablosunu gösterir. \n"
                "Her ayın 1'inde bu tablo sıfırlanır ve o ayın kazananlarına sürpriz ödüller verilir. ",
            inline=False
        )    
        embed.add_field(
            name="Oyun Oynamak İster misin?",
            value="Blackjack ve Slot oyunlarının kurallarını öğrenmek için `!oyun` komutunu kullanabilirsin.",
            inline=False
        )
        
        embed.set_footer(text=f"{ctx.guild.name} Ekonomi Sistemi")
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def steam(self, ctx):
        """Tonish'in Steam entegrasyonu komutlarını listeler."""

        embed = discord.Embed(
            title="🎮 Steam Entegrasyon Komutları 🎮",
            description="Tonish ile Steam hesabınızı bağlayarak kullanabileceğiniz sosyal ve analitik komutlar.",
            color=0x1b2838 
        )
        embed.add_field(
            name="**‼️ Önemli Not ‼️**",
            value="Steam hesabınızı eşleştirebilmek için gizlilik ayarlarınızdaki **'Oyun Detayları'** ve **'Envanter'** kısımlarının **herkese açık** olması gerekmektedir.\n`Steam` > `Ayarlar` > `Gizlilik Ayarları` kısmından güncelleyebilirsiniz.",
            inline=False
            )
        embed.add_field(
            name="!steam_bagla",
            value="⛓️ Steam hesabınızı Tonish ile eşleştirmek için kullanılır.\n**Örnek:** `!steam_bagla https://steamcommunity.com/id/kullaniciadi` veya `!steam_bagla 76561198000000000` (Tip:Steam profilinize girdikten sonra üst kısımda gözüken bağlantının üzerine tıklayarak linkinizi alabilirsiniz.)",
            inline=False
            )
        embed.add_field(
            name="!oyunsuresi",
            value="🕧 Sunucudaki kullanıcıların son 2 haftada toplam Steam'de oynadıkları oyun süresini listeler.",
            inline=False
            )
        embed.add_field(
            name="!ortak",
            value="👥 Etiketlediğiniz kullanıcının Steam hesabı ile sizin hesabınızdaki ortak oyunlar arasından rastgele bir oyun önerir.\n**Örnek:** `!ortak @kullanici`",
            inline=False
            )
        embed.add_field(
            name="!kimoyunda",
            value="🟢 Sunucuda profilini eşlemiş kullanıcıların anlık olarak hangi oyunda olduğunu listeler.",
            inline=False
            )

        embed.add_field(
            name="!kart",
            value="🪪 Steam hesabınızı analiz edip oyuncu profilinize göre size görsel bir Gamer Kart oluşturur.",
            inline=False
            )

        embed.add_field(
            name="!analiz",
            value="🧬 Steam hesabınızı analiz edip oyun zevkinize göre bir Gamer DNA grafiği oluşturur.",
            inline=False
            )

        embed.add_field(
            name="!sunucu-istatistik",
            value="📊 Steam hesabını bağlamış tüm üyelerin toplam oyun süresini, en popüler oyunu ve sunucunun favori türünü gösterir.",
            inline=False
            )

        embed.set_footer(text=f"{ctx.guild.name} Steam Sistemi")
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def yk(self, ctx):
        """
        Nishdot yönetim kurulu listesini gösterir.
        Kullanım: !yk
        """
        
        embed = discord.Embed(
            title="👔 Nishdot Yönetim Kurulu",
            description="Kulübümüzün idari, yönetim ve etkinlik kadrosu aşağıdadır.",
            color=discord.Color.dark_gold() 
        )

        embed.add_field(
            name="👑 Başkan",
            value="Yurdakul Efe Arıkan",
            inline=True
        )
        
        embed.add_field(
            name="🤝 Başkan Yardımcısı",
            value="Ömer Soysal",
            inline=True
        )

        embed.add_field(
            name="🏛️ Yönetim Kurulu Üyeleri",
            value="Yurdakul Efe Arıkan\nÖmer Soysal\nMehmet Boran Bulut\nEbru Karademir\nOğulcan Danişment",
            inline=False
        )

        embed.add_field(
            name="📅 Organizasyon Koordinatörü",
            value="İbrahim Ata Gültekin",
            inline=True
        )

        embed.add_field(
            name="🌍 Dış İlişkiler Koordinatörü",
            value="Kerem Çetin",
            inline=True
        )

        embed.add_field(
            name="📱 Sosyal Medya Koordinatörü",
            value="Muhammed Alper Kuvar",
            inline=True
        )

        embed.add_field(
            name="💰 Sponsorluk Sorumlusu",
            value="Kaan Mersin",
            inline=True
        )

        embed.add_field(
            name="📣 İletişim Sorumlusu",
            value="Ömer Çelik",
            inline=True
        )

        embed.add_field(
            name="👾 Game Jam Sorumlusu",
            value="Oğulcan Danişment",
            inline=True
        )

        embed.add_field(
            name="🛠️ Workshop Sorumlusu",
            value="Yağmur Güven\nYaren Er",
            inline=True
        )

        embed.add_field(
            name="🎨 Tasarımcı - Editör",
            value="Beyzanur Boduroğlu\nYusuf Dervent",
            inline=True
        )

        embed.add_field(
            name="✍️ İçerik Üreticisi",
            value="Ebru Karademir",
            inline=True
        )

        embed.add_field(
            name="🎥 Kameraman",
            value="Feyzanur Sarı",
            inline=True
        )

        embed.add_field(
            name="💬 Discord Sorumlusu",
            value="Yusuf Dervent",
            inline=True
        )
        embed.add_field(
            name="🎉 Etkinlik Görevlileri",
            value="Bahadır Bildiren\nSudenaz Çolak\nYusuf Çınar Üstal",
            inline=False
        )

        embed.set_footer(text=f"{ctx.guild.name} Yönetim Kadrosu")
        
        await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
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
            await ctx.send("Duyuru kanalı bulunamadı.")
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
            # Bot varsayılan olarak @everyone/rol etiketlerini engelliyor;
            # duyuru bilinçli olarak ping attığı için burada açıkça izin veriyoruz.
            await target_channel.send(
                content=ping_content,
                embed=embed,
                allowed_mentions=discord.AllowedMentions(everyone=True, roles=True, users=True),
            )
            await ctx.send("✅ Duyurun başarıyla gönderildi.", delete_after=10)
            await ctx.message.delete()
        except discord.Forbidden:
            log.warning("Duyuru gönderilemedi, yetki yetersiz (channel_id=%s)", self.announcement_channel_id)
            await ctx.send("Duyuru kanalına yazma yetkim yok. Kanal izinlerini kontrol et.")
        except discord.HTTPException:
            log.exception("Duyuru gönderilemedi (channel_id=%s)", self.announcement_channel_id)
            await ctx.send("Duyuru gönderilirken bir sorun oldu, tekrar dene.")

    @commands.command()
    @commands.guild_only()
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
            await ctx.send("Etkinlik kanalı bulunamadı.")
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

        try:
            await target_channel.send(embed=embed)
        except discord.Forbidden:
            log.warning("Etkinlik sayacı gönderilemedi, yetki yetersiz (channel_id=%s)", self.event_counter_channel_id)
            return await ctx.send("Etkinlik kanalına yazma yetkim yok. Kanal izinlerini kontrol et.")
        except discord.HTTPException:
            log.exception("Etkinlik sayacı gönderilemedi (channel_id=%s)", self.event_counter_channel_id)
            return await ctx.send("Etkinlik sayacı gönderilirken bir sorun oldu, tekrar dene.")

        await ctx.send("✅ Etkinlik sayacı gönderildi.", delete_after=10)
        try:
            await ctx.message.delete()
        except discord.HTTPException:
            pass

    @commands.command(name="oyunfikri", aliases=["gameidea"])
    async def oyunfikri(self, ctx):
        """
        Oyun geliştiriciler için rastgele oyun fikri üretir.
        Tür, Tema ve Kısıtlama kombinasyonları sunar.
        """
        view = GameIdeaView(ctx.author)
        embed = view.generate_embed()
        await ctx.send(embed=embed, view=view)

class GameIdeaView(discord.ui.View):
    def __init__(self, author):
        super().__init__(timeout=600) 
        self.author = author
        
        # Veri Listeleri
        self.genres = [
            "Platformer", "RPG", "Bulmaca (Puzzle)", "Strateji", "Hayatta Kalma (Survival)", 
            "Korku", "Gizlilik (Stealth)", "Ritim Oyunu", "Metroidvania", "Roguelike", 
            "Görsel Roman", "FPS", "Kart Oyunu", "Tower Defense","Spor","Building","Casual","Tamamen Serbest","Hack & Slash", 
            "Point & Click Macera", "Dungeon Crawler", "Bullet Hell", "Tycoon / İşletme", "Idle / Clicker", 
            "Sanal Bebek (Tamagotchi tarzı)", "Dating Sim (Flört Simülasyonu)", 
            "Battle Royale", "Endless Runner (Sonsuz Koşu)", "Text Adventure (Metin Tabanlı)", 
            "Party Game", "Zanaat / Crafting Odaklı", "Yarış (Racing)", "Müzik/Ritim"
        ]
        
        self.themes = [
            "Siberpunk İstanbul", "Terk edilmiş uzay istasyonu", "Orta çağ panayırı", 
            "Su altı şehri", "Rüyalar alemi", "Vahşi Batı", "Kıyamet sonrası", 
            "Oyuncak dünyası", "Antik Mısır", "Hacker dünyası", "Korsan gemisi",
            "Büyülü orman", "Distopik gelecek", "Noir dedektiflik", "Kırmızı evren","Renkler Yok",
            "1900's","1800's","Antik Yunanistan","Distopya","Ütopya","İstanbul","Ankara","Osmanlı",
            "Tamamen serbest","Kapadokya Peri Bacaları", "Kapalıçarşı'nın Dehlizleri", "Karadeniz Yaylaları", 
            "90'lar Türkiye'si", "Ege Kasabası","Mars Kolonisi", "Yapay Zeka'nın Zihni", "Dev Bir Canavarın İçi", 
            "Bulutların Üzerindeki Krallık", "Yeraltı Metro Tünelleri", "Solarpunk (Doğa ile teknoloji iç içe)",
            "Zamanın Donduğu Şehir", "Sonsuz Kütüphane", "Terk Edilmiş Lunapark","Steampunk Laboratuvar", "Lovecraftian (Kozmik Korku)", "Neon Noir",
            "Piksel Piksel Bozulmuş Dünya (Glitch World)", "Oyuncak Ev", "Kar Küresi İçi"
        ]
        
        self.constraints = [
            "Zıplamak yok", "Sadece tek tuş kullanılabilir", "Zaman sadece sen hareket edince akar", 
            "Düşmanları öldüremezsin, onlarla dost olmalısın", "Her şey yok edilebilir", 
            "Siyah-beyaz grafikler", "Metin yok (sadece semboller)", "Sesler görselleştirilmeli", 
            "Can barın yok (tek vuruşta ölürsün)", "Envanterin sadece 1 eşya alabilir",
            "Karanlıkta göremiyorsun", "Yer çekimi sürekli değişiyor", "Tamamen Serbest",
            "Sağlık barı yok (Canın kıyafetin/zırhın kadardır)",
            "Düşmanlar senin hareketlerini taklit eder", 
            "Sürekli kan kaybediyorsun (Zaman sınırı)", 
            "Yerçekimi yok (Sıfır yerçekimi)", 
            "Sadece fare (mouse) ile oynanabilir", 
            "HUD (Arayüz) hiç yok", 
            "Dost ateşi (Friendly Fire) her zaman açık","Karakterin görünmez ama ses çıkarıyor", 
            "Karakterin bir eşya (Canlı değil)", 
            "Karakter sürekli yaşlanıyor","Oyunun sonundan başına doğru ilerliyor", 
            "Dünya sadece müzik ritmine göre hareket ediyor", 
            "Grafikler ASCII (Yazı karakterleri) sanatından oluşmalı",
            "Ekran sürekli dönüyor","Renkler duygulara göre değişmeli"
        ]

    def generate_embed(self):
        genre = random.choice(self.genres)
        theme = random.choice(self.themes)
        constraint = random.choice(self.constraints)
        
        embed = discord.Embed(
            title="🎲 Rastgele Oyun Fikri",
            color=discord.Color.random()
        )
        
        embed.add_field(name="🕹️ Tür", value=genre, inline=False)
        embed.add_field(name="🌍 Tema", value=theme, inline=False)
        embed.add_field(name="⚠️ Kısıtlama", value=constraint, inline=False)
        
        embed.set_footer(text="Hadi bu fikri 5 dakikada beyin fırtınası yapın!")
        return embed

    @discord.ui.button(label="Yeni Fikir 🎲", style=discord.ButtonStyle.primary)
    async def regenerate(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.author.id:
            return await interaction.response.send_message("Bu makineyi sadece komutu yazan kişi kullanabilir! Kendi fikrini üretmek için `!oyunfikri` yaz.", ephemeral=True)
        
        embed = self.generate_embed()
        await interaction.response.edit_message(embed=embed, view=self)

# Botun bu eklentiyi yüklemesi için gereken fonksiyon
async def setup(bot):
    await bot.add_cog(General(bot))
