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
MODERATOR_ROLU_ID = int(os.getenv('MODERATOR_ROLU_ID')) 
TICKET_CATEGORY_ID = int(os.getenv('TICKET_CATEGORY_ID'))
TICKET_KANALI_ID = int(os.getenv('TICKET_KANALI_ID'))

# ROLLER

ROLE_OPTIONS = {
    # "ROL_ID": {"label": "rol adı", "emoji": "💻", "description": "rol açıklaması (isteğe bağlı)"},
    
    1430319278334410824: {
        "label": "Developer",
        "emoji": "💻",
        "description": "Oyun geliştirme ile ilgileniyorum."
    },
    1430324401110257784: {
        "label": "Artist (2D/3D)",
        "emoji": "🎨",
        "description": "2D/3D Görsel sanatlar ile ilgileniyorum."
    },
    1430324364884316232: {
        "label": "Level Designer",
        "emoji": "👾", # Veya 🎮
        "description": "Oyun tasarımı ile ilgileniyorum."
    },
        1430324364884316232: {
        "label": "Storyteller",
        "emoji": "✏️", # Veya 📝
        "description": "Hikaye anlatımı ile ilgileniyorum."
    },
        1430324364884316232: {
        "label": "UI/UX Designer",
        "emoji": "🚥", # Veya 🚦
        "description": "UI/UX tasarımı ile ilgileniyorum."
    },
    123456789000000005: {
        "label": "Sound Artist",
        "emoji": "🎤", # Veya 🎧
        "description": "Ses ve müzik ile ilgileniyorum."
    },
        1430324364884316232: {
        "label": "Playtester",
        "emoji": "🕹️", # Veya ❔
        "description": "Oyun testi ve QA ile ilgileniyorum. Oyunlarınızı test etmemi isterseniz @Playtester rolünü seçebilirsiniz."
    },
    123456789000000006: {
        "label": "Gamer",
        "emoji": "🎮", # Veya 🕹️
        "description": "Oyuncuyum ve oyun oynamayı seviyorum."
    },
        123456789000000006: {
        "label": "Mentor",
        "emoji": "👑", # Veya 🌟
        "description": "İşaretlediğim konumda bilgiliyim ve diğer geliştiricilere rehberlik ediyorum."
    },
        1430324364884316232: {
        "label": "Duyuru AL",
        "emoji": "🔔", # Veya 🛎️
        "description": "Sadece @everyone duyurularını almak istemiyorum. Tüm etkinlikleri takip etmek istiyorum."
    },
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
        emoji='👋'
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


# Ticket sistemi görüntüleri

class TicketCloseView(View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.button(
        label="Ticketi Kapat",
        style=discord.ButtonStyle.danger, 
        custom_id="kalici_ticket_kapat_butonu",
        emoji="🔒" 
    )

    #ticketi kapat tuşuna basıldıktan sonra
    
    async def close_ticket_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer() 
        
        channel = interaction.channel

        if not channel.topic or not channel.topic.startswith("Ticket sahibi: "):
            await interaction.followup.send("Hata: Bu kanal bir ticket kanalı olarak görünmüyor.", ephemeral=True)
            return

        try:
            user_id_str = channel.topic.split("Ticket sahibi: ")[1]
            ticket_owner = interaction.guild.get_member(int(user_id_str))
        except:
            await interaction.followup.send("Hata: Ticket sahibi bulunamadı (Belki sunucudan ayrıldı?).", ephemeral=True)
            return

        mod_role = interaction.guild.get_role(MODERATOR_ROLU_ID)
        
        is_owner = (ticket_owner is not None) and (interaction.user.id == ticket_owner.id)
        is_mod = (mod_role is not None) and (mod_role in interaction.user.roles)

        if not is_owner and not is_mod:
            await interaction.followup.send("Bu ticketi sadece sahibi veya bir moderatör kapatabilir.", ephemeral=True)
            return

        if ticket_owner: 
            current_overwrites = channel.overwrites_for(ticket_owner)
            current_overwrites.send_messages = False
            
            await channel.set_permissions(ticket_owner, overwrite=current_overwrites, reason="Ticket kapatıldı.")
        
        button.disabled = True
        button.label = "Ticket Kapatıldı"
        await interaction.message.edit(view=self)

        await interaction.followup.send(f"Ticket, {interaction.user.mention} tarafından kapatıldı. Kanal kilitlendi.")
        print(f"Ticket #{channel.name}, {interaction.user.name} tarafından kapatıldı.")


#Ticket oluşturma görünümü

class TicketCreationView(View):
    def __init__(self):
        super().__init__(timeout=None) 

    @discord.ui.button(
        label="Ticket Oluştur",
        style=discord.ButtonStyle.primary, 
        emoji="📩", 
        custom_id="kalici_ticket_tusu" 
    )
    async def create_ticket_button(self, interaction: discord.Interaction, button: Button):
        await interaction.response.defer(ephemeral=True) 


        mod_role = interaction.guild.get_role(MODERATOR_ROLU_ID)
        category = interaction.guild.get_channel(TICKET_CATEGORY_ID)
        
        if not mod_role or not category:
            await interaction.followup.send("Hata: Bot ayarları eksik. Lütfen yöneticiye bildirin (Moderatör rolü veya Ticket kategorisi bulunamadı).", ephemeral=True)
            print("HATA: MODERATOR_ROLE_ID veya TICKET_CATEGORY_ID ayarları yanlış.")
            return


        channel_name = f"ticket-{interaction.user.id}"
        existing_channel = discord.utils.get(interaction.guild.text_channels, name=channel_name, category=category)
        
        if existing_channel:
            await interaction.followup.send(f"Zaten açık bir ticket'ınız bulunuyor: {existing_channel.mention}", ephemeral=True)
            return


        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(view_channel=False), # @everyone göremez
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True), # Ticket sahibi görür/yazar
            mod_role: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True), # Moderatörler görür/yazar
            bot.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True) # Botun kendisi de görmeli
        }
        
        try:
            new_channel = await interaction.guild.create_text_channel(
                name=channel_name,
                category=category,
                overwrites=overwrites,
                topic=f"Ticket sahibi: {interaction.user.id}" # Kapatma butonu için gizli bilgi
            )
        except discord.Forbidden:
            await interaction.followup.send("Hata: Botun 'Kanal Oluşturma' veya 'İzinleri Ayarlama' yetkisi yok.", ephemeral=True)
            print("HATA: Ticket kanalı oluşturulamadı. İZİN EKSİK (Forbidden).")
            return
        except Exception as e:
            await interaction.followup.send(f"Bilinmeyen bir hata oluştu: {e}", ephemeral=True)
            print(f"TICKET OLUŞTURMA HATASI: {e}")
            return
            
