import discord
from discord.ext import commands
import aiosqlite
import os
import aiohttp
import json
import random
import io
from PIL import Image, ImageDraw, ImageFont
from datetime import datetime
from dotenv import load_dotenv

DB_PATH = "steam.db"

class Steam(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        load_dotenv() # Force reload .env
        self.api_key = os.getenv('STEAM_API_KEY')
        if self.api_key:
            print(f"[+] Steam API Key yüklendi (Uzunluk: {len(self.api_key)})")
        else:
            print("[-] Steam API Key BULUNAMADI! .env dosyasını kontrol edin.")

    async def cog_load(self):
        if not self.api_key:
            print("UYARI: STEAM_API_KEY bulunamadı! Steam komutları çalışmayabilir.")
        
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS steam_users (
                    user_id INTEGER PRIMARY KEY,
                    steam_id TEXT NOT NULL,
                    last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            await db.commit()
            print("[+] Steam veritabanı hazır.")

    async def resolve_steam_id(self, input_id):
        """
        Kullanıcı girdisini (URL, ID, Vanity URL) Steam 64 ID'ye çevirir.
        """
        # Eğer direkt 17 haneli bir sayı ise (Steam 64 ID)
        if input_id.isdigit() and len(input_id) == 17:
            return input_id
        
        # URL temizleme
        clean_input = input_id.strip('/').split('/')[-1]
        
        # Vanity URL çözme (kullanıcı adı)
        url = f"http://api.steampowered.com/ISteamUser/ResolveVanityURL/v0001/?key={self.api_key}&vanityurl={clean_input}"
        async with aiohttp.ClientSession() as session:
            async with session.get(url) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('response', {}).get('success') == 1:
                        return data['response']['steamid']
        
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
            summary_url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.api_key}&steamids={steam_id}"
            async with aiohttp.ClientSession() as session:
                async with session.get(summary_url) as response:
                    data = await response.json()
                    players = data.get('response', {}).get('players', [])
                    if not players:
                        return await ctx.send("Bu ID'ye ait bir Steam profili bulunamadı.")
                    
                    player = players[0]
                    persona_name = player.get('personaname', 'Bilinmeyen')

            # Veritabanına kaydet
            async with aiosqlite.connect(DB_PATH) as db:
                await db.execute("""
                    INSERT OR REPLACE INTO steam_users (user_id, steam_id, last_updated)
                    VALUES (?, ?, ?)
                """, (ctx.author.id, steam_id, datetime.now()))
                await db.commit()

            await ctx.send(f"✅ Başarılı! **{persona_name}** Steam hesabı başarıyla bağlandı.")

    @commands.command()
    async def oyunsuresi(self, ctx):
        """
        Sunucudaki kullanıcıların son 2 haftalık oyun sürelerini sıralar.
        """
        if not self.api_key:
            return await ctx.send("Steam API anahtarı eksik.")

        async with ctx.typing():
            # Veritabanından kayıtlı kullanıcıları çek
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT user_id, steam_id FROM steam_users") as cursor:
                    users = await cursor.fetchall()

            if not users:
                return await ctx.send("Henüz kimse Steam hesabını bağlamamış. `!steam_bagla` ile ilk sen ol!")

            leaderboard = []

            async with aiohttp.ClientSession() as session:
                for user_id, steam_id in users:
                    # Discord kullanıcısının sunucuda olup olmadığını kontrol et
                    member = ctx.guild.get_member(user_id)
                    if not member:
                        continue

                    url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={steam_id}&format=json"
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
                        print(f"Hata ({steam_id}): {e}")
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
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT user_id, steam_id FROM steam_users WHERE user_id IN (?, ?)", (ctx.author.id, member.id)) as cursor:
                    rows = await cursor.fetchall()

            if len(rows) < 2:
                return await ctx.send("Her iki kullanıcının da Steam hesabını bağlamış olması gerekiyor. `!steam_bagla` komutunu kullanın.")

            steam_ids = {row[0]: row[1] for row in rows}
            id1 = steam_ids[ctx.author.id]
            id2 = steam_ids[member.id]

            async with aiohttp.ClientSession() as session:
                # 1. Kullanıcının oyunları
                url1 = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={id1}&include_appinfo=true&format=json"
                # 2. Kullanıcının oyunları
                url2 = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={id2}&include_appinfo=true&format=json"

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

                except Exception as e:
                    print(f"Hata (!ortak): {e}")
                    await ctx.send("Oyunlar listelenirken bir hata oluştu.")

    @commands.command()
    async def kimoyunda(self, ctx):
        """
        Steam hesabını bağlayanlardan şu an kimin ne oynadığını gösterir.
        """
        if not self.api_key:
            return await ctx.send("Steam API anahtarı eksik.")

        async with ctx.typing():
            async with aiosqlite.connect(DB_PATH) as db:
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
            
            async with aiohttp.ClientSession() as session:
                ids_str = ",".join(steam_ids_list)
                url = f"http://api.steampowered.com/ISteamUser/GetPlayerSummaries/v0002/?key={self.api_key}&steamids={ids_str}"
                
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
                except Exception as e:
                    print(f"Hata (!kimoyunda): {e}")
                    return await ctx.send("Veriler alınırken hata oluştu.")

            if not playing_users:
                return await ctx.send("Şu an kimse Steam'de oyun oynamıyor. 🦗")

            embed = discord.Embed(
                title="🕹️ Kim Ne Oynuyor?",
                color=discord.Color.green()
            )
            
            for name, game in playing_users:
                embed.add_field(name=name, value=f"🎮 {game}", inline=False)
                
            for name, game in playing_users:
                embed.add_field(name=name, value=f"🎮 {game}", inline=False)
                
            await ctx.send(embed=embed)

    @commands.command()
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
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT steam_id FROM steam_users WHERE user_id = ?", (member.id,)) as cursor:
                    row = await cursor.fetchone()
            
            if not row:
                return await ctx.send(f"{member.display_name} henüz Steam hesabını bağlamamış.")
            
            steam_id = row[0]

            # 2. En çok oynanan oyunları çek
            async with aiohttp.ClientSession() as session:
                url = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={steam_id}&include_appinfo=true&format=json"
                try:
                    async with session.get(url) as response:
                        if response.status != 200:
                            return await ctx.send("Steam verileri alınamadı.")
                        data = await response.json()
                        games = data.get('response', {}).get('games', [])
                except Exception as e:
                    print(f"Hata (!analiz games): {e}")
                    return await ctx.send("Oyun listesi alınırken hata oluştu.")

            if not games:
                return await ctx.send("Kullanıcının hiç oyunu yok veya gizlilik ayarları kapalı.")

            # En çok oynanan 20 oyunu al (API limitleri ve hız için 50 yerine 20)
            top_games = sorted(games, key=lambda x: x.get('playtime_forever', 0), reverse=True)[:20]
            
            genre_counts = {}
            
            # 3. Oyunların türlerini çek (Store API)
            # Not: Bu işlem biraz sürebilir, kullanıcıya bilgi verelim.
            status_msg = await ctx.send(f"🧬 {member.display_name} için Gamer DNA analizi yapılıyor... (Bu işlem biraz sürebilir)")

            async with aiohttp.ClientSession() as session:
                for game in top_games:
                    appid = game['appid']
                    store_url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=turkish"
                    
                    try:
                        async with session.get(store_url) as response:
                            if response.status == 200:
                                store_data = await response.json()
                                if store_data and str(appid) in store_data and store_data[str(appid)]['success']:
                                    genres = store_data[str(appid)]['data'].get('genres', [])
                                    for g in genres:
                                        g_name = g['description']
                                        genre_counts[g_name] = genre_counts.get(g_name, 0) + 1
                    except Exception as e:
                        print(f"Hata (!analiz genre {appid}): {e}")
                        continue
                    
                    # Rate limit yememek için kısa bekleme (opsiyonel ama güvenli)
                    # await asyncio.sleep(0.1) 

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
            import urllib.parse
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

            await status_msg.delete()
            await ctx.send(embed=embed)

    @commands.command(aliases=["kimlik"])
    async def kart(self, ctx, member: discord.Member = None):
        """
        Kullanıcının Steam Gamer Kartını oluşturur.
        """
        member = member or ctx.author
        
        if not self.api_key:
            return await ctx.send("Steam API anahtarı eksik.")

        async with ctx.typing():
            # 1. Veritabanından Steam ID çek
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT steam_id FROM steam_users WHERE user_id = ?", (member.id,)) as cursor:
                    row = await cursor.fetchone()
            
            if not row:
                return await ctx.send(f"{member.display_name} henüz Steam hesabını bağlamamış.")
            
            steam_id = row[0]

            # 2. Steam'den Oyunları Çek
            async with aiohttp.ClientSession() as session:
                # Oyunlar
                url_games = f"http://api.steampowered.com/IPlayerService/GetOwnedGames/v0001/?key={self.api_key}&steamid={steam_id}&include_appinfo=true&format=json"
                # Profil (Avatar için) - Discord avatarı da kullanılabilir ama Steam avatarı daha uyumlu olabilir. 
                # Kullanıcı isteği: "kullanıcının profil resmini" dedi, Discord profil resmi daha mantıklı çünkü bot Discord botu.
                
                try:
                    async with session.get(url_games) as resp:
                        if resp.status != 200: return await ctx.send("Steam verileri alınamadı.")
                        data = await resp.json()
                        games = data.get('response', {}).get('games', [])
                except Exception as e:
                    print(f"Hata (!kart): {e}")
                    return await ctx.send("Veri alınırken hata oluştu.")

            if not games:
                return await ctx.send("Gösterilecek oyun bulunamadı.")

            # En çok oynanan 3 oyunu al
            top_3 = sorted(games, key=lambda x: x.get('playtime_forever', 0), reverse=True)[:3]

            # 3. Görsel Oluşturma (Pillow)
            # Arka plan (800x400)
            width, height = 800, 400
            background_color = (30, 30, 35) # Koyu gri
            card = Image.new("RGBA", (width, height), background_color)
            draw = ImageDraw.Draw(card)

            # Fontlar (Varsayılan fontu yüklemeye çalış, yoksa default)
            try:
                font_large = ImageFont.truetype("Roboto-Regular.ttf", 20)
                font_medium = ImageFont.truetype("Roboto-Regular.ttf", 15)
                font_small = ImageFont.truetype("Roboto-Regular.ttf", 10)
            except:
                font_large = ImageFont.load_default()
                font_medium = ImageFont.load_default()
                font_small = ImageFont.load_default()

            # --- Sol Taraf: Kullanıcı Bilgisi ---
            
            # Avatar
            avatar_size = 150
            if member.avatar:
                avatar_bytes = await member.avatar.read()
                avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
                avatar_img = avatar_img.resize((avatar_size, avatar_size))
                
                # Yuvarlak maske
                mask = Image.new("L", (avatar_size, avatar_size), 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.ellipse((0, 0, avatar_size, avatar_size), fill=255)
                
                card.paste(avatar_img, (50, 50), mask)
            
            # Kullanıcı Adı
            draw.text((50, 220), member.display_name, font=font_large, fill="white")
            
            # Toplam Oyun Saati
            total_minutes = sum(g.get('playtime_forever', 0) for g in games)
            total_hours = total_minutes // 60
            draw.text((50, 270), f"Toplam Süre: {total_hours} Saat", font=font_medium, fill="#AAAAAA")
            
            # Oyun Sayısı
            draw.text((50, 310), f"Kütüphane: {len(games)} Oyun", font=font_medium, fill="#AAAAAA")

            # --- Favori Tür Analizi (Top 10 Oyun) ---
            # Kullanıcı beklerken bilgi verelim (opsiyonel, ama iyi olur)
            # await ctx.send("Favori tür analiz ediliyor...", delete_after=3)
            
            top_10_games = sorted(games, key=lambda x: x.get('playtime_forever', 0), reverse=True)[:10]
            genre_counts = {}
            
            async with aiohttp.ClientSession() as session:
                for game in top_10_games:
                    appid = game['appid']
                    store_url = f"https://store.steampowered.com/api/appdetails?appids={appid}&l=turkish"
                    try:
                        async with session.get(store_url) as response:
                            if response.status == 200:
                                store_data = await response.json()
                                if store_data and str(appid) in store_data and store_data[str(appid)]['success']:
                                    genres = store_data[str(appid)]['data'].get('genres', [])
                                    for g in genres:
                                        g_name = g['description']
                                        genre_counts[g_name] = genre_counts.get(g_name, 0) + 1
                    except:
                        continue

            favorite_genre = max(genre_counts, key=genre_counts.get) if genre_counts else "Bilinmiyor"

            # Favori Tür Yazısı
            draw.text((50, 350), f"Favori Tür: {favorite_genre}", font=font_medium, fill="#AAAAAA")

            # --- Sağ Taraf: Top 3 Oyun ---
            
            game_x = 350
            game_y = 30
            
            async with aiohttp.ClientSession() as session:
                for game in top_3:
                    appid = game['appid']
                    game_name = game['name']
                    playtime = game.get('playtime_forever', 0) // 60
                    
                    # Kapak Resmi URL
                    header_url = f"https://steamcdn-a.akamaihd.net/steam/apps/{appid}/header.jpg"
                    
                    try:
                        async with session.get(header_url) as resp:
                            if resp.status == 200:
                                img_data = await resp.read()
                                game_img = Image.open(io.BytesIO(img_data)).convert("RGBA")
                                # Boyutlandır (Örn: 400x187 -> 200x90 gibi küçültelim)
                                game_img = game_img.resize((240, 112)) 
                                card.paste(game_img, (game_x, game_y))
                    except:
                        # Resim yüklenemezse kutu çiz
                        draw.rectangle([game_x, game_y, game_x+240, game_y+112], outline="white", width=2)
                        draw.text((game_x+10, game_y+40), "Resim Yok", fill="white")

                    # Oyun Adı ve Süresi
                    # draw.text((game_x + 250, game_y + 10), game_name[:20], font=font_medium, fill="white")
                    draw.text((game_x + 250, game_y + 40), f"{playtime} Saat", font=font_small, fill="#AAAAAA")

                    game_y += 120 # Bir sonraki oyun için aşağı kaydır

            # ByteIO'ya kaydet
            buffer = io.BytesIO()
            card.save(buffer, format="PNG")
            buffer.seek(0)
            
            file = discord.File(buffer, filename="gamer_card.png")
            await ctx.send(file=file)

async def setup(bot):
    await bot.add_cog(Steam(bot))
