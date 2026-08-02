import discord
from discord.ext import commands
import aiosqlite
import contextlib
import logging
import os
import urllib.parse
import aiohttp
import json
import random
import io
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime

log = logging.getLogger(__name__)

DB_PATH = "steam.db"

# SQLite kilit bekleme süresi (saniye)
DB_TIMEOUT = 30

class Steam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.api_key = os.getenv('STEAM_API_KEY')
        self.session = None
        # appid -> [tür adı, ...]. Steam Store API'nin sıkı rate limit'i var
        # (~200 istek / 5 dk) ve oyun türleri neredeyse hiç değişmez.
        self.genre_cache = {}
        if not self.api_key:
            log.warning("STEAM_API_KEY bulunamadı! Steam komutları çalışmayacak.")

    async def cog_load(self):
        self.session = aiohttp.ClientSession()

        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute("""
                CREATE TABLE IF NOT EXISTS steam_users (
                    user_id INTEGER PRIMARY KEY,
                    steam_id TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
        log.info("Steam veritabanı hazır.")

    async def cog_unload(self):
        if self.session and not self.session.closed:
            await self.session.close()

    @contextlib.asynccontextmanager
    async def _session(self):
        """
        Paylaşılan aiohttp oturumunu verir.

        Eskiden her komut kendi ClientSession'ını açıp kapatıyordu; bu her seferinde
        yeni TCP/TLS el sıkışması demekti. Tek oturum bağlantıları yeniden kullanır.
        """
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        yield self.session

    async def fetch_genres(self, appid) -> list:
        """Bir oyunun türlerini getirir; sonuç bellekte cache'lenir."""
        if appid in self.genre_cache:
            return self.genre_cache[appid]

        store_url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=turkish"
        turler = []
        try:
            async with self._session() as session:
                async with session.get(store_url) as response:
                    if response.status == 200:
                        store_data = await response.json()
                        anahtar = str(appid)
                        if store_data and anahtar in store_data and store_data[anahtar].get('success'):
                            turler = [
                                g['description']
                                for g in store_data[anahtar]['data'].get('genres', [])
                            ]
                    elif response.status == 429:
                        # Rate limit — cache'leme, bir sonraki sefere tekrar denensin
                        log.warning("Steam Store API rate limit (appid=%s)", appid)
                        return []
        except (aiohttp.ClientError, ValueError):
            log.warning("Oyun türleri alınamadı (appid=%s)", appid)
            return []

        self.genre_cache[appid] = turler
        return turler

    async def count_genres(self, games) -> dict:
        """Oyun listesindeki türleri sayar."""
        genre_counts = {}
        for game in games:
            for tur in await self.fetch_genres(game['appid']):
                genre_counts[tur] = genre_counts.get(tur, 0) + 1
        return genre_counts

    async def resolve_steam_id(self, input_id):
        """
        Kullanıcı girdisini (URL, ID, Vanity URL) Steam 64 ID'ye çevirir.

        Desteklenen formatlar:
          76561198000000000
          https://steamcommunity.com/profiles/76561198000000000
          https://steamcommunity.com/id/kullaniciadi
        """
        if not input_id:
            return None

        # Sorgu parametrelerini ve sondaki eğik çizgileri at
        temiz = input_id.strip().split('?')[0].split('#')[0].strip('/')

        # Doğrudan 17 haneli Steam64 ID mi?
        if temiz.isdigit() and len(temiz) == 17:
            return temiz

        # URL ise son parçayı al (/profiles/<id> veya /id/<vanity>)
        son_parca = temiz.split('/')[-1]

        # /profiles/<id> formatı — vanity değil, direkt Steam64 ID
        if son_parca.isdigit() and len(son_parca) == 17:
            return son_parca

        # Geriye kalan: vanity URL (kullanıcı adı) — API'ye sor
        url = f"https://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={self.api_key}&vanityurl={son_parca}"
        try:
            async with self._session() as session:
                async with session.get(url) as response:
                    if response.status == 200:
                        data = await response.json()
                        if data.get('response', {}).get('success') == 1:
                            return data['response']['steamid']
        except aiohttp.ClientError:
            log.exception("Steam vanity URL çözümlenemedi (input=%r)", son_parca)

        return None

    @commands.command()
    async def steam_bagla(self, ctx, steam_input: str):
        """
        Steam profilini Discord hesabına bağlar.
        Kullanım: !steam_bagla <Steam ID veya Profil Linki>
        """
        if not self.api_key:
            return await ctx.send("Steam API anahtarı yapılandırılmamış. Lütfen bot sahibine bildirin.")

        async with ctx.typing():
            steam_id = await self.resolve_steam_id(steam_input)
            
            if not steam_id:
                return await ctx.send("Steam ID bulunamadı! Lütfen geçerli bir Steam ID veya profil linki gir.\nÖrnek: `!steam_bagla https://steamcommunity.com/id/kullaniciadi` veya `!steam_bagla 76561198000000000`")

            # Profilin varlığını ve gizliliğini kontrol et
            summary_url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.api_key}&steamids={steam_id}"
            async with self._session() as session:
                async with session.get(summary_url) as response:
                    data = await response.json()
                    players = data.get('response', {}).get('players', [])
                    if not players:
                        return await ctx.send("Bu ID'ye ait bir Steam profili bulunamadı.")
                    
                    player = players[0]
                    persona_name = player.get('personaname', 'Bilinmeyen')

            # Veritabanına kaydet
            async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO steam_users (user_id, steam_id, last_updated)
                    VALUES (?, ?, ?)
                """, (ctx.author.id, steam_id, datetime.now()))
                await db.commit()

            await ctx.send(f"✅ Başarılı! **{persona_name}** Steam hesabı başarıyla bağlandı.")

    @commands.command()
    @commands.guild_only()
    async def oyunsuresi(self, ctx):
        """
        Sunucudaki kullanıcıların son 2 haftalık oyun sürelerini sıralar.
        """
        if not self.api_key:
            return await ctx.send("Steam API anahtarı eksik.")

        async with ctx.typing():
            # Veritabanından kayıtlı kullanıcıları çek
            async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
                async with db.execute("SELECT user_id, steam_id FROM steam_users") as cursor:
                    users = await cursor.fetchall()

            if not users:
                return await ctx.send("Henüz kimse Steam hesabını bağlamamış. `!steam_bagla` ile ilk sen ol!")

            leaderboard = []

            async with self._session() as session:
                for user_id, steam_id in users:
                    # Discord kullanıcısının sunucuda olup olmadığını kontrol et
                    member = ctx.guild.get_member(user_id)
                    if not member:
                        continue

                    url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={steam_id}&format=json"
                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                games = data.get('response', {}).get('games', [])
                                
                                # Son 2 haftadaki toplam oyun süresi (dakika)
                                total_playtime_2weeks = sum(game.get('playtime_2weeks', 0) for game in games)
                                
                                if total_playtime_2weeks > 0:
                                    leaderboard.append((member.display_name, total_playtime_2weeks))
                    except Exception as e:
                        log.warning("Oyun süresi alınamadı (steam_id=%s): %s", steam_id, e)
                        continue

            # Sıralama (En çok oynayan en üstte)
            leaderboard.sort(key=lambda x: x[1], reverse=True)

            if not leaderboard:
                return await ctx.send("Son 2 haftada kimse oyun oynamamış veya gizlilik ayarları kapalı.")

            # Mesaj oluşturma
            embed = discord.Embed(
                title="🏆 Haftalık Oyun Canavarları",
                description="Son 2 haftada en çok oyun oynayanlar:",
                color=discord.Color.gold()
            )

            for i, (name, minutes) in enumerate(leaderboard[:10], 1):
                hours = minutes // 60
                mins = minutes % 60
                time_str = f"{hours} sa {mins} dk"
                
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                embed.add_field(name=f"{medal} {name}", value=f"⏱️ {time_str}", inline=False)

            await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def ortak(self, ctx, member: discord.Member):
        """
        Etiketlenen kullanıcı ile ortak oyunları bulur ve birini önerir.
        Kullanım: !ortak @kullanici
        """
        if not self.api_key:
            return await ctx.send("Steam API anahtarı eksik.")

        if member.id == ctx.author.id:
            return await ctx.send("Kendinle ortak oyun bulamazsın. 😅")

        async with ctx.typing():
            async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
                async with db.execute("SELECT user_id, steam_id FROM steam_users WHERE user_id IN (?, ?)", (ctx.author.id, member.id)) as cursor:
                    rows = await cursor.fetchall()

            if len(rows) < 2:
                return await ctx.send("Her iki kullanıcının da Steam hesabını bağlamış olması gerekiyor. `!steam_bagla` komutunu kullanın.")

            steam_ids = {row[0]: row[1] for row in rows}
            id1 = steam_ids[ctx.author.id]
            id2 = steam_ids[member.id]

            async with self._session() as session:
                # 1. Kullanıcının oyunları
                url1 = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={id1}&include_appinfo=true&format=json"
                # 2. Kullanıcının oyunları
                url2 = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={id2}&include_appinfo=true&format=json"

                try:
                    games1 = []
                    games2 = []
                    
                    async with session.get(url1) as resp1:
                        if resp1.status == 200:
                            data1 = await resp1.json()
                            games1 = data1.get('response', {}).get('games', [])

                    async with session.get(url2) as resp2:
                        if resp2.status == 200:
                            data2 = await resp2.json()
                            games2 = data2.get('response', {}).get('games', [])

                    # Oyun ID'lerine göre set oluştur
                    games1_map = {g['appid']: g['name'] for g in games1}
                    games2_ids = {g['appid'] for g in games2}

                    # Kesişim
                    common_appids = set(games1_map.keys()) & games2_ids
                    
                    if not common_appids:
                        return await ctx.send(f"{member.display_name} ile hiç ortak oyununuz yok. 😢")

                    # Rastgele bir oyun seç
                    chosen_appid = random.choice(list(common_appids))
                    chosen_game_name = games1_map[chosen_appid]
                    
                    store_url = f"https://store.steampowered.com/app/{chosen_appid}/"

                    embed = discord.Embed(
                        title="🎮 Ortak Oyun Önerisi",
                        description=f"**{ctx.author.display_name}** ve **{member.display_name}** için ortak oyun bulundu!",
                        color=discord.Color.purple()
                    )
                    embed.add_field(name="Önerilen Oyun", value=f"**[{chosen_game_name}]({store_url})**", inline=False)
                    embed.set_footer(text=f"Toplam {len(common_appids)} ortak oyununuz var.")
                    
                    await ctx.send(embed=embed)

                except (aiohttp.ClientError, ValueError, KeyError):
                    log.exception("!ortak komutu başarısız")
                    await ctx.send("Oyunlar listelenirken bir hata oluştu.")

    @commands.command()
    @commands.guild_only()
    async def kimoyunda(self, ctx):
        """
        Steam hesabını bağlayanlardan şu an kimin ne oynadığını gösterir.
        """
        if not self.api_key:
            return await ctx.send("Steam API anahtarı eksik.")

        async with ctx.typing():
            async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
                async with db.execute("SELECT user_id, steam_id FROM steam_users") as cursor:
                    users = await cursor.fetchall()

            if not users:
                return await ctx.send("Kimse Steam hesabını bağlamamış.")

            # Steam ID'leri virgülle birleştir (API max 100 ID kabul eder)
            steam_id_map = {u[1]: u[0] for u in users}
            steam_ids_list = list(steam_id_map.keys())
            
            # 100'lük gruplar halinde işle (Basitlik için şimdilik tek grup varsayalım, ama doğrusu chunking)
            # Eğer kullanıcı sayısı çoksa chunking gerekir. Şimdilik hepsi tek seferde.
            
            playing_users = []
            
            async with self._session() as session:
                ids_str = ",".join(steam_ids_list)
                url = f"https://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.api_key}&steamids={ids_str}"
                
                try:
                    async with session.get(url) as response:
                        if response.status == 200:
                            data = await response.json()
                            players = data.get('response', {}).get('players', [])
                            
                            for player in players:
                                # gameextrainfo varsa oyundadır
                                game_name = player.get('gameextrainfo')
                                if game_name:
                                    steam_id = player['steamid']
                                    discord_id = steam_id_map.get(steam_id)
                                    member = ctx.guild.get_member(discord_id)
                                    
                                    if member:
                                        playing_users.append((member.display_name, game_name))
                except (aiohttp.ClientError, ValueError, KeyError):
                    log.exception("!kimoyunda komutu başarısız")
                    return await ctx.send("Veriler alınırken hata oluştu.")

            if not playing_users:
                return await ctx.send("Şu an kimse Steam'de oyun oynamıyor. 🦗")

            embed = discord.Embed(
                title="🕹️ Kim Ne Oynuyor?",
                color=discord.Color.green()
            )
            
            for name, game in playing_users:
                embed.add_field(name=name, value=f"🎮 {game}", inline=False)

            await ctx.send(embed=embed)

    @commands.command()
    @commands.guild_only()
    async def analiz(self, ctx, member: discord.Member = None):
        """
        Kullanıcının oyun zevkini (Gamer DNA) analiz eder.
        En çok oynanan oyunların türlerine göre pasta grafiği oluşturur.
        """
        member = member or ctx.author
        
        if not self.api_key:
            return await ctx.send("Steam API anahtarı eksik.")

        async with ctx.typing():
            # 1. Steam ID'yi bul
            async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
                async with db.execute("SELECT steam_id FROM steam_users WHERE user_id = ?", (member.id,)) as cursor:
                    row = await cursor.fetchone()
            
            if not row:
                return await ctx.send(f"{member.display_name} henüz Steam hesabını bağlamamış.")
            
            steam_id = row[0]

            # 2. En çok oynanan oyunları çek
            async with self._session() as session:
                url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={steam_id}&include_appinfo=true&format=json"
                try:
                    async with session.get(url) as response:
                        if response.status != 200:
                            return await ctx.send("Steam verileri alınamadı.")
                        data = await response.json()
                        games = data.get('response', {}).get('games', [])
                except (aiohttp.ClientError, ValueError):
                    log.exception("!analiz oyun listesi alınamadı")
                    return await ctx.send("Oyun listesi alınırken hata oluştu.")

            if not games:
                return await ctx.send("Kullanıcının hiç oyunu yok veya gizlilik ayarları kapalı.")

            # En çok oynanan 20 oyunu al (API limitleri ve hız için 50 yerine 20)
            top_games = sorted(games, key=lambda x: x.get('playtime_forever', 0), reverse=True)[:30]
            
            genre_counts = {}
            
            # 3. Oyunların türlerini çek (Store API)
            # Not: Bu işlem biraz sürebilir, kullanıcıya bilgi verelim.
            status_msg = await ctx.send(f"🧬 {member.display_name} için Gamer DNA analizi yapılıyor... (Bu işlem biraz sürebilir)")

            genre_counts = await self.count_genres(top_games)

            if not genre_counts:
                await status_msg.delete()
                return await ctx.send("Oyun türleri analiz edilemedi. (Steam Store API yanıt vermedi)")

            # 4. Veriyi düzenle ve Grafik Oluştur
            # En popüler 5 türü al, gerisini "Diğer" yap
            sorted_genres = sorted(genre_counts.items(), key=lambda x: x[1], reverse=True)
            top_5 = sorted_genres[:5]
            others_count = sum(count for _, count in sorted_genres[5:])
            
            labels = [g[0] for g in top_5]
            data = [g[1] for g in top_5]
            
            if others_count > 0:
                labels.append("Diğer")
                data.append(others_count)

            # QuickChart URL oluştur
            chart_config = {
                "type": "pie",
                "data": {
                    "labels": labels,
                    "datasets": [{
                        "data": data,
                        "backgroundColor": ["#FF6384", "#36A2EB", "#FFCE56", "#4BC0C0", "#9966FF", "#C9CBCF"]
                    }]
                },
                "options": {
                    "plugins": {
                        "legend": {"labels": {"font": {"size": 14, "color": "white"}}},
                        "datalabels": {"color": "white", "font": {"size": 16, "weight": "bold"}}
                    }
                }
            }
            
            # JSON'u URL-safe string'e çevir
            encoded_config = urllib.parse.quote(json.dumps(chart_config))
            chart_url = f"https://quickchart.io/chart?c={encoded_config}&bkg=transparent"

            # 5. Yorum Oluştur
            dominant_genre = top_5[0][0]
            comments = {
                "Aksiyon": "Adrenalin tutkunusun! Reflekslerin konuşuyor. 💥",
                "Macera": "Keşfetmeyi ve hikayelerde kaybolmayı seviyorsun. 🗺️",
                "RYO": "Karakter geliştirmek ve dünyaları kurtarmak senin işin. 🛡️",
                "Strateji": "Büyük resmî gören bir taktik dehasısın. 🧠",
                "Simülasyon": "Gerçekçilik ve detaylar senin için her şey. ✈️",
                "Spor": "Rekabetçi ruhun sahada (veya ekranda) belli oluyor. ⚽",
                "Yarış": "Hız senin göbek adın! 🏎️",
                "Bağımsız Yapımcı": "Gizli hazineleri bulmayı seven bir gurmesin. 💎",
                "Devasa Çok Oyunculu": "Sosyal bir oyuncusun, klanın sensiz yapamaz. 👥"
            }
            comment = comments.get(dominant_genre, "Çok yönlü bir oyuncusun! Her türden keyif alıyorsun. 🎮")

            # Embed Gönder
            embed = discord.Embed(
                title=f"🧬 {member.display_name} - Oyun DNA'sı",
                description=f"**Baskın Tür:** {dominant_genre}\n\n_{comment}_",
                color=discord.Color.dark_theme()
            )
            embed.set_image(url=chart_url)
            embed.set_footer(text=f"Analiz edilen oyun sayısı: {len(top_games)}")

            await status_msg.delete()
            await ctx.send(embed=embed)

    @commands.command(aliases=["kimlik"])
    @commands.guild_only()
    async def kart(self, ctx, member: discord.Member = None):
        """
        Kullanıcının Steam Gamer Kartını oluşturur.
        """
        member = member or ctx.author
        
        if not self.api_key:
            return await ctx.send("Steam API anahtarı eksik.")

        async with ctx.typing():
            # 1. Veritabanından Steam ID çek
            async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
                async with db.execute("SELECT steam_id FROM steam_users WHERE user_id = ?", (member.id,)) as cursor:
                    row = await cursor.fetchone()
            
            if not row:
                return await ctx.send(f"{member.display_name} henüz Steam hesabını bağlamamış.")
            
            steam_id = row[0]

            # 2. Steam'den Oyunları Çek
            async with self._session() as session:
                # Oyunlar
                url_games = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={steam_id}&include_appinfo=true&format=json"
                # Profil (Avatar için) - Discord avatarı da kullanılabilir ama Steam avatarı daha uyumlu olabilir. 
                # Kullanıcı isteği: "kullanıcının profil resmini" dedi, Discord profil resmi daha mantıklı çünkü bot Discord botu.
                
                try:
                    async with session.get(url_games) as resp:
                        if resp.status != 200: return await ctx.send("Steam verileri alınamadı.")
                        data = await resp.json()
                        games = data.get('response', {}).get('games', [])
                except (aiohttp.ClientError, ValueError):
                    log.exception("!kart oyun listesi alınamadı")
                    return await ctx.send("Veri alınırken hata oluştu.")

            if not games:
                return await ctx.send("Gösterilecek oyun bulunamadı.")

            # En çok oynanan 3 oyunu al
            top_3 = sorted(games, key=lambda x: x.get('playtime_forever', 0), reverse=True)[:3]

            # 3. Ağ işleri: avatar, favori tür, kapak görselleri
            #    (Hepsi PIL'den ÖNCE toplanır ki çizim tek seferde executor'da yapılabilsin.)
            try:
                avatar_bytes = await member.display_avatar.read()
            except discord.HTTPException:
                log.warning("Avatar okunamadı (user_id=%s)", member.id)
                avatar_bytes = None

            top_10_games = sorted(games, key=lambda x: x.get('playtime_forever', 0), reverse=True)[:10]
            genre_counts = await self.count_genres(top_10_games)
            favorite_genre = max(genre_counts, key=genre_counts.get) if genre_counts else "Bilinmiyor"

            kapaklar = []
            async with self._session() as session:
                for game in top_3:
                    veri = None
                    header_url = f"https://steamcdn-a.akamaihd.net/steam/apps/{game['appid']}/header.jpg"
                    try:
                        async with session.get(header_url) as resp:
                            if resp.status == 200:
                                veri = await resp.read()
                    except aiohttp.ClientError:
                        log.warning("Kapak görseli alınamadı (appid=%s)", game['appid'])
                    kapaklar.append({
                        "name": game['name'],
                        "playtime": game.get('playtime_forever', 0) // 60,
                        "image": veri,
                    })

            # 4. Görseli oluştur — Pillow bloklayıcıdır, event loop'u kilitlememek
            #    için executor'da çalıştırılır (economy.py'deki liderlik tablosuyla aynı desen).
            toplam_saat = sum(g.get('playtime_forever', 0) for g in games) // 60
            buffer = await self.bot.loop.run_in_executor(
                None,
                self.render_gamer_card,
                member.display_name, avatar_bytes, toplam_saat, len(games), favorite_genre, kapaklar,
            )

            await ctx.send(file=discord.File(buffer, filename="gamer_card.png"))

    def render_gamer_card(self, display_name, avatar_bytes, toplam_saat, oyun_sayisi, favori_tur, kapaklar):
        """Gamer kartını çizer. BLOKLAYICI — executor'da çağrılmalı."""
        width, height = 800, 400
        card = Image.new("RGBA", (width, height), (30, 30, 35))
        draw = ImageDraw.Draw(card)

        try:
            font_large = ImageFont.truetype("Roboto-Regular.ttf", 20)
            font_medium = ImageFont.truetype("Roboto-Regular.ttf", 15)
            font_small = ImageFont.truetype("Roboto-Regular.ttf", 12)
        except OSError:
            font_large = font_medium = font_small = ImageFont.load_default()

        # --- Sol Taraf: Kullanıcı Bilgisi ---
        avatar_size = 150
        if avatar_bytes:
            try:
                avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
                avatar_img = avatar_img.resize((avatar_size, avatar_size))
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                ImageDraw.Draw(mask).ellipse((0, 0, avatar_size, avatar_size), fill=255)
                card.paste(avatar_img, (50, 50), mask)
            except Exception:
                log.exception("Avatar işlenemedi")

        draw.text((50, 220), display_name, font=font_large, fill="white")
        draw.text((50, 270), f"Toplam Süre: {toplam_saat} Saat", font=font_medium, fill="#AAAAAA")
        draw.text((50, 310), f"Kütüphane: {oyun_sayisi} Oyun", font=font_medium, fill="#AAAAAA")
        draw.text((50, 350), f"Favori Tür: {favori_tur}", font=font_medium, fill="#AAAAAA")

        # --- Sağ Taraf: Top 3 Oyun ---
        game_x, game_y = 350, 20
        for kapak in kapaklar:
            cizildi = False
            if kapak["image"]:
                try:
                    game_img = Image.open(io.BytesIO(kapak["image"])).convert("RGBA")
                    card.paste(game_img.resize((240, 112)), (game_x, game_y))
                    cizildi = True
                except Exception:
                    log.warning("Kapak görseli işlenemedi: %s", kapak["name"])

            if not cizildi:
                draw.rectangle([game_x, game_y, game_x + 240, game_y + 112], outline="white", width=2)
                draw.text((game_x + 10, game_y + 40), "Resim Yok", fill="white")

            draw.text((game_x + 250, game_y + 10), kapak["name"][:22], font=font_medium, fill="white")
            draw.text((game_x + 250, game_y + 40), f"{kapak['playtime']} Saat", font=font_small, fill="#AAAAAA")
            game_y += 120

        buffer = io.BytesIO()
        card.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer


    @commands.command(name="sunucu-istatistik", aliases=["server-stats"])
    @commands.guild_only()
    async def sunucu_istatistik(self, ctx):
        """
        Sunucudaki tüm bağlı Steam hesaplarının kolektif istatistiklerini gösterir.
        Toplam oyun süresi, en popüler oyun ve sunucunun favori türü gibi verileri analiz eder.
        """
        if not self.api_key:
            return await ctx.send("Steam API anahtarı eksik.")

        status_msg = await ctx.send("📊 Sunucu kütüphanesi taranıyor... Bu işlem kullanıcı sayısına göre zaman alabilir.")

        async with ctx.typing():
            # 1. Tüm kullanıcıları çek
            async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
                async with db.execute("SELECT steam_id FROM steam_users") as cursor:
                    users = await cursor.fetchall()

            if not users:
                await status_msg.delete()
                return await ctx.send("Henüz kimse Steam hesabını bağlamamış.")

            total_playtime_minutes = 0
            game_ownership = {} # {appid: {"name": name, "count": count}}
            
            # 2. Her kullanıcının oyunlarını çek ve topla
            async with self._session() as session:
                for (steam_id,) in users:
                    url = f"https://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={steam_id}&include_appinfo=true&format=json"
                    try:
                        async with session.get(url) as response:
                            if response.status == 200:
                                data = await response.json()
                                games = data.get('response', {}).get('games', [])
                                
                                for game in games:
                                    appid = game['appid']
                                    playtime = game.get('playtime_forever', 0)
                                    name = game['name']
                                    
                                    total_playtime_minutes += playtime
                                    
                                    if appid not in game_ownership:
                                        game_ownership[appid] = {"name": name, "count": 0}
                                    game_ownership[appid]["count"] += 1
                    except Exception as e:
                        log.warning("Sunucu istatistiği alınamadı (steam_id=%s): %s", steam_id, e)
                        continue

            if not game_ownership:
                await status_msg.delete()
                return await ctx.send("Sunucu verisi oluşturulamadı. (Gizlilik ayarları veya API hatası)")

            # 3. İstatistikleri Hesapla
            
            # Toplam Süre
            total_hours = total_playtime_minutes // 60
            
            # En Popüler Oyun
            most_popular_appid = max(game_ownership, key=lambda k: game_ownership[k]["count"])
            most_popular_game = game_ownership[most_popular_appid]
            
            # 4. Sunucu Favori Türü (En popüler 20 oyun üzerinden)
            # Tüm oyunları taramak çok uzun sürer, bu yüzden en çok sahip olunan 20 oyunu baz alıyoruz.
            sorted_games_by_popularity = sorted(game_ownership.items(), key=lambda x: x[1]["count"], reverse=True)[:20]
            genre_counts = {}
            
            genre_counts = await self.count_genres(
                [{'appid': appid} for appid, _ in sorted_games_by_popularity]
            )
            
            server_favorite_genre = max(genre_counts, key=genre_counts.get) if genre_counts else "Bilinmiyor"

            # 5. Embed Oluştur
            embed = discord.Embed(
                title="📊 Sunucu Kütüphane İstatistikleri",
                description=f"Bu sunucudaki **{len(users)}** Steam kullanıcısının verileri analiz edildi ve en çok sahip olunan 20 oyun arasından sunucu analizi yapıldı.",
                color=discord.Color.gold()
            )
            
            embed.add_field(
                name="⏳ Toplam Oyun Süresi", 
                value=f"**{total_hours:,}** Saat", 
                inline=False
            )
            
            embed.add_field(
                name="🏆 En Popüler Oyun", 
                value=f"**{most_popular_game['name']}**\n({most_popular_game['count']} kişi sahip)", 
                inline=False
            )
            
            embed.add_field(
                name="🎭 Sunucunun Favori Türü", 
                value=f"**{server_favorite_genre}**", 
                inline=False
            )
            
            # En popüler oyunun resmini ekle
            embed.set_thumbnail(url=f"https://steamcdn-a.akamaihd.net/steam/apps/{most_popular_appid}/header.jpg")
            
            await status_msg.delete()
            await ctx.send(embed=embed)

async def setup(bot):
    await bot.add_cog(Steam(bot))
