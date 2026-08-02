import discord
from discord.ext import commands
import aiosqlite
import random
import io
import json
import logging
import time
import asyncio
from datetime import datetime
from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

DB_PATH = "economy.db"
LEADERBOARD_BG = "liderlik_bg.png"
FONT_BOLD = "Roboto-Bold.ttf"
FONT_REGULAR = "Roboto-Regular.ttf"

# SQLite kilit bekleme süresi (saniye) — eşzamanlı komutlarda "database is locked" önler
DB_TIMEOUT = 30

# !gunluk ayarları (bellek yerine veritabanında tutulur, restart'a dayanıklı)
DAILY_AMOUNT = 50
DAILY_COOLDOWN = 86400  # 24 saat

# Terk edilmiş Sistem Kırıcı oturumu bu süreden sonra bayat sayılır
SB_SESSION_TIMEOUT = 1800  # 30 dakika

# Oyun giriş ücretleri
ZINDAN_UCRETI = 50
SISTEMKIRICI_UCRETI = 100

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

def create_health_bar(current, max_hp, length=10):
    """Görsel can barı oluşturur."""
    pct = current / max_hp
    filled = int(pct * length)
    bar = "🟩" * filled + "⬜" * (length - filled)
    return bar

class DungeonGame(discord.ui.View):
    def __init__(self, ctx, cog):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.cog = cog
        self.message = None
        
        # Oyuncu Statları
        self.player_max_hp = 100
        self.player_hp = 100
        self.potions = 2
        self.turn_count = 1
        self.log = "50 Tonishcoin vererek zindan muhafızını kandırdın vs savaş başladı! Hamleni seç."
        
        # Düşman Seçimi
        roll = random.random()
        if roll < 0.40:
            self.enemy = {
                "name": "Hırsız Goblin", "icon": "👺", "hp": 70, "max_hp": 70,
                "min_dmg": 8, "max_dmg": 15, "reward":70, "color": discord.Color.green()
            }
        elif roll < 0.80:
            self.enemy = {
                "name": "Savaşçı Ork", "icon": "👹", "hp": 110, "max_hp": 110,
                "min_dmg": 10, "max_dmg": 18, "reward": 150, "color": discord.Color.dark_orange()
            }
        else:
            self.enemy = {
                "name": "Karanlık Şövalye", "icon": "💀", "hp": 150, "max_hp": 150,
                "min_dmg": 11, "max_dmg": 22, "reward": 400, "color": discord.Color.dark_grey()
            }

    async def update_display(self, game_over=False, win=False):
        enemy_bar = create_health_bar(self.enemy["hp"], self.enemy["max_hp"])
        player_bar = create_health_bar(self.player_hp, self.player_max_hp)
        
        desc = (
            f"**{self.enemy['icon']} {self.enemy['name']}**\n"
            f"{enemy_bar} **{self.enemy['hp']}/{self.enemy['max_hp']} HP**\n\n"
            f"**👤 Maceracı (Sen)**\n"
            f"{player_bar} **{self.player_hp}/{self.player_max_hp} HP** | 🧪 İksir: {self.potions}/2\n\n"
            f"📜 **Savaş Günlüğü:**\n{self.log}"
        )
        
        color = self.enemy["color"]
        if game_over:
            color = discord.Color.green() if win else discord.Color.red()
            self.stop()
            self.clear_items()
            self.cog.finish_game(self.ctx.author.id)

        embed = discord.Embed(title=f"⚔️ ZİNDAN SAVAŞI - TUR {self.turn_count}", description=desc, color=color)
        embed.set_footer(text=f"Oyuncu: {self.ctx.author.display_name}", icon_url=self.ctx.author.avatar.url if self.ctx.author.avatar else None)
        
        if self.message:
            await self.message.edit(embed=embed, view=None if game_over else self)
        else:
            self.message = await self.ctx.send(embed=embed, view=self)

    async def on_timeout(self):
        """Oyuncu 3 dakika hamle yapmazsa savaşı terk etmiş sayılır."""
        self.cog.finish_game(self.ctx.author.id)
        if self.message:
            try:
                embed = discord.Embed(
                    title="⌛ ZİNDAN TERK EDİLDİ",
                    description="Uzun süre hamle yapmadın, zindandan sürüklenerek çıkarıldın. "
                                "Giriş ücreti iade edilmez.",
                    color=discord.Color.dark_grey(),
                )
                await self.message.edit(embed=embed, view=None)
            except discord.HTTPException:
                log.exception("Zindan zaman aşımı mesajı güncellenemedi")

    async def enemy_turn(self, player_defending=False):
        if self.enemy["hp"] <= 0:
            return # Düşman öldü, saldıramaz

        dmg = random.randint(self.enemy["min_dmg"], self.enemy["max_dmg"])
        
        if player_defending:
            reduction_rate = random.randint(60, 100)
            reduced_dmg = int(dmg * (100 - reduction_rate) / 100)
            self.log += f"\n🛡️ Kalkanın hasarın %{reduction_rate}'ını engelledi! ({dmg} -> {reduced_dmg})"
            dmg = reduced_dmg
        else:
            self.log += f"\n💥 {self.enemy['name']} sana {dmg} hasar vurdu!"
            
        self.player_hp -= dmg
        if self.player_hp < 0: self.player_hp = 0

    async def check_game_over(self):
        if self.enemy["hp"] <= 0:
            self.enemy["hp"] = 0
            reward = self.enemy["reward"]
            self.log += f"\n\n🏆 **KAZANDIN!** Düşmanı yendin ve **{reward}** tonish coin kazandın!"
            await self.cog.update_balance(self.ctx.author.id, reward)
            await self.update_display(game_over=True, win=True)
            return True
            
        if self.player_hp <= 0:
            self.log += f"\n\n💀 **ÖLDÜN...** Cesedin zindanda çürüyecek."
            await self.update_display(game_over=True, win=False)
            return True
            
        return False

    async def process_turn(self, interaction, action_type):
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message("Bu senin savaşın değil!", ephemeral=True)
            return
        
        await interaction.response.defer()
        self.log = "" # Günlüğü temizle
        player_defending = False
        
        # 1. OYUNCU HAMLESİ
        if action_type == "attack":
            if random.random() < 0.10:
                self.log += f"💨 Saldırı denedin ama **ISKALADIN!** Dengen bozuldu!"
                # Ceza: Düşman kritik vuracak (Enemy turn'de halledilir)
                # Basitlik için burada flag koymuyorum, sadece hasar yok.
            else:
                dmg = random.randint(7, 18)
                self.enemy["hp"] -= dmg
                self.log += f"⚔️ Saldırdın ve **{dmg}** hasar verdin!"
            
        elif action_type == "heavy":
            if random.random() < 0.45: # %55 Miss
                self.log += f"💨 Ağır darbe denedin ama **ISKALADIN!** Dengen bozuldu!"
                # Ceza: Düşman kritik vuracak (Enemy turn'de halledilir)
                # Basitlik için burada flag koymuyorum, sadece hasar yok.
            else:
                dmg = random.randint(20, 35)
                self.enemy["hp"] -= dmg
                self.log += f"🔨 **BAM!** Ağır darbe ile **{dmg}** hasar verdin!"
                
        elif action_type == "defend":
            player_defending = True
            self.log += f"🛡️ Savunma pozisyonuna geçtin. Gelecek hasarı karşılamaya hazırsın!"
            
        elif action_type == "potion":
            if self.potions > 0:
                self.potions -= 1
                heal = random.randint(20, 50)
                self.player_hp = min(self.player_max_hp, self.player_hp + heal)
                self.log += f"🧪 İksiri kafana diktin. (+{heal} HP)"
            else:
                self.log += f"🚫 İksirin kalmadı! Boşa hamle yaptın..."

        # 2. DÜŞMAN ÖLÜM KONTROLÜ
        if await self.check_game_over(): return

        # 3. DÜŞMAN HAMLESİ
        await self.enemy_turn(player_defending)

        # 4. OYUNCU ÖLÜM KONTROLÜ
        if await self.check_game_over(): return

        # 5. GÜNCELLEME
        self.turn_count += 1
        await self.update_display()

    @discord.ui.button(label="Saldır", style=discord.ButtonStyle.red, emoji="⚔️")
    async def btn_attack(self, interaction, button):
        await self.process_turn(interaction, "attack")

    @discord.ui.button(label="Ağır Darbe", style=discord.ButtonStyle.danger, emoji="🔨")
    async def btn_heavy(self, interaction, button):
        await self.process_turn(interaction, "heavy")

    @discord.ui.button(label="Savun", style=discord.ButtonStyle.blurple, emoji="🛡️")
    async def btn_defend(self, interaction, button):
        await self.process_turn(interaction, "defend")

    @discord.ui.button(label="İksir", style=discord.ButtonStyle.green, emoji="🧪")
    async def btn_potion(self, interaction, button):
        await self.process_turn(interaction, "potion")

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
        # Bahis oyun başında escrow'a alındı. Zaman aşımı = pes etme, bahis yanar.
        # (Eskiden hiçbir kesinti yapılmadığı için oyuncular kötü eli bekleyip
        #  bedava çıkabiliyordu.)
        self.cog.finish_game(self.ctx.author.id)
        if self.message:
            try:
                await self.message.edit(
                    content=f"⌛ Zaman aşımı! Hamle yapmadığın için el düştü, "
                            f"**{self.bet}** tonish coin yandı.",
                    view=None, embed=None,
                )
            except discord.HTTPException:
                log.exception("Blackjack zaman aşımı mesajı güncellenemedi")

    async def update_message(self, content, game_over=False):
        """Oyun durumunu gösteren mesajı günceller."""
        if game_over:
            self.stop()
            self.cog.finish_game(self.ctx.author.id)
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
            # Bahis oyun başında düşüldü; kaybedince ek bir kesinti yok.
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

        # Bahis oyun başında escrow'a alındı. Buradaki tüm hareketler İADE/ÖDÜL:
        #   kazanç  -> 2x bahis geri yatar (bahis + eşit kazanç, net +bahis)
        #   berabere -> sadece bahis geri yatar (net 0)
        #   kayıp   -> hiçbir şey yatmaz (net -bahis)
        if dealer_score > 21:
            await self.cog.update_balance(self.ctx.author.id, self.bet * 2)
            result_message += f"**Kurpiyer Yandı!** Sen kazandın 🎉 **{self.bet}** tonish coin kâr ettin."
        elif player_score > dealer_score:
            await self.cog.update_balance(self.ctx.author.id, self.bet * 2)
            result_message += f"**Kazandın!** 🎉 **{self.bet}** tonish coin kâr ettin."
        elif dealer_score > player_score:
            result_message += f"**Kaybettin...** 😥 **{self.bet}** tonish coin kaybettin."
        else:
            await self.cog.update_balance(self.ctx.author.id, self.bet)
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

        # Bahsi tek atomik işlemde düş — yetersizse hiçbir şey değişmez.
        # (Hızlı çift tıklamada çift harcamayı ve eksi bakiyeyi engeller.)
        user_id = self.ctx.author.id
        if not await self.cog.try_spend(user_id, self.bet):
            balance = await self.cog.get_balance(user_id)
            await interaction.followup.send(
                f"Yetersiz bakiye! 😥 Oynamak için **{self.bet}** tonish coin'e ihtiyacın var. "
                f"Mevcut bakiyen: **{balance}**\nParan olunca tekrar dene!",
                ephemeral=True
            )
            return

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
        self.started_at = time.time()  # bayat oturumları temizlemek için
        self.secret_code = self.generate_code()
        self.attempts_left = 10
        self.history = []  # List of (guess, green, yellow)
        self.hints_left = 3
        self.given_hints = []
        self.available_hints = []
        self.generate_possible_hints()
        
        # Otomatik 3 ipucu ver
        for _ in range(3):
            self.get_hint()

    def generate_code(self):
        """0-9 arası 5 benzersiz rakam seçer."""
        digits = list("0123456789")
        random.shuffle(digits)
        return "".join(digits[:5])

    def generate_possible_hints(self):
        """Olası ipuçlarını oluşturur ve karıştırır."""
        hints = []
        for i, char in enumerate(self.secret_code):
            digit = int(char)
            pos = i + 1
            
            # Büyüklük/Küçüklük
            if digit > 5:
                hints.append(f"{pos}. rakam 5'ten büyük.")
            elif digit < 5:
                hints.append(f"{pos}. rakam 5'ten küçük.")
            
            # Tek/Çift
            if digit % 2 == 0:
                hints.append(f"{pos}. rakam çift sayı.")
            else:
                hints.append(f"{pos}. rakam tek sayı.")
                
            # Asal
            if char in "2357":
                hints.append(f"{pos}. rakam asal sayı.")
                
            # Varlık (Konum belirtmeden)
            hints.append(f"Rakamlardan biri {digit}.")
            
        random.shuffle(hints)
        self.available_hints = hints

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
        """Havuzdan rastgele bir ipucu çeker."""
        if self.hints_left <= 0 or not self.available_hints:
            return None
        
        hint = self.available_hints.pop()
        self.given_hints.append(hint)
        self.hints_left -= 1
        return hint


