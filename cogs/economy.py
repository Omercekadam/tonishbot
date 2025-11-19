import discord
from discord.ext import commands, tasks
import aiosqlite
import random
import os
import io
from datetime import datetime, time, timezone
from PIL import Image, ImageDraw, ImageFont

DB_PATH = "economy.db"

class BlackjackView(discord.ui.View):
    """
    Blackjack oyunu için interaktif görünüm.
    Kart çekme (Hit) ve Durma (Stand) butonlarını içerir.
    """
    def __init__(self, ctx, bet, cog):
        super().__init__(timeout=60.0) # 60 saniye süre sınırı
        self.ctx = ctx
        self.bet = bet
        self.cog = cog
        self.player_hand = []
        self.dealer_hand = []
        # 52 kartlık deste oluştur
        self.deck = [
            (face, suit) 
            for _ in range(4) 
            for suit in ['♠️', '♥️', '♦️', '♣️'] 
            for face in ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']
        ]
        random.shuffle(self.deck)
        # Başlangıç kartlarını dağıt
        self.player_hand.append(self.deck.pop())
        self.player_hand.append(self.deck.pop())
        self.dealer_hand.append(self.deck.pop())
        self.message = None

    def calculate_hand(self, hand):
        """Eldeki kartların toplam değerini hesaplar."""
        values = {'2':2, '3':3, '4':4, '5':5, '6':6, '7':7, '8':8, '9':9, '10':10, 'J':10, 'Q':10, 'K':10, 'A':11}
        score = sum(values[card[0]] for card in hand)
        aces = sum(1 for card in hand if card[0] == 'A')
        # As varsa ve toplam 21'i geçiyorsa As'ı 1 olarak say
        while score > 21 and aces:
            score -= 10
            aces -= 1
        return score

    def format_hand(self, hand):
        """Kartları okunabilir string formatına çevirir."""
        return ", ".join(f"{c[0]}{c[1]}" for c in hand)

    async def update_game(self, end=False, result_text=""):
        """Oyun durumunu günceller ve mesajı düzenler."""
        p_score = self.calculate_hand(self.player_hand)
        d_card = f"{self.dealer_hand[0][0]}{self.dealer_hand[0][1]}"
        
        embed = discord.Embed(title="Blackjack ♠️", color=discord.Color.blue())
        embed.add_field(name="Senin Elin", value=f"{self.format_hand(self.player_hand)} ({p_score})", inline=False)
        
        if end:
            # Oyun bittiyse kurpiyerin elini göster
            d_score = self.calculate_hand(self.dealer_hand)
            embed.add_field(name="Kurpiyerin Eli", value=f"{self.format_hand(self.dealer_hand)} ({d_score})", inline=False)
            embed.description = result_text
            self.stop() # Butonları devre dışı bırak
            await self.message.edit(embed=embed, view=None)
        else:
            # Oyun devam ediyorsa sadece kurpiyerin açık kartını göster
            embed.add_field(name="Kurpiyer", value=f"{d_card}", inline=False)
            await self.message.edit(embed=embed, view=self)

    @discord.ui.button(label="Hit", style=discord.ButtonStyle.green)
    async def hit(self, interaction, button):
        """Kart çekme butonu."""
        if interaction.user.id != self.ctx.author.id: return
        self.player_hand.append(self.deck.pop())
        if self.calculate_hand(self.player_hand) > 21:
            # 21'i geçti, kaybettin
            await self.cog.update_balance(self.ctx.author.id, -self.bet)
            await self.update_game(True, f"💥 Yandın! **{self.bet}** kaybettin.")
        else:
            await interaction.response.defer()
            await self.update_game()

    @discord.ui.button(label="Stand", style=discord.ButtonStyle.red)
    async def stand(self, interaction, button):
        """Durma butonu."""
        if interaction.user.id != self.ctx.author.id: return
        await interaction.response.defer()
        
        # Kurpiyer 17 olana kadar kart çeker
        while self.calculate_hand(self.dealer_hand) < 17:
            self.dealer_hand.append(self.deck.pop())
            
        p_score = self.calculate_hand(self.player_hand)
        d_score = self.calculate_hand(self.dealer_hand)
        
        # Sonuçları karşılaştır
        if d_score > 21 or p_score > d_score:
            win = self.bet * 2
            await self.cog.update_balance(self.ctx.author.id, win)
            await self.update_game(True, f"🎉 Kazandın! **{win}** coin aldın.")
        elif d_score > p_score:
            await self.cog.update_balance(self.ctx.author.id, -self.bet)
            await self.update_game(True, f"😥 Kaybettin. **{self.bet}** coin gitti.")
        else:
            await self.update_game(True, "Berabere! Bahsin iade.")

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monthly_check.start() # Aylık kontrol görevini başlat

    async def cog_load(self):
        """Eklenti yüklendiğinde veritabanı tablosunu oluştur."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("CREATE TABLE IF NOT EXISTS economy (user_id INTEGER PRIMARY KEY, balance INTEGER DEFAULT 100)")
            await db.commit()

    async def get_balance(self, user_id):
        """Kullanıcının bakiyesini getirir."""
        async with aiosqlite.connect(DB_PATH) as db:
            # Kullanıcı yoksa oluştur
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user_id,))
            await db.commit()
            async with db.execute("SELECT balance FROM economy WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 100

    async def update_balance(self, user_id, amount):
        """Kullanıcının bakiyesini günceller (Ekleme/Çıkarma)."""
        async with aiosqlite.connect(DB_PATH) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user_id,))
            await db.execute("UPDATE economy SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    @commands.command()
    async def bakiye(self, ctx, member: discord.Member = None):
        """Kullanıcının bakiyesini gösterir."""
        member = member or ctx.author
        bal = await self.get_balance(member.id)
        await ctx.send(f"{member.display_name}: **{bal}** tonish coin 💸")

    @commands.command()
    @commands.cooldown(1, 86400, commands.BucketType.user) # 24 saatte bir
    async def gunluk(self, ctx):
        """Günlük ödül (50 coin) verir."""
        await self.update_balance(ctx.author.id, 50)
        bal = await self.get_balance(ctx.author.id)
        await ctx.send(f"Günlük 50 coin aldın! Yeni bakiye: **{bal}**")

    @commands.command()
    async def blackjack(self, ctx, bet: int):
        """Blackjack oyunu başlatır."""
        if bet <= 0: return await ctx.send("Geçersiz bahis.")
        bal = await self.get_balance(ctx.author.id)
        if bal < bet: return await ctx.send("Yetersiz bakiye.")
        
        view = BlackjackView(ctx, bet, self)
        view.message = await ctx.send("Blackjack başlıyor...", view=view)
        await view.update_game()

    @commands.command()
    async def slot(self, ctx, bet: int):
        """Slot makinesi oyunu."""
        if bet <= 0: return await ctx.send("Geçersiz bahis.")
        bal = await self.get_balance(ctx.author.id)
        if bal < bet: return await ctx.send("Yetersiz bakiye.")
        
        await self.update_balance(ctx.author.id, -bet)
        symbols = ['🍒', '🍑', '🎮', '7️⃣']
        result = [random.choice(symbols) for _ in range(3)]
        
        win = 0
        # Kazanma kombinasyonları
        if result[0] == result[1] == result[2]:
            win = bet * (100 if result[0] == '7️⃣' else 10)
        elif result.count('🍒') == 2:
            win = bet * 2
            
        if win > 0:
            await self.update_balance(ctx.author.id, win)
            msg = f"🎉 Kazandın! **{win}** coin."
        else:
            msg = "Kaybettin..."
            
        await ctx.send(f"🎰 | {' '.join(result)} | \n{msg}")

    @commands.command()
    async def liderlik(self, ctx):
        """En zengin 5 kullanıcıyı listeler."""
        async with aiosqlite.connect(DB_PATH) as db:
            async with db.execute("SELECT user_id, balance FROM economy ORDER BY balance DESC LIMIT 5") as cursor:
                rows = await cursor.fetchall()
        
        if not rows: return await ctx.send("Liste boş.")
        
        desc = ""
        for i, (uid, bal) in enumerate(rows, 1):
            desc += f"**#{i}** <@{uid}> - {bal} coin\n"
            
        embed = discord.Embed(title="🏆 Liderlik Tablosu", description=desc, color=discord.Color.gold())
        await ctx.send(embed=embed)

    @tasks.loop(time=time(0, 5, tzinfo=timezone.utc))
    async def monthly_check(self):
        """Her ayın 1'inde çalışacak periyodik görev."""
        if datetime.now().day == 1:
            # Buraya aylık sıfırlama veya ödül mantığı eklenebilir
            pass

async def setup(bot):
    await bot.add_cog(Economy(bot))
