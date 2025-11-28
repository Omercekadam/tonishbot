import discord
import os
import asyncio
from discord.ext import commands
from dotenv import load_dotenv

load_dotenv()

TOKEN = os.getenv('DISCORD_TOKEN')
CEK_DISCORD_ID = int(os.getenv('CEK_DISCORD_ID', 0))

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True 

class TonishBot(commands.Bot):
    def __init__(self):
        super().__init__(
            command_prefix="!", 
            intents=intents,
            help_command=None 
        )
        self.cek_id = CEK_DISCORD_ID 

    async def setup_hook(self):
        """
        Bot başlatılırken çalışacak kurulum fonksiyonu.
        Eklentileri (Cogs) burada yüklüyoruz.
        """
        print("--- TonishBot Başlatılıyor ---")
        
        # Cogs klasöründeki tüm .py dosyalarını otomatik bul ve yükle
        for filename in os.listdir('./cogs'):
            if filename.endswith('.py'):
                try:
                    # cogs.dosya_adi formatında yükleme yap
                    await self.load_extension(f'cogs.{filename[:-3]}')
                    print(f"[+] Eklenti Yüklendi: {filename}")
                except Exception as e:
                    print(f"[-] Eklenti Yüklenemedi {filename}: {e}")

        print("--- Tüm Eklentiler İşlendi ---")

    async def on_ready(self):
        """Bot Discord'a başarıyla bağlandığında çalışır."""
        print(f'{self.user} olarak giriş yapıldı!')
        print(f'ID: {self.user.id}')
        print('------')

bot = TonishBot()

if __name__ == "__main__":
    if not TOKEN:
        print("HATA: DISCORD_TOKEN bulunamadı. .env dosyasını kontrol edin.")
    else:
        bot.run(TOKEN)