# YENİ KANALDAKİ KAPAT TUŞU VE EMBED       

        embed = discord.Embed(
            title=f"Destek Talebi Başlatıldı",
            description=f"Merhaba {interaction.user.mention}, talebin alındı!\nLütfen sorununu buraya detaylıca yaz. Bir moderatör kısa süre içinde seninle ilgilenecektir.",
            color=0x2ECC71 
        )
        
        if interaction.user.avatar:
            embed.set_author(name=f"{interaction.user.display_name} (ID: {interaction.user.id})", icon_url=interaction.user.avatar.url)
        else:
            embed.set_author(name=f"{interaction.user.display_name} (ID: {interaction.user.id})")

        if interaction.user.avatar:
            embed.set_thumbnail(url=interaction.user.avatar.url)


        embed.add_field(name="Ticket Sahibi", value=interaction.user.mention, inline=True)
        embed.add_field(name="Yetkili Ekip", value=mod_role.mention, inline=True)

        embed.timestamp = discord.utils.utcnow()

        embed.set_footer(text=f"Ticket Kanalı: #{new_channel.name}")

        await interaction.followup.send(f"Ticket'ınız başarıyla oluşturuldu: {new_channel.mention}", ephemeral=True)
        print(f"{interaction.user.name} (ID: {interaction.user.id}) yeni bir ticket oluşturdu: #{new_channel.name}")
        await new_channel.send(f"{interaction.user.mention}, {mod_role.mention} rolü bilgilendirildi.", embed=embed, view=TicketCloseView())
        

