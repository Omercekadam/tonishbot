import discord
from discord.ext import commands, tasks
import aiosqlite
import random
import os
import io
from datetime import datetime, time, timezone
from PIL import Image, ImageDraw, ImageFont

DB_PATH = "economy.db"
LEADERBOARD_BG = "liderlik_bg.png"
FONT_BOLD = "Roboto-Bold.ttf"
FONT_REGULAR = "Roboto-Regular.ttf"

KART_DEGERLERI = {
    '2': 2, '3': 3, '4': 4, '5': 5, '6': 6, '7': 7, '8': 8, '9': 9, '10': 10,
    'J': 10, 'Q': 10, 'K': 10, 'A': 11
}

SUITS = ['♠️', '♥️', '♦️', '♣️']
FACES = ['2', '3', '4', '5', '6', '7', '8', '9', '10', 'J', 'Q', 'K', 'A']

SLOT_SEMBOLLERI = ['🍒', '🍑', '7️⃣', '🍋', '🍇', '🔔', '💎']
SLOT_AGIRLIKLARI = [30, 30, 5, 20, 20, 10, 2]
SLOT_KAZANCLARI = {
    '🍒': 2, '🍑': 2, '7️⃣': 100, '🍋': 3, '🍇': 3, '🔔': 10, '💎': 50
}

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
    def __init__(self, ctx, bet: int, cog):
        super().__init__(timeout=600.0)
        self.ctx = ctx
        self.bet = bet
        self.cog = cog
        self.message = None

    async def on_timeout(self):
        """10 dakika sonra butonları kaldırır."""
        disabled_embed = discord.Embed(
            title="Slot Makinesi 🎰 (Zaman Aşımı)",
            description=f"Bu makine 10 dakika boyunca kullanılmadığı için kapandı.\n"
                        f"Yeniden oynamak için `!slot [bahis]` komutunu kullan.",
            color=discord.Color.dark_grey()
        )
        if self.message:
            await self.message.edit(embed=disabled_embed, view=None)

    @discord.ui.button(label="Çevir! 🎰", style=discord.ButtonStyle.green, custom_id="slot_spin_button")
    async def çevir_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message(
                "Bu senin slot makinen değil! 😠 Kendi makineni açmak için `!slot [bahis]` yaz.", 
                ephemeral=True
            )
            return

        await interaction.response.defer()

        # Bakiye Kontrolü
        user_id = self.ctx.author.id
        balance = await self.cog.get_balance(user_id)

        if balance < self.bet:
            await interaction.followup.send(
                f"Yetersiz bakiye! 😥 Oynamak için **{self.bet}** tonish coin'e ihtiyacın var. "
                f"Mevcut bakiyen: **{balance}**\nParan olunca tekrar dene!", 
                ephemeral=True
            )
            return

        await self.cog.update_balance(user_id, -self.bet)

        # Slot Çevirme
        spin_sonucu = random.choices(SLOT_SEMBOLLERI, weights=SLOT_AGIRLIKLARI, k=3)
        sonuc_str = f"**[ {spin_sonucu[0]} | {spin_sonucu[1]} | {spin_sonucu[2]} ]**"

        #Kazanç Hesaplama
        kazanc = 0
        sonuc_mesaji = ""
        s1, s2, s3 = spin_sonucu[0], spin_sonucu[1], spin_sonucu[2]
        embed_color = discord.Color.dark_grey()

        if s1 == s2 == s3:
            kazanan_sembol = s1
            kazanc_carpani = SLOT_KAZANCLARI.get(kazanan_sembol, 5)
            kazanc = self.bet * kazanc_carpani
            
            if kazanan_sembol == '7️⃣':
                sonuc_mesaji = f"🎉 **JACKPOT!** 🎉 \n**{kazanc}** tonish coin kazandın!"
                embed_color = discord.Color.red()
            else:
                sonuc_mesaji = f"Tebrikler! 3'lü ({kazanan_sembol}) yakaladın.🥳\n**{kazanc}** tonish coin kazandın!"
                embed_color = discord.Color.green()
                
        elif spin_sonucu.count('🍒') == 2:
            kazanc_carpani = 2
            kazanc = self.bet * kazanc_carpani
            sonuc_mesaji = f"İki kiraz! 🍒\n**{kazanc}** tonish coin kazandın!"
            embed_color = discord.Color.green()
        
        elif spin_sonucu.count('🍑') == 2:
            kazanc_carpani = 2
            kazanc = self.bet * kazanc_carpani
            sonuc_mesaji = f"İki şeftali! 🍑\n**{kazanc}** tonish coin kazandın!"
            embed_color = discord.Color.green()

        else:
            sonuc_mesaji = f"Maalesef kaybettin... Bir dahaki sefere! 😥"
            embed_color = discord.Color.dark_grey()

        # Veritabanını Güncelle
        if kazanc > 0:
            await self.cog.update_balance(user_id, kazanc)

        yeni_bakiye = await self.cog.get_balance(user_id)

        # Embedi Güncelle
        new_embed = discord.Embed(
            title="Slot Makinesi 🎰",
            description=f"Her çevirme: **{self.bet}** tonish coin\n\n"
                        f"{sonuc_str}\n\n"
                        f"{sonuc_mesaji}",
            color=embed_color
        )
        new_embed.set_footer(text=f"Yeni bakiyen: {yeni_bakiye} | Tekrar oynamak için 'Çevir!'")
        
        author = self.ctx.author
        if author.avatar:
            new_embed.set_author(name=f"{author.display_name}", icon_url=author.avatar.url)
        else:
            new_embed.set_author(name=f"{author.display_name}")
        
        await interaction.edit_original_response(embed=new_embed, view=self)

