import discord
from discord.ext import commands
import wavelink
import os
import aiosqlite
import json

DB_PATH = "playlists.db"

class Music(commands.Cog):
    def __init__(self, bot):
        self.bot = bot

    async def cog_load(self):
        """Cog yüklendiğinde veritabanını oluştur ve Lavalink'e bağlan."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS playlists (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    user_id INTEGER,
                    name TEXT,
                    tracks TEXT
                )
            """)
            await db.commit()
            
        self.bot.loop.create_task(self.connect_nodes())

    async def connect_nodes(self):
        """Lavalink sunucusuna bağlanır."""
        await self.bot.wait_until_ready() # Botun hazır olmasını bekle
        
        node_url = os.getenv("LAVALINK_URL", "http://127.0.0.1:2333")
        password = os.getenv("LAVALINK_PASSWORD", "youshallnotpass")
        
        nodes = [
            wavelink.Node(uri=node_url, password=password)
        ]
        
        try:
            await wavelink.Pool.connect(nodes=nodes, client=self.bot, cache_capacity=100)
            print(f"[+] Wavelink bağlandı: {node_url}")
        except Exception as e:
            print(f"[-] Wavelink bağlantı hatası: {e}")

    @commands.Cog.listener()
    async def on_wavelink_node_ready(self, payload: wavelink.NodeReadyEventPayload):
        print(f"Lavalink Node bağlandı: {payload.node.identifier}")

    @commands.command(name="connect", aliases=["join", "baglan"])
    async def connect_command(self, ctx):
        """Ses kanalına bağlanır."""
        if not ctx.author.voice:
            return await ctx.send("Önce bir ses kanalına girmelisin!")
        
        channel = ctx.author.voice.channel
        if not ctx.voice_client:
            await channel.connect(cls=wavelink.Player)
            await ctx.send(f"🔊 **{channel.name}** kanalına bağlandım.")
        else:
            await ctx.send("Zaten bir kanaldayım.")

    @commands.command(name="play", aliases=["cal", "p"])
    async def play_command(self, ctx, *, search: str = None):
        """Müzik çalar."""
        print(f"[DEBUG] Play komutu çalıştı. Gelen arama: '{search}'")
        
        if search is None:
            return await ctx.send("❌ Lütfen bir şarkı adı veya linki gir! Örnek: `!play tarkan`")

        if not ctx.voice_client:
            await ctx.invoke(self.connect_command)
            
        if not ctx.voice_client:
            return

        player: wavelink.Player = ctx.voice_client
        player.autoplay = wavelink.AutoPlayMode.partial

        try:
            tracks = await wavelink.Playable.search(search)
        except Exception as e:
            return await ctx.send(f"Hata oluştu: {e}")

        if not tracks:
            return await ctx.send("Şarkı bulunamadı.")

        if isinstance(tracks, wavelink.Playlist):
            added = await player.queue.put_wait(tracks)
            await ctx.send(f"🎶 Playlist eklendi: **{tracks.name}** ({added} şarkı)")
        else:
            track = tracks[0]
            await player.queue.put_wait(track)
            await ctx.send(f"🎵 Kuyruğa eklendi: **{track.title}**")

        if not player.playing:
            await player.play(player.queue.get(), volume=100)

    @commands.command(name="stop", aliases=["dur", "leave", "cik"])
    async def stop_command(self, ctx):
        """Müziği durdurur ve kanaldan ayrılır."""
        if not ctx.voice_client:
            return await ctx.send("Zaten bağlı değilim.")
        
        await ctx.voice_client.disconnect()
        await ctx.send("👋 Görüşürüz!")

    @commands.command(name="skip", aliases=["gec", "s"])
    async def skip_command(self, ctx):
        """Şarkıyı geçer."""
        if not ctx.voice_client:
            return
        
        player: wavelink.Player = ctx.voice_client
        if not player.playing:
            return await ctx.send("Şu an bir şey çalmıyor.")
        
        await player.skip(force=True)
        await ctx.send("⏭️ Şarkı geçildi.")

    @commands.command(name="queue", aliases=["kuyruk", "q"])
    async def queue_command(self, ctx):
        """Kuyruğu gösterir."""
        if not ctx.voice_client:
            return
            
        player: wavelink.Player = ctx.voice_client
        if player.queue.is_empty:
            return await ctx.send("Kuyruk boş.")
            
        embed = discord.Embed(title="Müzik Kuyruğu", color=discord.Color.blue())
        queue_list = ""
        for i, track in enumerate(player.queue[:10], start=1):
            queue_list += f"{i}. {track.title}\n"
            
        if len(player.queue) > 10:
            queue_list += f"...ve {len(player.queue) - 10} daha fazla."
            
        embed.description = queue_list
        await ctx.send(embed=embed)

    @commands.command(name="nowplaying", aliases=["np", "calan"])
    async def nowplaying_command(self, ctx):
        """Çalan şarkıyı gösterir."""
        if not ctx.voice_client:
            return
            
        player: wavelink.Player = ctx.voice_client
        if not player.playing:
            return await ctx.send("Şu an bir şey çalmıyor.")
            
        track = player.current
        embed = discord.Embed(title="Şu An Çalıyor", description=f"[{track.title}]({track.uri})", color=discord.Color.green())
        if track.artwork:
            embed.set_thumbnail(url=track.artwork)
        await ctx.send(embed=embed)

    # --- Playlist Yönetimi ---

    @commands.group(name="playlist", aliases=["pl"], invoke_without_command=True)
    async def playlist_group(self, ctx):
        """Playlist komutları."""
        await ctx.send("Kullanım: `!playlist create/add/play/list/delete`")

    @playlist_group.command(name="create", aliases=["olustur"])
    async def playlist_create(self, ctx, *, name: str):
        """Yeni bir playlist oluşturur."""
        async with aiosqlite.connect(DB_PATH) as db:
            # Aynı isimde playlist var mı kontrol et
            async with db.execute("SELECT id FROM playlists WHERE user_id = ? AND name = ?", (ctx.author.id, name)) as cursor:
                if await cursor.fetchone():
                    return await ctx.send("Bu isimde zaten bir playlistin var!")
            
            await db.execute("INSERT INTO playlists (user_id, name, tracks) VALUES (?, ?, ?)", (ctx.author.id, name, json.dumps([])))
            await db.commit()
        
        await ctx.send(f"✅ Playlist oluşturuldu: **{name}**")

    @playlist_group.command(name="add", aliases=["ekle"])
    async def playlist_add(self, ctx, name: str, *, query: str):
        """Playliste şarkı ekler."""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT tracks FROM playlists WHERE user_id = ? AND name = ?", (ctx.author.id, name)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return await ctx.send("Böyle bir playlist bulunamadı.")
                
                tracks = json.loads(row[0])
                tracks.append(query)
                
                await db.execute("UPDATE playlists SET tracks = ? WHERE user_id = ? AND name = ?", (json.dumps(tracks), ctx.author.id, name))
                await db.commit()
                
        await ctx.send(f"✅ **{name}** playlistine eklendi: `{query}`")

    @playlist_group.command(name="list", aliases=["liste"])
    async def playlist_list(self, ctx):
        """Playlistlerini listeler."""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT name, tracks FROM playlists WHERE user_id = ?", (ctx.author.id,)) as cursor:
                rows = await cursor.fetchall()
                
        if not rows:
            return await ctx.send("Hiç playlistin yok.")
            
        embed = discord.Embed(title=f"{ctx.author.display_name} Playlistleri", color=discord.Color.gold())
        for name, tracks_json in rows:
            tracks = json.loads(tracks_json)
            embed.add_field(name=name, value=f"{len(tracks)} şarkı", inline=True)
            
        await ctx.send(embed=embed)

    @playlist_group.command(name="play", aliases=["cal"])
    async def playlist_play(self, ctx, *, name: str):
        """Playlisti çalar."""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT tracks FROM playlists WHERE user_id = ? AND name = ?", (ctx.author.id, name)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    return await ctx.send("Böyle bir playlist bulunamadı.")
                
                track_queries = json.loads(row[0])
        
        if not track_queries:
            return await ctx.send("Bu playlist boş.")
            
        if not ctx.voice_client:
            await ctx.invoke(self.connect_command)
            
        if not ctx.voice_client:
            return
            
        player: wavelink.Player = ctx.voice_client
        await ctx.send(f"🎶 **{name}** playlisti yükleniyor... ({len(track_queries)} şarkı)")
        
        count = 0
        for query in track_queries:
            try:
                tracks = await wavelink.Playable.search(query)
                if tracks:
                    if isinstance(tracks, wavelink.Playlist):
                        await player.queue.put_wait(tracks)
                    else:
                        await player.queue.put_wait(tracks[0])
                    count += 1
            except Exception:
                pass
                
        await ctx.send(f"✅ **{count}** şarkı kuyruğa eklendi.")
        
        if not player.playing:
            await player.play(player.queue.get(), volume=100)

    @playlist_group.command(name="delete", aliases=["sil"])
    async def playlist_delete(self, ctx, *, name: str):
        """Playlisti siler."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("DELETE FROM playlists WHERE user_id = ? AND name = ?", (ctx.author.id, name))
            await db.commit()
            
        await ctx.send(f"🗑️ Playlist silindi: **{name}**")

    @play_command.error
    async def play_command_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("❌ Şarkı adı girmeyi unuttun! Kullanım: `!play <şarkı adı veya link>`")

async def setup(bot):
    await bot.add_cog(Music(bot))
