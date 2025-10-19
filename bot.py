# TonishBot - Nişantaşı Üniversitesi Discord Botu

#kütüphaneler
import discord
import os
import asyncio
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
import time
import threading
import functools
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# .env dosyasındaki bilgileri yükleme
load_dotenv()

# .env dosyasından bilgileri çekme
TOKEN = os.getenv('DISCORD_TOKEN')
KAYIT_KANALI_ID = int(os.getenv('KAYIT_KANALI_ID'))
KAYITSIZ_ROLU_ID = int(os.getenv('KAYITSIZ_ROLU_ID'))
TOPLULUK_ROLU_ID = int(os.getenv('TOPLULUK_ROLU_ID'))
KULUP_ROLU_ID = int(os.getenv('KULUP_ROLU_ID'))
WEBSITE_USERNAME = os.getenv('WEBSITE_USERNAME')
WEBSITE_PASSWORD = os.getenv('WEBSITE_PASSWORD')

# Bot için gerekli izinleri tanımlama
intents = discord.Intents.default()
intents.members = True
intents.message_content = True

client = discord.Client(intents=intents)

# --- WEBSCRAPPING FONKSİYONU ---
def ogrenci_numarasi_dogrula(ogrenci_no):
    LOGIN_PAGE_URL = 'https://sks.nisantasi.edu.tr/kulup-baskani/login'
    MEMBER_LIST_URL = 'https://sks.nisantasi.edu.tr/kulup-baskani/uyeler'
    
    service = Service(executable_path='chromedriver.exe')
    options = webdriver.ChromeOptions()
    
    # --- GÖRSEL MOD İÇİN BU SATIRI YORUMDA BIRAK ---
    options.add_argument('--headless') 
    # herhangi bir çakışma ve izin sorunu olmasın diye abartı ayarlar
    options.add_argument("--start-maximized")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-infobars")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-browser-side-navigation")
    options.add_argument("--disable-gpu")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36")    
    options.add_experimental_option('excludeSwitches', ['enable-logging'])


    print("Web scraping başlıyor")
    driver = None
    try:
        print("\nadım 1: tarayıcı başlatılıyor")
        driver = webdriver.Chrome(service=service, options=options)
        
        wait = WebDriverWait(driver, 20)

        print("\nadım 2: giriş sayfası")
        driver.get(LOGIN_PAGE_URL)
    
        print("\nadım 3: bilgileri dolduruluyor...")
        username_box = wait.until(EC.visibility_of_element_located((By.ID, 'kullaniciAdi')))
        username_box.click()
        username_box.send_keys(WEBSITE_USERNAME)        
        password_box = driver.find_element(By.ID, 'sifre')
        password_box.click()
        password_box.send_keys(WEBSITE_PASSWORD)

        print("\nadım 4: giriş butonuna tıklama")
        login_button = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, "button[type='submit']")))
        login_button.click()
       
        print("Kulüp Üyeleri butonunun yüklenmesi bekleniyor...")
        kulup_uyeleri_button = wait.until(EC.element_to_be_clickable((By.XPATH, "/html/body/div[5]/main/div/div[1]/a/button")))

        print("Kulüp Üyeleri butonuna tıklanıyor...")
        kulup_uyeleri_button.click()

        # webscraping
        wait.until(EC.visibility_of_element_located((By.TAG_NAME, 'tbody')))
        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')
        
        bulunan_numaralar = []
        table_body = soup.find('tbody')
        if not table_body: return False
        rows = table_body.find_all('tr')
        for row in rows:
            cells = row.find_all('td')
            if len(cells) > 3:
                ogrenci_no_hucre = cells[3].text.strip()
                if ogrenci_no_hucre.isdigit():
                    bulunan_numaralar.append(ogrenci_no_hucre)
        
        if ogrenci_no in bulunan_numaralar:
            print("BAŞARILI: Öğrenci bulundu!")
            return True
        else:
            print("BAŞARISIZ: Öğrenci bulunamadı.")
            return False
    except Exception as e:
        print(f"\n!!! HATA !!! Selenium ile web scraping sırasında bir hata oluştu: {e}")
        return False
    finally:
        if driver:
            print("\nİşlem bitti. Tarayıcı 5 saniye içinde kapatılacak.")
            time.sleep(5)
            driver.quit()

