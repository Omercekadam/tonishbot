import discord
from discord.ext import commands, tasks
import aiosqlite
import random
import os
import io
from datetime import datetime, time, timezone
from PIL import Image, ImageDraw, ImageFont

DB_PATH = "economy.db"

KART_DEGERLERI = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'J': 10, 'Q': 10, 'K': 10, 'A': 11
}

SUITS = ['♠️', '♥️', '♦️', '♣️']
FACES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

def el_hesapla(el: list) -> int:
    """Bir elin toplam değerini (As kontrolü yaparak) hesaplar."""
    toplam = 0
    as_sayisi = 0
    for kart in el:
        yuz = kart[0]
        toplam += KART_DEGERLERI[yuz]
        if yuz == 'A':
            as_sayisi += 1
    while toplam > 21 and as_sayisi > 0:
        toplam -= 10
        as_sayisi -= 1
    return toplam

def kartlari_goster(el: list) -> str:
    """El listesini emojili stringe çevirir."""
    return ", ".join(f"{kart[0]}{kart[1]}" for kart in el)

class BlackjackView(discord.ui.View):
    def __init__(self, ctx, bet: int, cog):
        super().__init__(timeout=60.0) 
        self.ctx = ctx
        self.bet = bet
        self.cog = cog
        self.player_hand = [] 
        self.dealer_hand = [] 
        
        self.deck = []
        for _ in range(4):
            for suit in SUITS:
                for face in FACES:
                    self.deck.append((face, suit))
        
        random.shuffle(self.deck) 
        self.message = None 
        
        self.player_hand.append(self.deck.pop())
        self.player_hand.append(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())

    async def on_timeout(self):
        if self.message:
            await self.message.edit(content="Zaman aşımı! Oyun iptal edildi. Bahis iade edilmedi.", view=None, embed=None)

    async def update_message(self, content, game_over=False):
        """Oyun durumunu gösteren mesajı günceller."""
        if game_over:
            self.stop() 
            await self.message.edit(content=content, view=None, embed=None)
        else:
            player_score = el_hesapla(self.player_hand)
            dealer_card = self.dealer_hand[0]
            dealer_card_formatted = f"{dealer_card[0]}{dealer_card[1]}"
            
            embed = discord.Embed(
                title=f"{self.ctx.author.display_name} Blackjack Oynuyor!",
                description=f"Bahis: **{self.bet}** tonish coin\n\n"
                            f"Senin Elin: {kartlari_goster(self.player_hand)} (Toplam: {player_score})\n"
                            f"Kurpiyerin Görünen Kartı: {dealer_card_formatted}\n\n"
                            f"**Kart mı istiyorsun, yoksa duracak mısın?**",
                color=discord.Color.blue()
            )
            await self.message.edit(content="", embed=embed, view=self)

    async def check_game_state(self, interaction):
        """Oyunun durumunu kontrol eder."""
        player_score = el_hesapla(self.player_hand)
        
        if player_score > 21:
            await self.cog.update_balance(self.ctx.author.id, -self.bet) 
            await self.update_message(
                f"**Yandın!** (Bust) 💥\n"
                f"Elin: {kartlari_goster(self.player_hand)} (Toplam: {player_score})\n"
                f"**{self.bet}** tonish coin kaybettin.",
                game_over=True
            )
            return True 
        
        if player_score == 21:
            await self.dealer_turn(interaction)
            return True 

        return False 

    async def dealer_turn(self, interaction):
        """Sıra kurpiyere geçtiğinde."""
        player_score = el_hesapla(self.player_hand)
        dealer_score = el_hesapla(self.dealer_hand)

        while dealer_score < 17:
            self.dealer_hand.append(self.deck.pop())
            dealer_score = el_hesapla(self.dealer_hand)
            
        result_message = (
            f"Senin Elin: {kartlari_goster(self.player_hand)} (Toplam: {player_score})\n"
            f"Kurpiyerin Eli: {kartlari_goster(self.dealer_hand)} (Toplam: {dealer_score})\n\n"
        )

        winnings = int(self.bet * 2) 

        if dealer_score > 21:
            result_message += f"**Kurpiyer Yandı!** Sen kazandın 🎉 **{winnings}** tonish coin aldın."
            await self.cog.update_balance(self.ctx.author.id, winnings) 
        elif player_score > dealer_score:
            result_message += f"**Kazandın!** 🎉 **{winnings}** tonish coin aldın."
            await self.cog.update_balance(self.ctx.author.id, winnings) 
        elif dealer_score > player_score:
            result_message += f"**Kaybettin...** 😥 **{self.bet}** tonish coin kaybettin."
            await self.cog.update_balance(self.ctx.author.id, -self.bet) 
        else:
            result_message += "**Berabere!** Bahsin iade edildi."

        await self.update_message(result_message, game_over=True)

    @discord.ui.button(label="Kart Çek (Hit)", style=discord.ButtonStyle.green)
    async def hit_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Bu senin oyunun değil!", ephemeral=True)
            return

        self.player_hand.append(self.deck.pop())
        await interaction.response.defer() 

        if not await self.check_game_state(interaction):
            await self.update_message(content="") 

    @discord.ui.button(label="Dur (Stand)", style=discord.ButtonStyle.red)
    async def stand_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Bu senin oyunun değil!", ephemeral=True)
            return
        
        await interaction.response.defer()
        await self.dealer_turn(interaction)