class SystemBreakerSession:
    def __init__(self, user_id):
        self.user_id = user_id
        self.secret_code = self.generate_code()
        self.attempts_left = 10
        self.history = []  # List of (guess, green, yellow)
        self.hints_left = 3
        self.revealed_indices = set()

    def generate_code(self):
        """0-9 arası 5 benzersiz rakam seçer."""
        digits = list("0123456789")
        random.shuffle(digits)
        return "".join(digits[:5])

    def check_guess(self, guess):
        """Tahmini kontrol eder ve (green, yellow) döner."""
        green = 0
        yellow = 0
        for i, char in enumerate(guess):
            if char == self.secret_code[i]:
                green += 1
            elif char in self.secret_code:
                yellow += 1
        return green, yellow

    def get_hint(self):
        """Rastgele bir ipucu (index, digit) döner."""
        if self.hints_left <= 0:
            return None
        
        unrevealed = [i for i in range(5) if i not in self.revealed_indices]
        if not unrevealed:
            return None
            
        idx = random.choice(unrevealed)
        self.revealed_indices.add(idx)
        self.hints_left -= 1
        return idx, self.secret_code[idx]

    def get_revealed_str(self):
        """Bilinen kısımları string olarak döner (Örn: 1 _ 3 _ _)."""
        chars = []
        for i in range(5):
            if i in self.revealed_indices:
                chars.append(self.secret_code[i])
            else:
                chars.append("_")
        return " ".join(chars)

class SystemBreakerView(discord.ui.View):
    def __init__(self, ctx, cog, game):
        super().__init__(timeout=300)
        self.ctx = ctx
        self.cog = cog
        self.game = game
        self.update_button_label()

    def update_button_label(self):
        self.children[0].label = f"💡 İpucu Al ({self.game.hints_left})"
        self.children[0].disabled = self.game.hints_left <= 0

    @discord.ui.button(label="💡 İpucu Al", style=discord.ButtonStyle.blurple)
    async def hint_button(self, interaction: discord.Interaction, button: discord.ui.Button):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Bu senin oyunun değil!", ephemeral=True)
            return

        hint = self.game.get_hint()
        if not hint:
            await interaction.response.send_message("İpucu hakkın kalmadı veya hepsi açık!", ephemeral=True)
            return

        idx, digit = hint
        self.update_button_label()
        
        # Embed güncelleme
        embed = interaction.message.embeds[0]
        
        # İpucu alanını güncelle veya ekle
        hint_str = self.game.get_revealed_str()
        
        # Mevcut description'ı koru ama ipucu bilgisini ekle
        # Description'ı parse etmek yerine yeni bir field ekleyelim veya güncelleyelim
        
        # Field kontrolü
        found_field = False
        for i, field in enumerate(embed.fields):
            if field.name == "🔍 Bilinen Şifre Parçaları":
                embed.set_field_at(i, name="🔍 Bilinen Şifre Parçaları", value=f"`{hint_str}`", inline=False)
                found_field = True
                break
        
        if not found_field:
            embed.add_field(name="🔍 Bilinen Şifre Parçaları", value=f"`{hint_str}`", inline=False)

        await interaction.response.edit_message(embed=embed, view=self)
        await interaction.followup.send(f"İpucu: **{idx+1}. hane {digit}**!", ephemeral=True)

