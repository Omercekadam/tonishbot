# TonishBot - Nişantaşı Üniversitesi Discord Botu

#kütüphaneler
import discord
import os
from dotenv import load_dotenv
from discord.ext import commands
from discord import app_commands # Gerekli değil ama modern yaklaşım için kalsın
from discord.ui import View, Button, Modal, TextInput, Select # İhtiyacımız olan arayüz elemanları


# .env dosyasındaki bilgileri yükleme
load_dotenv()

# .env dosyasından bilgileri çekme
TOKEN = os.getenv('DISCORD_TOKEN')
KAYIT_KANALI_ID = int(os.getenv('KAYIT_KANALI_ID'))
TOPLULUK_ROLU_ID = int(os.getenv('TOPLULUK_ROLU_ID'))
KULUP_ROLU_ID = int(os.getenv('KULUP_ROLU_ID'))
ROLALMA_KANALI_ID=int(os.getenv('ROLALMA_KANALI_ID'))

# ROLLER

ROLE_OPTIONS = {
    # "ROL_ID": {"label": "rol adı", "emoji": "💻", "description": "rol açıklaması (isteğe bağlı)"},
    
    1430319278334410824: {
        "label": "Game Developer",
        "emoji": "💻",
        "description": "Oyun geliştirme ile ilgileniyorum."
    },
    1430324401110257784: {
        "label": "Visual Artist",
        "emoji": "🎨",
        "description": "2D/3D Görsel sanatlar ile ilgileniyorum."
    },
    1430324364884316232: {
        "label": "Game Designer",
        "emoji": "✏️", # Veya 📝
        "description": "Oyun tasarımı ile ilgileniyorum."
    },
    # 123456789000000004: {
    #     "label": "Level Designer",
    #     "emoji": "🟩", # Veya 🗺️
    #     "description": "Bölüm tasarımı ile ilgileniyorum."
    # },
    # 123456789000000005: {
    #     "label": "Sound Artist",
    #     "emoji": "🎤", # Veya 🎧
    #     "description": "Ses ve müzik ile ilgileniyorum."
    # },
    # 123456789000000006: {
    #     "label": "Game Tester",
    #     "emoji": "🎮", # Veya 🕹️
    #     "description": "Oyun testi ve QA ile ilgileniyorum."
    # },
    # 123456789000000007: {
    #     "label": "Notify Me",
    #     "emoji": "🔔",
    #     "description": "Duyurulardan haberdar olmak istiyorum."
    # },
}

#INTENTS

intents = discord.Intents.default()
intents.members = True 
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)


#KAYIT FORMU
class RegistrationModal(Modal, title="TonishBot Kayıt Paneli"):

    
    #ad
    form_isim = TextInput(
        label="İsminiz",
        placeholder="İsim",
        style=discord.TextStyle.short,
        required=True,
        max_length=20
    )

    #soyad
    form_soyisim = TextInput(
        label="Soyisminiz",
        placeholder="Soyisim",
        style=discord.TextStyle.short,
        required=True,
        max_length=20
    )

    #nickname
    form_nickname = TextInput(
        label="Kullanmak istediğiniz Nickname",
        placeholder="Tonish",
        style=discord.TextStyle.short,
        required=True,
        max_length=20
    )

    #NICK DEĞİŞTİRME
    async def on_submit(self, interaction: discord.Interaction):

        isim = self.form_isim.value
        soyisim = self.form_soyisim.value
        nickname = self.form_nickname.value

        new_nick = f"{isim} '{nickname}' {soyisim}"

        try:
            await interaction.user.edit(nick=new_nick)
            
            await interaction.response.send_message(
                f"Harika! Kaydın tamamlandı ve nickname'in başarıyla ayarlandı:\n**{new_nick}**",
                ephemeral=True 
            )
        except discord.Forbidden:
            await interaction.response.send_message(
                "Nickname'ini değiştiremiyorum.",
                ephemeral=True
            )
        except Exception as e:
            await interaction.response.send_message(f"Beklenmedik bir hata oluştu: {e}", ephemeral=True)
            print(f"Hata: {e}")

# KAYIT BUTONU GÖRÜNÜMÜ

class RegistrationView(View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(
        label="Kayıt Olmak İçin Tıkla",
        style=discord.ButtonStyle.green,
        custom_id="kalici_kayit_butonu" 
    )
    async def register_button_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RegistrationModal())