# --- BUTON SINIFI (EN BÜYÜK DEĞİŞİKLİK BURADA) ---
class KayitView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    async def run_blocking(self, blocking_func, *args):
        """ Asistan şefe işi devreden ve sonucunu bekleyen yönetici fonksiyon """
        # functools.partial, partiala şu fonksiyonu, bu argümanlarla çalıştır
        func = functools.partial(blocking_func, *args)
        # client.loop.run_in_executor parçaladı ve iki blok şeklinde çalıştırdı ki heartbeat atmaya devam etsin
        return await client.loop.run_in_executor(None, func)

    @discord.ui.button(label="Evet, NU öğrencisiyim", style=discord.ButtonStyle.success, custom_id="ogrenci_evet")
    async def evet_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        member = interaction.user
        await interaction.response.send_message(f"Harika, {member.mention}! Lütfen 11 haneli okul numaranı bu kanala yaz.", ephemeral=True)
        try:
            def check(m): return m.author == interaction.user and m.channel == interaction.channel
            message = await client.wait_for('message', timeout=60.0, check=check)
            ogrenci_no = message.content.strip()

            if not ogrenci_no.isdigit() or len(ogrenci_no) != 11:
                await interaction.followup.send("Girdiğin numara 11 haneli ve sadece rakamlardan oluşmalı.", ephemeral=True)
                return

            await interaction.followup.send("Numaranı kontrol ediyorum, bu işlem 20 saniye kadar sürebilir...", ephemeral=True)
            
            dogrulandi = await self.run_blocking(ogrenci_numarasi_dogrula, ogrenci_no)
            
            kayitsiz_rolu = interaction.guild.get_role(KAYITSIZ_ROLU_ID)
            if dogrulandi:
                kulup_uyesi_rolu = interaction.guild.get_role(KULUP_ROLU_ID)
                await member.add_roles(kulup_uyesi_rolu)
                await member.remove_roles(kayitsiz_rolu)
                await interaction.followup.send(f"Doğrulama başarılı! Aramıza hoş geldin. `Kulüp Üyesi` rolü verildi.", ephemeral=True)
            else:
                kayitlink = 'https://sks.nisantasi.edu.tr/uye-talep'
                await interaction.followup.send(f"Maalesef girdiğin öğrenci numarası sistemde bulunamadı. Eğer kulübümüze katılmak istersen aşağıdaki bağlantıya tıklayarak kayıt işlemini yapabilirsin! Daha sonra '!kayitol' komutunu bu kanala yazarak tekrar kayıt işlemi yapabilirsin.\n{kayitlink} ", ephemeral=True)
        except asyncio.TimeoutError:
            await interaction.followup.send("Zamanında cevap vermediğin için kayıt iptal edildi.", ephemeral=True)

    @discord.ui.button(label="Hayır, Değilim", style=discord.ButtonStyle.danger, custom_id="ogrenci_hayir")
    async def hayir_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):

        member = interaction.user
        topluluk_rolu = interaction.guild.get_role(TOPLULUK_ROLU_ID)
        kayitsiz_rolu = interaction.guild.get_role(KAYITSIZ_ROLU_ID)
        await member.add_roles(topluluk_rolu)
        await member.remove_roles(kayitsiz_rolu)
        await interaction.response.send_message(f"Kaydın tamamlandı {member.mention}! `Topluluk Üyesi` rolü verildi.", ephemeral=True)

# --- Bot Eventleri  --- 
@client.event
async def on_ready():
    client.add_view(KayitView())
    print(f'{client.user} olarak giriş yaptık ve kayıt sistemimiz hazır!')
    print('--------------------------------------------------')

@client.event
async def on_member_join(member):
    print(f'{member.name} sunucuya katıldı.')
    kayit_kanali = member.guild.get_channel(KAYIT_KANALI_ID)
    kayitsiz_rolu = member.guild.get_role(KAYITSIZ_ROLU_ID)
    if not kayit_kanali or not kayitsiz_rolu:
        print("HATA: Kayıt kanalı veya kayıtsız rolü bulunamadı! ID'leri kontrol et.")
        return
    await member.add_roles(kayitsiz_rolu)
    hgmesaj = (f"Hoş geldin {member.mention}! Sunucumuza tam erişim sağlamak için lütfen kayıt ol.\n\n"
             f"**İstanbul Nişantaşı Üniversitesi öğrencisi misin?**")
    await kayit_kanali.send(hgmesaj, view=KayitView())

# !kayitol eventi
@client.event
async def on_message(message):
    # Botun kendi kendine cevap vermesini engelle
    if message.author == client.user:
        return

    # Sadece #kayıt kanalında çalışsın
    if message.channel.id != KAYIT_KANALI_ID:
        return

    # Komut '!kayitol' ise...
    if message.content.lower() == '!kayitol':
        # Kullanıcının eski komutunu 1 saniye sonra sil (kanalı temiz tutmak için)
        await asyncio.sleep(1)
        await message.delete()

        # Kayıt mesajını ve butonlarını yeniden gönder
        member = message.author
        hgmesaj = (f"Tekrar hoş geldin {member.mention}! Kayıt işlemini yeniden başlatalım.\n\n"
                   f"**İstanbul Nişantaşı Üniversitesi öğrencisi misin?**")
        
        # Bu mesajın da sadece komutu yazan kişi tarafından görülmesi daha iyi olabilir.
        # Ama şimdilik kanala atalım, isteğe göre bunu da 'ephemeral' yapabiliriz.
        await message.channel.send(hgmesaj, view=KayitView(), delete_after=300) # 5 dakika sonra kendini silsin

# --- BOTU ÇALIŞTIR --- 
client.run(TOKEN)