class SlotView(discord.ui.View):
    """Slot oyunu için interaktif görünüm."""
    def __init__(self, ctx, bet, cog):
        super().__init__(timeout=60.0)
        self.ctx = ctx
        self.bet = bet
        self.cog = cog

    @discord.ui.button(label="🎰 Çevir", style=discord.ButtonStyle.blurple)
    async def spin(self, interaction, button):
        if interaction.user.id != self.ctx.author.id: return
        
        bal = await self.cog.get_balance(self.ctx.author.id)
        if bal < self.bet:
            return await interaction.response.send_message("Yetersiz bakiye!", ephemeral=True)

        await self.cog.update_balance(self.ctx.author.id, -self.bet)
        
        symbols = ['🍒', '🍑', '🎮', '7️⃣']
        result = [random.choice(symbols) for _ in range(3)]
        
        win = 0
        if result[0] == result[1] == result[2]:
            win = self.bet * (100 if result[0] == '7️⃣' else 10)
        elif result.count('🍒') == 2:
            win = self.bet * 2
            
        msg = f"🎰 | {' '.join(result)} | \n"
        if win > 0:
            await self.cog.update_balance(self.ctx.author.id, win)
            msg += f"🎉 Kazandın! **{win}** coin."
        else:
            msg += "Kaybettin..."
            
        await interaction.response.edit_message(content=msg, view=self)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monthly_check.start() 

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS economy (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 100)")
            await db.commit()

    async def get_balance(self, user_id):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user_id,))
            await db.commit()
            async with db.execute("SELECT balance FROM economy WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 100

    async def update_balance(self, user_id, amount):
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user_id,))
            await db.execute("UPDATE economy SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    @commands.command()
    async def bakiye(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        bal = await self.get_balance(member.id)
        await ctx.send(f"{member.display_name}: **{bal}** tonish coin 💸")

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user) 
    async def gunluk(self, ctx):
        await self.update_balance(ctx.author.id, 50)
        bal = await self.get_balance(ctx.author.id)
        await ctx.send(f"Günlük 50 coin aldın! Yeni bakiye: **{bal}**")

    @commands.command(name="blackjack", aliases=["bj"])
    async def blackjack(self, ctx, bet: int):
        """Blackjack oynamak için."""
        user_id = ctx.author.id
        balance = await self.get_balance(user_id)
        
        if bet <= 0:
            await ctx.send("Lütfen geçerli bir bahis miktarı gir (0'dan büyük).")
            return
            
        if balance < bet:
            await ctx.send(f"Yetersiz bakiye! 😥 Mevcut bakiyen: **{balance}**")
            return

        view = BlackjackView(ctx, bet, self)
        player_score = el_hesapla(view.player_hand)
        
        dealer_card = view.dealer_hand[0] 
        dealer_card_formatted = f"{dealer_card[0]}{dealer_card[1]}" 
        
        embed = discord.Embed(
            title=f"Blackjack♠️!",
            description=f"Bahis: **{bet}** tonish coin\n\n"
                        f"Senin Elin: {kartlari_goster(view.player_hand)} (Toplam: {player_score})\n"
                        f"Kurpiyerin Görünen Kartı: {dealer_card_formatted}\n\n"
                        f"**Kart mı istiyorsun, yoksa duracak mısın?**",
            color=discord.Color.blue()
        )
        if ctx.author.avatar:
            embed.set_author(name=f"Oynayan: {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
        else:
            embed.set_author(name=f"Oynayan: {ctx.author.display_name}")

        message = await ctx.send(embed=embed, view=view)
        view.message = message 
        
        await view.check_game_state(None)

    @blackjack.error
    async def blackjack_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Unutkanlık! 💸 Bahis miktarını girmeyi unuttun. \n**Örnek kullanım:** `!blackjack 50`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Hoppa! 😮 Bahis miktarı bir sayı olmalı. \n**Örnek kullanım:** `!blackjack 50`")
        else:
            print(f"Blackjack komutunda beklenmedik hata: {error}")
            await ctx.send("Blackjack oynarken beklenmedik bir hata oluştu. 😥 Yetkiliye haber ver!")

    @commands.command()
    async def slot(self, ctx, bet: int):
        """Slot makinesi oyunu."""
        if bet <= 0: return await ctx.send("Geçersiz bahis.")
        bal = await self.get_balance(ctx.author.id)
        if bal < bet: return await ctx.send("Yetersiz bakiye.")
        
        view = SlotView(ctx, bet, self)
        await ctx.send(f"🎰 **SLOT MAKİNESİ** 🎰\nBahis: **{bet}** coin\n\n❓ | ❓ | ❓", view=view)

    def generate_leaderboard_image(self, users_data):
        """
        Liderlik tablosu için görsel oluşturur.
        users_data: [(sıra, kullanıcı_adı, bakiye, avatar_bytes), ...]
        """
        # Arka planı yükle veya oluştur
        try:
            background = Image.open("liderlik_bg.png").convert("RGBA")
        except:
            # Arka plan yoksa düz renk oluştur
            background = Image.new("RGBA", (800, 600), (44, 47, 51, 255))

        draw = ImageDraw.Draw(background)
        
        # Fontları yükle
        try:
            title_font = ImageFont.truetype("Roboto-Bold.ttf", 60)
            text_font = ImageFont.truetype("Roboto-Regular.ttf", 40)
            rank_font = ImageFont.truetype("Roboto-Bold.ttf", 50)
        except:
            title_font = ImageFont.load_default()
            text_font = ImageFont.load_default()
            rank_font = ImageFont.load_default()

        # Başlık
        draw.text((400, 50), "LİDERLİK TABLOSU", font=title_font, fill="white", anchor="mm")

        start_y = 150
        for rank, username, balance, avatar_bytes in users_data:
            # Sıra numarası
            draw.text((50, start_y + 35), f"#{rank}", font=rank_font, fill="#FFD700" if rank == 1 else "white")

            # Avatar
            if avatar_bytes:
                try:
                    avatar = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
                    avatar = avatar.resize((70, 70))
                    # Yuvarlak maske
                    mask = Image.new("L", (70, 70), 0)
                    draw_mask = ImageDraw.Draw(mask)
                    draw_mask.ellipse((0, 0, 70, 70), fill=255)
                    background.paste(avatar, (120, start_y), mask)
                except:
                    pass # Avatar yüklenemezse boş geç

            # Kullanıcı adı ve Bakiye
            draw.text((210, start_y + 15), str(username), font=text_font, fill="white")
            draw.text((600, start_y + 15), f"{balance} Coin", font=text_font, fill="#00FF00")

            start_y += 90

        # ByteIO'ya kaydet
        buffer = io.BytesIO()
        background.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    @commands.command()
    async def liderlik(self, ctx):
        """En zengin 5 kullanıcıyı görsel olarak listeler."""
        async with ctx.typing():
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT user_id, balance FROM economy ORDER BY balance DESC LIMIT 5") as cursor:
                    rows = await cursor.fetchall()
            
            if not rows: return await ctx.send("Liste boş.")
            
            users_data = []
            for i, (uid, bal) in enumerate(rows, 1):
                user = self.bot.get_user(uid)
                if not user:
                    try:
                        user = await self.bot.fetch_user(uid)
                    except:
                        user = None
                
                username = user.display_name if user else "Bilinmeyen Kullanıcı"
                
                # Avatarı indir
                avatar_bytes = None
                if user and user.avatar:
                    try:
                        avatar_bytes = await user.avatar.read()
                    except:
                        pass
                
                users_data.append((i, username, bal, avatar_bytes))

            # Görseli asenkron olarak oluştur
            buffer = await self.bot.loop.run_in_executor(None, self.generate_leaderboard_image, users_data)
            
            file = discord.File(buffer, filename="liderlik.png")
            await ctx.send(file=file)

    @tasks.loop(time=time(0, 5, tzinfo=timezone.utc))
    async def monthly_check(self):
        """Her ayın 1'inde çalışacak periyodik görev."""
        if datetime.now().day == 1:
            # Buraya aylık sıfırlama veya ödül mantığı eklenebilir
            pass

async def setup(bot):
    await bot.add_cog(Economy(bot))