# AÇILAN MENU
class RoleSelect(Select):

    def __init__(self):
        options = []
        for role_id, data in ROLE_OPTIONS.items():
            options.append(
                discord.SelectOption(
                    label=data["label"],
                    value=str(role_id), 
                    emoji=data.get("emoji"), 
                    description=data.get("description") 
                )
            )

        #SEÇMECE
        super().__init__(
            custom_id="kalici_rol_secme_menusu", 
            placeholder="Almak istediğiniz rolleri seçin...",
            min_values=0, 
            max_values=len(options), 
            options=options
        )

    async def callback(self, interaction: discord.Interaction):
        # DÜŞÜNME EFEKTİ
        await interaction.response.defer(ephemeral=True)
        
        member = interaction.user 
        
        selected_role_ids = set(int(value) for value in self.values)
        all_menu_role_ids = set(ROLE_OPTIONS.keys())
        
        roles_to_add = []
        roles_to_remove = []
        
        #ROL KONTROL

        for role_id in all_menu_role_ids:
            role = interaction.guild.get_role(role_id)
            if role is None:
                print(f"HATA: {role_id} ID'li rol sunucuda bulunamadı. Ayarları kontrol et.")
                continue
            
            # ROL EKLE
            if role_id in selected_role_ids and role not in member.roles:
                roles_to_add.append(role)
            # ROL ÇIKAR
            elif role_id not in selected_role_ids and role in member.roles:
                roles_to_remove.append(role)

        try:
            if roles_to_add:
                await member.add_roles(*roles_to_add, reason="Rol menüsünden seçildi")
            if roles_to_remove:
                await member.remove_roles(*roles_to_remove, reason="Rol menüsünden kaldırıldı")

            await interaction.followup.send("Rollerin başarıyla güncellendi!", ephemeral=True)
            
        except discord.Forbidden:
            print(f"HATA: {member.name} için roller güncellenemedi")
            await interaction.followup.send("Rollerini güncelleyemedim.", ephemeral=True)
        except Exception as e:
            print(f"ROL MENÜSÜ HATASI: {e}")
            await interaction.followup.send(f"Bilinmeyen bir hata oluştu: {e}", ephemeral=True)


#MENÜ SİLİNMESİN DİYE

class RoleSelectView(View):
    def __init__(self):
        super().__init__(timeout=None)
        self.add_item(RoleSelect())

# BOT ÇALIŞTI

@bot.event
async def on_ready():
    print(f'Bot {bot.user} olarak giriş yaptı!')
    print(f'Token: {TOKEN[:5]}...') 
    print(f'Karşılama Kanalı ID: {KAYIT_KANALI_ID}')
    bot.add_view(RegistrationView())

# YENİ ÜYE

@bot.event
async def on_member_join(member: discord.Member):
    channel = bot.get_channel(KAYIT_KANALI_ID)

    try:
        guild = member.guild
        
        topluluk_rol = guild.get_role(TOPLULUK_ROLU_ID)
        
        if topluluk_rol is not None:
            await member.add_roles(topluluk_rol)
            print(f"Başarılı: {member.name} kullanıcısına '{topluluk_rol.name}' rolü verildi.")
        else:
            print(f"HATA: {TOPLULUK_ROLU_ID} ID'li Topluluk Üyesi rolü bulunamadı. Lütfen kontrol et.")
            
    except discord.Forbidden:
        print(f"HATA: {member.name} kullanıcısına rol verilemedi.")
    except Exception as e:
        print(f"ROL VERME HATASI: {e}")

    if channel is not None:

        message_content = f"Aramıza hoş geldin, {member.mention}! \n\nSunucumuzu tam olarak kullanabilmek için lütfen aşağıdaki butona basarak kayıt ol."
        await channel.send(message_content, view=RegistrationView())
    else:
        print(f"HATA: {KAYIT_KANALI_ID} ID'li kanal bulunamadı. Lütfen kontrol et.")


# TEST KOMUTU

@bot.command()
async def kayittest(ctx):
    print(f"{ctx.author} tarafından !kayittest komutu kullanıldı.")
    
    message_content = (
        f"Merhaba, {ctx.author.mention}! Bu bir kayıt sistemi testidir. \n\n"
        f"Sistemi denemek için lütfen aşağıdaki butona basarak kayıt olmayı dene."
    )
    await ctx.send(message_content, view=RegistrationView())

# ROL MENUSU KOMUTU

@bot.command()
@commands.has_permissions(administrator=True) 
async def rolmenusu(ctx):

    embed = discord.Embed(
        title="Almak istediğiniz rolleri seçin",
        description="Aşağıdaki menüye tıklayarak ilgilendiğiniz alanları seçebilir ve ilgili rollerinizi alabilirsiniz. Seçimlerinizi istediğiniz zaman değiştirebilirsiniz.🎮✅",
        color=discord.Color.magenta()
    )
    embed.set_thumbnail(url=ctx.guild.icon.url)

    await ctx.send(embed=embed, view=RoleSelectView())
    print(f"{ctx.author} tarafından '{ctx.channel.name}' kanalına rol menüsü gönderildi.")

    await ctx.message.delete()

# ÇALIŞTIR

bot.run(TOKEN)