class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.monthly_check.start()
        self.system_breaker_games = {} # user_id -> SystemBreakerSession 

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

    @commands.command(name="bakiyeguncelle")
    @commands.has_permissions(administrator=True)
    async def bakiyeguncelle(self, ctx, member: discord.Member, amount: int):
        """Belirtilen kullanıcının bakiyesini 'amount' kadar artırır/azaltır. (Yönetici komutu)"""
        
        # Önce güncelle
        await self.update_balance(member.id, amount)
        # Sonra yeni bakiyeyi al
        new_balance = await self.get_balance(member.id)
        
        await ctx.send(f"✅ {member.display_name} kullanıcısının yeni bakiyesi: **{new_balance}** tonish coin 💸")

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

    @commands.command(name="slot")
    async def slot(self, ctx, bet: int):
        """Slot makinesini interaktif bir butonla başlatır."""
        
        if bet <= 0:
            await ctx.send("Lütfen geçerli bir bahis miktarı gir (0'dan büyük).")
            return
            
        balance = await self.get_balance(ctx.author.id)
        
        if balance < bet:
            await ctx.send(f"Yetersiz bakiye! 😥 Oynamak için **{bet}** tonish coin'e ihtiyacın var. Mevcut bakiyen: **{balance}**")
            return

        view = SlotView(ctx, bet, self)
        
        embed = discord.Embed(
            title="Slot Makinesi 🎰",
            description=f"Her 'Çevir!' tuşuna basış **{bet}** tonish coin'e mal olacak.\n\n"
                        "Bol şans! ✨",
            color=discord.Color.gold()
        )
        
        if ctx.author.avatar:
            embed.set_author(name=f"{ctx.author.display_name} makineye oturdu!", icon_url=ctx.author.avatar.url)
        else:
            embed.set_author(name=f"{ctx.author.display_name} makineye oturdu!")
        
        embed.set_footer(text=f"Bu makine 10 dakika sonra kaybolacak.")
        
        message = await ctx.send(embed=embed, view=view)
        
        view.message = message

    @commands.command(name="sistemkirici", aliases=["hacker", "hardcore"])
    async def sistem_kirici(self, ctx):
        """Sistem Kırıcı (Hardcore Mod) oyununu başlatır. Giriş: 100 Coin."""
        user_id = ctx.author.id
        
        # Zaten oyunda mı?
        if user_id in self.system_breaker_games:
            await ctx.send("Zaten devam eden bir 'Sistem Kırıcı' görevin var! `!tahmin <sayı>` ile devam et.")
            return

        # Bakiye kontrolü
        balance = await self.get_balance(user_id)
        entry_fee = 100
        if balance < entry_fee:
            await ctx.send(f"Yetersiz bakiye! 🚫 Bu göreve girmek için **{entry_fee}** tonish coin gerekiyor. Mevcut: **{balance}**")
            return

        # Ücreti al ve oyunu başlat
        await self.update_balance(user_id, -entry_fee)
        self.system_breaker_games[user_id] = SystemBreakerSession(user_id)
        
        embed = discord.Embed(
            title="💻 SİSTEM KIRICI (HARDCORE) BAŞLADI",
            description=f"**Hedef:** 5 Haneli Şifreyi Çöz (Rakamlar benzersiz!)\n"
                        f"**Hak:** 10 Deneme\n"
                        f"**Ödül:** Kalan hakka göre artar!\n\n"
                        f"Tahmin yapmak için: `!tahmin 12345` yaz.",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text="Sistem güvenliği: YÜKSEK 🔒")
        
        view = SystemBreakerView(ctx, self, self.system_breaker_games[user_id])
        await ctx.send(embed=embed, view=view)

    @commands.command(name="tahmin")
    async def tahmin(self, ctx, guess: str):
        """Sistem Kırıcı oyunu için tahmin yap."""
        user_id = ctx.author.id
        
        if user_id not in self.system_breaker_games:
            await ctx.send("Aktif bir 'Sistem Kırıcı' oyunun yok. `!sistemkirici` yazarak başla!")
            return

        game = self.system_breaker_games[user_id]
        
        # Validasyon
        if not guess.isdigit() or len(guess) != 5:
            await ctx.send("⚠️ Hata: Şifre **5 rakamdan** oluşmalı! (Örn: 80294)")
            return
        
        if len(set(guess)) != 5:
            await ctx.send("⚠️ Hata: Şifredeki rakamlar **birbirinden farklı** olmalı!")
            return

        # Tahmini işle
        game.attempts_left -= 1
        green, yellow = game.check_guess(guess)
        game.history.append((guess, green, yellow))

        # KAZANDI MI?
        if green == 5:
            # Ödül Hesaplama: 200 + (Kalan Hak x 100 / 2)
            bonus = (game.attempts_left * 100) // 2
            total_reward = 200 + bonus
            
            await self.update_balance(user_id, total_reward)
            del self.system_breaker_games[user_id]
            
            embed = discord.Embed(
                title="🔓 SİSTEM HACKLENDİ! BAŞARILI!",
                description=f"**Şifre:** `{guess}`\n"
                            f"**Kalan Hak:** {game.attempts_left}\n"
                            f"**Kazanç:** {total_reward} tonish coin 💰",
                color=discord.Color.green()
            )
            await ctx.send(embed=embed)
            return

        # KAYBETTİ Mİ?
        if game.attempts_left <= 0:
            secret = game.secret_code
            del self.system_breaker_games[user_id]
            
            embed = discord.Embed(
                title="🚫 SİSTEM KİLİTLENDİ! BAŞARISIZ!",
                description=f"Hakkın bitti. Sistem kendini imha etti.\n"
                            f"**Doğru Şifre:** `{secret}`",
                color=discord.Color.red()
            )
            await ctx.send(embed=embed)
            return

        # DEVAM EDİYOR - Durum Göster
        history_text = ""
        for g, gr, ye in game.history:
            history_text += f"`{g}` -> 🟩{gr} 🟨{ye}\n"

        embed = discord.Embed(
            title=f"Sistem Analizi 📟 (Kalan Hak: {game.attempts_left})",
            description=f"Son Tahmin: `{guess}`\n\n"
                        f"**Geçmiş Tahminler:**\n{history_text}",
            color=discord.Color.orange()
        )
        
        # İpuçlarını göster
        if game.revealed_indices:
            embed.add_field(name="🔍 Bilinen Şifre Parçaları", value=f"`{game.get_revealed_str()}`", inline=False)
            
        view = SystemBreakerView(ctx, self, game)
        await ctx.send(embed=embed, view=view)

    def create_circular_mask(self, size):
        mask = Image.new("L", size, 0)
        draw = ImageDraw.Draw(mask)
        draw.ellipse((0, 0) + size, fill=255)
        return mask

    def generate_leaderboard_image(self, users_data):
        """
        Liderlik tablosu için görsel oluşturur.
        users_data: [(rank, user_display_name, balance, avatar_bytes), ...]
        """
        try:
            bg = Image.open(LEADERBOARD_BG).convert("RGBA")
        except Exception as e:
            print(f"Arkaplan yüklenemedi: {e}")
            bg = Image.new("RGBA", (800, 600), (44, 47, 51, 255))

        draw = ImageDraw.Draw(bg)

        try:
            font_isim = ImageFont.truetype(FONT_BOLD, 36)
            font_bakiye = ImageFont.truetype(FONT_REGULAR, 28)
            font_rank = ImageFont.truetype(FONT_BOLD, 40)
        except IOError:
            font_isim = ImageFont.load_default()
            font_bakiye = ImageFont.load_default()
            font_rank = ImageFont.load_default()

        # Koordinatlar
        current_y = 150 
        y_step = 100 
        rank_x = 50      
        avatar_x = 120   
        name_x = 270     
        balance_x = 270 
        avatar_size = (80, 80)
        
        mask = self.create_circular_mask(avatar_size)

        for rank, username, balance, avatar_bytes in users_data:
            # Avatar İşlemleri
            if avatar_bytes:
                try:
                    avatar_img = Image.open(io.BytesIO(avatar_bytes)).convert("RGBA")
                    avatar_img = avatar_img.resize(avatar_size)
                    bg.paste(avatar_img, (avatar_x, current_y), mask)
                except Exception as e:
                    print(f"Avatar işleme hatası: {e}")
            
            # Yazı İşlemleri
            draw.text((rank_x, current_y + 15), f"#{rank}", font=font_rank, fill="#F4E400") 
            draw.text((name_x, current_y + 5), str(username), font=font_isim, fill="#171717")
            draw.text((balance_x, current_y + 45), f"{balance} tonish coin", font=font_bakiye, fill="#171717")

            current_y += y_step

        buffer = io.BytesIO()
        bg.save(buffer, format="PNG")
        buffer.seek(0)
        return buffer

    @commands.command(name="liderlik", aliases=["zenginler", "top", "leaderboard"])
    async def leaderboard(self, ctx):
        """tonish coin liderlik tablosunu GÖRSEL olarak oluşturur."""
        
        loading_msg = await ctx.send("Liderlik tablosu oluşturuluyor... 🎨")

        try:
            # 1. Veritabanından ilk 5 kişiyi çek
            async with aiosqlite.connect(DB_PATH) as db:
                async with db.execute("SELECT user_id, balance FROM economy ORDER BY balance DESC LIMIT 5") as cursor:
                    rows = await cursor.fetchall()

            if not rows:
                await loading_msg.edit(content="Henüz liderlik tablosunda kimse yok.")
                return

            # 2. Verileri Hazırla (Avatar indirme vs. async yapılmalı)
            users_data = []
            for i, (uid, bal) in enumerate(rows, 1):
                try:
                    user = await self.bot.fetch_user(uid)
                    username = user.display_name
                    
                    avatar_bytes = None
                    if user.display_avatar:
                        try:
                            avatar_bytes = await user.display_avatar.read()
                        except:
                            pass
                except discord.NotFound:
                    username = "Bilinmeyen Kullanıcı"
                    avatar_bytes = None
                except Exception as e:
                    print(f"Kullanıcı getirme hatası {uid}: {e}")
                    username = "Hata"
                    avatar_bytes = None
                
                users_data.append((i, username, bal, avatar_bytes))

            # 3. Resmi Oluştur (Bloklayan işlem olduğu için executor'da çalıştır)
            buffer = await self.bot.loop.run_in_executor(None, self.generate_leaderboard_image, users_data)

            # 4. Gönder
            file = discord.File(buffer, filename="liderlik.png")
            await ctx.send(file=file)
            await loading_msg.delete()

        except Exception as e:
            print(f"Liderlik tablosu hatası: {e}")
            await loading_msg.edit(content=f"Bir hata oluştu: {e}")

    @tasks.loop(time=time(0, 5, tzinfo=timezone.utc))
    async def monthly_check(self):
        """Her ayın 1'inde çalışacak periyodik görev."""
        if datetime.now().day == 1:
            # Buraya aylık sıfırlama veya ödül mantığı eklenebilir
            pass

async def setup(bot):
    await bot.add_cog(Economy(bot))