class Economy(commands.Cog):
    def __init__(self, bot):
        self.bot = bot
        self.system_breaker_games = {} # user_id -> SystemBreakerSession
        # Aynı anda birden fazla bahisli oyun açılmasını engeller.
        # (Eskiden aynı bakiyeyle N tane blackjack açılıp bakiye eksiye düşürülebiliyordu.)
        self.active_games = {}  # user_id -> oyun adı

    async def cog_load(self):
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            # WAL kalıcı bir dosya ayarıdır, bir kez açmak yeterli.
            # Eşzamanlı okuma/yazmada "database is locked" hatalarını azaltır.
            await db.execute("PRAGMA journal_mode=WAL")
            await db.execute(
                "CREATE TABLE IF NOT EXISTS economy ("
                "user_id INTEGER PRIMARY KEY, "
                "balance INTEGER DEFAULT 100, "
                "last_daily INTEGER DEFAULT 0)"
            )

            # Mevcut veritabanları için idempotent migration
            async with db.execute("PRAGMA table_info(economy)") as cursor:
                kolonlar = {row[1] for row in await cursor.fetchall()}
            if "last_daily" not in kolonlar:
                log.info("economy tablosuna last_daily kolonu ekleniyor")
                await db.execute("ALTER TABLE economy ADD COLUMN last_daily INTEGER DEFAULT 0")

            await db.commit()

        try:
            with open("emoji_games.json", "r", encoding="utf-8") as f:
                self.emoji_games = json.load(f)
        except Exception:
            log.exception("Emoji oyunları yüklenemedi")
            self.emoji_games = []

    # --- Oyun eşzamanlılık kilidi -------------------------------------------------

    def start_game(self, user_id, oyun_adi) -> str | None:
        """Kilidi almaya çalışır. Başarılıysa None, meşgulse mevcut oyunun adını döner."""
        mevcut = self.active_games.get(user_id)
        if mevcut:
            return mevcut
        self.active_games[user_id] = oyun_adi
        return None

    def finish_game(self, user_id):
        """Oyun bittiğinde/zaman aşımına uğradığında kilidi bırakır."""
        self.active_games.pop(user_id, None)

    # --- Bakiye ------------------------------------------------------------------

    async def get_balance(self, user_id):
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user_id,))
            await db.commit()
            async with db.execute("SELECT balance FROM economy WHERE user_id = ?", (user_id,)) as cursor:
                row = await cursor.fetchone()
                return row[0] if row else 100

    async def update_balance(self, user_id, amount):
        """Bakiyeye ekler/çıkarır. Harcama için try_spend kullan — bu negatifi engellemez."""
        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user_id,))
            await db.execute("UPDATE economy SET balance = balance + ? WHERE user_id = ?", (amount, user_id))
            await db.commit()

    async def try_spend(self, user_id, amount) -> bool:
        """
        Bakiyeden atomik olarak düşer.

        Tek bir koşullu UPDATE kullanır: bakiye yetmiyorsa hiçbir satır güncellenmez
        ve False döner. Bu, "önce oku, sonra yaz" arasındaki await'lerde oluşan
        çift harcamayı (TOCTOU) ve eksi bakiyeyi tamamen kapatır.
        """
        if amount <= 0:
            raise ValueError(f"try_spend pozitif miktar bekler, {amount} verildi")

        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user_id,))
            cursor = await db.execute(
                "UPDATE economy SET balance = balance - ? WHERE user_id = ? AND balance >= ?",
                (amount, user_id, amount),
            )
            await db.commit()
            return cursor.rowcount > 0

    @commands.command(name="bakiyeguncelle")
    @commands.guild_only()
    @commands.has_permissions(administrator=True)
    async def bakiyeguncelle(self, ctx, member: discord.Member, amount: int):
        """Belirtilen kullanıcının bakiyesini 'amount' kadar artırır/azaltır. (Yönetici komutu)"""
        
        # Önce güncelle
        await self.update_balance(member.id, amount)
        # Sonra yeni bakiyeyi al
        new_balance = await self.get_balance(member.id)
        
        await ctx.send(f"✅ {member.display_name} kullanıcısının yeni bakiyesi: **{new_balance}** tonish coin 💸")

    @commands.command(aliases=["tonishcoin", "cuzdan"])
    @commands.guild_only()
    async def bakiye(self, ctx, member: discord.Member = None):
        member = member or ctx.author
        bal = await self.get_balance(member.id)
        await ctx.send(f"{member.display_name}: **{bal}** tonish coin 💸")

    @commands.command()
    async def gunluk(self, ctx):
        """Her 24 saatte bir günlük ödülü verir."""
        # Bekleme süresi veritabanında tutulur — commands.cooldown bellekte tutulduğu
        # için bot her yeniden başladığında sıfırlanıyordu ve sınırsız farm edilebiliyordu.
        user_id = ctx.author.id
        simdi = int(time.time())
        esik = simdi - DAILY_COOLDOWN

        async with aiosqlite.connect(DB_PATH, timeout=DB_TIMEOUT) as db:
            await db.execute("INSERT OR IGNORE INTO economy (user_id) VALUES (?)", (user_id,))
            cursor = await db.execute(
                "UPDATE economy SET balance = balance + ?, last_daily = ? "
                "WHERE user_id = ? AND last_daily <= ?",
                (DAILY_AMOUNT, simdi, user_id, esik),
            )
            alindi = cursor.rowcount > 0

            if not alindi:
                async with db.execute(
                    "SELECT last_daily FROM economy WHERE user_id = ?", (user_id,)
                ) as c2:
                    row = await c2.fetchone()
                son = row[0] if row else simdi

            await db.commit()

        if not alindi:
            kalan = max(0, DAILY_COOLDOWN - (simdi - son))
            saat, dakika = divmod(kalan // 60, 60)
            return await ctx.send(
                f"⏳ Günlük ödülünü zaten aldın! Tekrar almak için **{saat} saat {dakika} dakika** beklemelisin."
            )

        bal = await self.get_balance(user_id)
        await ctx.send(f"Günlük {DAILY_AMOUNT} coin aldın! Yeni bakiye: **{bal}**")

    @commands.command(name="blackjack", aliases=["bj"])
    @commands.guild_only()
    async def blackjack(self, ctx, bet: int):
        """Blackjack oynamak için."""
        user_id = ctx.author.id

        if bet <= 0:
            await ctx.send("Lütfen geçerli bir bahis miktarı gir (0'dan büyük).")
            return

        mevcut = self.start_game(user_id, "blackjack")
        if mevcut:
            await ctx.send(f"Zaten devam eden bir **{mevcut}** oyunun var! Önce onu bitir.")
            return

        # Bahsi peşin al (escrow). Böylece oyuncu kötü eli terk ederek bedava çıkamaz.
        if not await self.try_spend(user_id, bet):
            self.finish_game(user_id)
            balance = await self.get_balance(user_id)
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

        try:
            view.message = await ctx.send(embed=embed, view=view)
        except discord.HTTPException:
            # Masayı açamadıysak bahsi iade et ve kilidi bırak
            log.exception("Blackjack masası gönderilemedi, bahis iade ediliyor (user_id=%s)", user_id)
            await self.update_balance(user_id, bet)
            self.finish_game(user_id)
            return

        await view.check_game_state(None)

    @blackjack.error
    async def blackjack_error(self, ctx, error):
        if isinstance(error, commands.MissingRequiredArgument):
            await ctx.send("Unutkanlık! 💸 Bahis miktarını girmeyi unuttun. \n**Örnek kullanım:** `!blackjack 50`")
        elif isinstance(error, commands.BadArgument):
            await ctx.send("Hoppa! 😮 Bahis miktarı bir sayı olmalı. \n**Örnek kullanım:** `!blackjack 50`")
        else:
            # Kilit sızmasın diye her durumda bırak
            self.finish_game(ctx.author.id)
            log.exception("Blackjack komutunda beklenmedik hata", exc_info=error)
            await ctx.send("Blackjack oynarken beklenmedik bir hata oluştu. 😥 Yetkiliye haber ver!")

    @commands.command(name="slot")
    @commands.guild_only()
    async def slot(self, ctx, bet: int):
        """
        Slot makinesini interaktif bir butonla başlatır.

        Bahis her 'Çevir!' basışında düşülür (SlotView içinde atomik olarak),
        bu yüzden makine açmak eşzamanlılık kilidi gerektirmez.
        """
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
    @commands.guild_only()
    async def sistem_kirici(self, ctx):
        """Sistem Kırıcı (Hardcore Mod) oyununu başlatır. Giriş: 100 Coin."""
        user_id = ctx.author.id

        # Zaten oyunda mı? (Bayat oturumlar otomatik temizlenir)
        mevcut = self.system_breaker_games.get(user_id)
        if mevcut:
            if time.time() - mevcut.started_at < SB_SESSION_TIMEOUT:
                await ctx.send(
                    "Zaten devam eden bir 'Sistem Kırıcı' görevin var! `!tahmin <sayı>` ile devam et, "
                    "vazgeçmek için `!vazgec` yaz."
                )
                return
            log.info("Bayat Sistem Kırıcı oturumu temizlendi (user_id=%s)", user_id)
            del self.system_breaker_games[user_id]

        # Ücreti atomik olarak al
        if not await self.try_spend(user_id, SISTEMKIRICI_UCRETI):
            balance = await self.get_balance(user_id)
            await ctx.send(
                f"Yetersiz bakiye! 🚫 Bu göreve girmek için **{SISTEMKIRICI_UCRETI}** tonish coin gerekiyor. "
                f"Mevcut: **{balance}**"
            )
            return

        self.system_breaker_games[user_id] = SystemBreakerSession(user_id)

        embed = discord.Embed(
            title="💻 SİSTEM KIRICI (HARDCORE) BAŞLADI",
            description=f"**Hedef:** 5 Haneli Şifreyi Çöz (Rakamlar benzersiz!)\n"
                        f"**Hak:** 10 Deneme\n"
                        f"**Ödül:** Kalan hakka göre artar!\n\n"
                        f"Tahmin yapmak için: `!tahmin 12345` yaz.",
            color=discord.Color.dark_red()
        )
        embed.set_footer(text=f"Oyuncu: {ctx.author.display_name} | Sistem güvenliği: YÜKSEK 🔒", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        # Başlangıç ipuçlarını ekle
        if self.system_breaker_games[user_id].given_hints:
            hints_str = "\n".join([f"• {h}" for h in self.system_breaker_games[user_id].given_hints])
            embed.add_field(name="💡 İpuçları", value=hints_str, inline=False)
        
        await ctx.send(embed=embed)

    @commands.command(name="vazgec", aliases=["birak", "iptal"])
    @commands.guild_only()
    async def vazgec(self, ctx):
        """Devam eden Sistem Kırıcı görevinden vazgeçer (giriş ücreti iade edilmez)."""
        oturum = self.system_breaker_games.pop(ctx.author.id, None)
        if not oturum:
            return await ctx.send("Vazgeçebileceğin aktif bir 'Sistem Kırıcı' görevin yok.")

        await ctx.send(
            f"🚪 Görevden vazgeçtin. Şifre **`{oturum.secret_code}`** imiş.\n"
            f"Giriş ücreti iade edilmez. Yeniden denemek için `!sistemkirici` yaz."
        )

    @commands.command(name="zindan", aliases=["dungeon", "rpg"])
    @commands.guild_only()
    @commands.cooldown(1, 60, commands.BucketType.user)
    async def zindan(self, ctx):
        """Zindan Akını oyununu başlatır. Giriş: 50 Coin."""
        user_id = ctx.author.id

        mevcut = self.start_game(user_id, "zindan")
        if mevcut:
            ctx.command.reset_cooldown(ctx)
            await ctx.send(f"Zaten devam eden bir **{mevcut}** oyunun var! Önce onu bitir.")
            return

        # Giriş ücretini atomik olarak al
        if not await self.try_spend(user_id, ZINDAN_UCRETI):
            self.finish_game(user_id)
            ctx.command.reset_cooldown(ctx)
            balance = await self.get_balance(user_id)
            await ctx.send(
                f"Yetersiz bakiye! 🚫 Zindana girmek için **{ZINDAN_UCRETI}** tonish coin gerekiyor. "
                f"Mevcut: **{balance}**"
            )
            return

        game = DungeonGame(ctx, self)
        try:
            await game.update_display()
        except discord.HTTPException:
            log.exception("Zindan masası gönderilemedi, ücret iade ediliyor (user_id=%s)", user_id)
            await self.update_balance(user_id, ZINDAN_UCRETI)
            self.finish_game(user_id)

    @commands.command(name="tahmin")
    @commands.guild_only()
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
            # Ödül Hesaplama: 200 + (Kalan Hak x 50 / 2)
            bonus = (game.attempts_left * 50) // 2
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
            embed.set_footer(text=f"Oyuncu: {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
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
            embed.set_footer(text=f"Oyuncu: {ctx.author.display_name}", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
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
        embed.set_footer(text=f"Oyuncu: {ctx.author.display_name} | Sistem güvenliği: YÜKSEK 🔒", icon_url=ctx.author.avatar.url if ctx.author.avatar else None)
        
        # İpuçlarını göster
        if game.given_hints:
            hints_str = "\n".join([f"• {h}" for h in game.given_hints])
            embed.add_field(name="💡 İpuçları", value=hints_str, inline=False)
            
        await ctx.send(embed=embed)

    @commands.command(name="bilmece")
    @commands.guild_only()
    @commands.cooldown(1, 300, commands.BucketType.user)
    async def bilmece(self, ctx):
        """Emojilerle anlatılan oyunu tahmin et! (5dk bekleme süresi)"""
        # Adminler için cooldown sıfırla
        if ctx.author.guild_permissions.administrator:
            ctx.command.reset_cooldown(ctx)

        if not self.emoji_games:
            # Tekrar yüklemeyi dene
            try:
                with open("emoji_games.json", "r", encoding="utf-8") as f:
                    self.emoji_games = json.load(f)
            except Exception:
                log.exception("Bilmece veritabanı yüklenemedi")
                await ctx.send("Oyun veritabanı şu an yüklenemiyor. Bir yetkiliye haber ver. 😥")
                return

        game_data = random.choice(self.emoji_games)
        correct_answer = game_data["name"]
        aliases = game_data.get("aliases", [])
        
        # Normalizasyon fonksiyonu
        def normalize(text):
            return text.lower().replace("-", "").replace(" ", "").replace("'", "").replace(":", "")

        normalized_answer = normalize(correct_answer)
        normalized_aliases = [normalize(a) for a in aliases]
        
        # JSON'da 'emoji' anahtarı kullanılıyor, kodda 'emojis' kalmış olabilir.
        emoji_str = game_data.get("emoji", game_data.get("emojis", "❓"))

        embed = discord.Embed(
            title="🎮 HANGİ OYUN BU?",
            description=f"❓ **Soru:** {emoji_str}\n\n"
                        f"⏱️ **Süre:** 30 Saniye\n"
                        f"Cevabı direkt sohbete yazın!",
            color=discord.Color.blue()
        )
        message = await ctx.send(embed=embed)
        
        start_time = datetime.now()
        
        def check(m):
            if m.channel != ctx.channel or m.author.bot:
                return False
            
            content = normalize(m.content)
            return content == normalized_answer or content in normalized_aliases

        try:
            # İlk 15 saniye (İpucusuz)
            winner_msg = await self.bot.wait_for('message', check=check, timeout=15.0)
            
            # KAZANDI (Hızlı)
            elapsed = (datetime.now() - start_time).total_seconds()
            reward = 100
            
            await self.update_balance(winner_msg.author.id, reward)
            
            embed.color = discord.Color.green()
            embed.description = f"🎉 **DOĞRU CEVAP!**\n\n" \
                                f"**Kazanan:** {winner_msg.author.mention}\n" \
                                f"**Oyun:** {correct_answer}\n" \
                                f"**Süre:** {elapsed:.1f}sn\n" \
                                f"**Ödül:** {reward} Tonish Coin 💰"
            await message.edit(embed=embed)
            await ctx.send(f"Tebrikler {winner_msg.author.mention}! Hızlı davrandın ve **{reward}** coin kazandın!")
            return

        except asyncio.TimeoutError:
            # İpucu Zamanı
            embed.description = f"❓ **Soru:** {emoji_str}\n\n" \
                                f"💡 **İpucu:** {game_data['hint']}\n" \
                                f"⏱️ **Süre:** Son 15 Saniye!"
            embed.color = discord.Color.gold()
            await message.edit(embed=embed)
            
            try:
                # Son 15 saniye (İpuculu)
                winner_msg = await self.bot.wait_for('message', check=check, timeout=15.0)
                
                # KAZANDI (Yavaş)
                elapsed = (datetime.now() - start_time).total_seconds()
                reward = 50
                
                await self.update_balance(winner_msg.author.id, reward)
                
                embed.color = discord.Color.green()
                embed.description = f"🎉 **DOĞRU CEVAP!**\n\n" \
                                    f"**Kazanan:** {winner_msg.author.mention}\n" \
                                    f"**Oyun:** {correct_answer}\n" \
                                    f"**Süre:** {elapsed:.1f}sn\n" \
                                    f"**Ödül:** {reward} Tonish Coin 💰"
                await message.edit(embed=embed)
                await ctx.send(f"Tebrikler {winner_msg.author.mention}! İpucuyla bildin ve **{reward}** coin kazandın!")
                
            except asyncio.TimeoutError:
                # KİMSE BİLEMEDİ
                embed.color = discord.Color.red()
                embed.description = f"⌛ **SÜRE DOLDU!**\n\n" \
                                    f"Kimse bilemedi...\n" \
                                    f"**Doğru Cevap:** {correct_answer}"
                await message.edit(embed=embed)

    @bilmece.error
    async def bilmece_error(self, ctx, error):
        if isinstance(error, commands.NoPrivateMessage):
            return await ctx.send("Bu komut sadece sunucu içinde çalışır. 🏠")

        if isinstance(error, commands.CommandOnCooldown):
            # Admin ise bekleme süresini yoksay (guild_permissions sadece sunucuda var)
            yetkili = getattr(getattr(ctx.author, "guild_permissions", None), "administrator", False)
            if yetkili:
                ctx.command.reset_cooldown(ctx)
                return await ctx.reinvoke()

            return await ctx.send(
                f"⏳ Biraz soluklan! Bu komutu tekrar kullanmak için "
                f"**{error.retry_after:.0f} saniye** beklemelisin."
            )

        log.exception("Bilmece komutunda beklenmedik hata", exc_info=error)
        await ctx.send("Bilmece başlatılırken bir hata oluştu. 😥")

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
        except OSError:
            log.warning("Liderlik arkaplanı (%s) yüklenemedi, düz renk kullanılıyor", LEADERBOARD_BG)
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
                except Exception:
                    log.warning("Liderlik avatarı işlenemedi (%s)", username)
            
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
    @commands.guild_only()
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
                username = "Bilinmeyen Kullanıcı"
                avatar_bytes = None
                try:
                    # Önce cache'e bak — her çağrıda 5 ayrı API isteği atmayalım
                    user = self.bot.get_user(uid) or await self.bot.fetch_user(uid)
                    username = user.display_name
                    try:
                        avatar_bytes = await user.display_avatar.read()
                    except discord.HTTPException:
                        log.debug("Avatar okunamadı (user_id=%s)", uid)
                except discord.NotFound:
                    log.info("Liderlik tablosunda silinmiş kullanıcı (user_id=%s)", uid)
                except discord.HTTPException:
                    log.warning("Kullanıcı getirilemedi (user_id=%s)", uid)

                users_data.append((i, username, bal, avatar_bytes))

            # 3. Resmi Oluştur (Bloklayan işlem olduğu için executor'da çalıştır)
            buffer = await self.bot.loop.run_in_executor(None, self.generate_leaderboard_image, users_data)

            # 4. Gönder
            file = discord.File(buffer, filename="liderlik.png")
            await ctx.send(file=file)
            await loading_msg.delete()

        except Exception:
            log.exception("Liderlik tablosu oluşturulamadı")
            await loading_msg.edit(content="Liderlik tablosu oluşturulamadı, birazdan tekrar dene. 😥")

async def setup(bot):
    await bot.add_cog(Economy(bot))