# BOT ÇALIŞTI

@bot.event
async def on_ready():
    print(f'Bot {bot.user} olarak giriş yaptı!')
    print(f'Token: {TOKEN[:5]}...') 
    print(f'Karşılama Kanalı ID: {KAYIT_KANALI_ID}')
    bot.add_view(RegistrationView())
    bot.add_view(RoleSelectView())
    bot.add_view(TicketCreationView())
    bot.add_view(TicketCloseView())

    print("Tüm kalıcı görünümler (View) başarıyla yüklendi.")

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


# !KAYITTEST KOMUTU

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
        description="Aşağıdaki menüye tıklayarak ilgilendiğiniz alanları seçebilir ve ilgili rollerinizi alabilirsiniz. Seçimlerinizi istediğiniz zaman bu kanaldan değiştirebilirsiniz.🎮✅",
        color=discord.Color.magenta()
    )
    embed.set_thumbnail(url=ctx.guild.icon.url)

    await ctx.send(embed=embed, view=RoleSelectView())
    print(f"{ctx.author} tarafından '{ctx.channel.name}' kanalına rol menüsü gönderildi.")

    await ctx.message.delete()

#Ticket mesajını kurma

@bot.command()
@commands.has_permissions(administrator=True) 
async def ticketkur(ctx, *, mesaj="Destek almak için aşağıdaki butona tıklayarak bir ticket oluşturabilirsiniz."):
    """
    Ticket oluşturma embed'ini ve butonunu bu komutun kullanıldığı kanala gönderir.
    """
    try:
        embed = discord.Embed(
            title="📩 Destek Talebi Oluşturun", 
            description=mesaj,
            color=0xeb596d
        )

        if ctx.guild.icon:
            embed.set_author(name=f"{ctx.guild.name} | Destek Kanalı", icon_url=ctx.guild.icon.url)
        else:
            embed.set_author(name=f"{ctx.guild.name} | Destek Kanalı")

        embed.add_field(
            name="Süreç Nasıl İşler?",
            value="1. `Ticket Oluştur` butonuna basın.\n2. Sizin için özel bir kanal oluşturulacak.\n3. Sorununuzu oraya yazın, bir yetkili size yardımcı olacak.",
            inline=False 
        )
        embed.add_field(name="Gizlilik", value="Kanalı sadece siz ve yetkililer görebilir.", inline=True)
        embed.add_field(name="Kurallar", value="Lütfen sabırlı olun ve gereksiz ticket açmayın.", inline=True)

        embed.set_image(url="https://i.imgur.com/example.png") # <-- KENDİ BANNER LİNKİNİ GİR imgur.coma yükle

        embed.set_footer(text="TonishBot Ticket Sistemi", icon_url=bot.user.avatar.url if bot.user.avatar else None)
        embed.timestamp = discord.utils.utcnow() 

        await ctx.send(embed=embed, view=TicketCreationView())
        print(f"{ctx.author} tarafından '{ctx.channel.name}' kanalına ticket kurulum mesajı gönderildi.")
        
        await ctx.message.delete()
        
    except discord.Forbidden:
        print(f"HATA: {ctx.channel.name} kanalına ticket kurulum mesajı gönderilemedi. İZİN EKSİK.")
        await ctx.author.send(f"Hata: `{ctx.channel.name}` kanalına mesaj gönderemedim. 'Mesaj Gönder' ve 'Gömüleri Bağla' izinlerimi kontrol et.")
    except Exception as e:
        print(f"TICKETKUR KOMUTU HATASI: {e}")

@ticketkur.error
async def ticketkur_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, bu komutu sadece sunucu yöneticileri kullanabilir.", delete_after=10)
        await ctx.message.delete(delay=10)

# ÇALIŞTIR

bot.run(TOKEN)