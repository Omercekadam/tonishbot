# TonishBot - Nişantaşı Üniversitesi Discord Botu

#kütüphaneler
import discord
import os
import io
import datetime
import pytz 
from PIL import Image, ImageDraw, ImageFont, ImageOps
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
ROLALMA_KANALI_ID=int(os.getenv('ROLALMA_KANALI_ID'))
MODERATOR_ROLU_ID = int(os.getenv('MODERATOR_ROLU_ID')) 
TICKET_CATEGORY_ID = int(os.getenv('TICKET_CATEGORY_ID'))
TICKET_KANALI_ID = int(os.getenv('TICKET_KANALI_ID'))
KAYITSIZ_ROLE_ID = int(os.getenv('KAYITSIZ_ROLE_ID'))
WELCOME_CHANNEL_ID = int(os.getenv('WELCOME_CHANNEL_ID'))
ADMIN_COMMAND_CHANNEL_ID = int(os.getenv('ADMIN_COMMAND_CHANNEL_ID'))
ANNOUNCEMENT_CHANNEL_ID = int(os.getenv('ANNOUNCEMENT_CHANNEL_ID'))
EVENT_COUNTER_CHANNEL_ID = int(os.getenv('EVENT_COUNTER_CHANNEL_ID'))

# ROLLER

ROLE_OPTIONS = {
    # "ROL_ID": {"label": "rol adı", "emoji": "💻", "description": "rol açıklaması (isteğe bağlı)"},
    
    1430626208521126041: {
        "label": "Developer",
        "emoji": "💻",
        "description": "Oyun geliştirme ile ilgileniyorum."
    },
    1430627371353903115: {
        "label": "Artist (2D/3D)",
        "emoji": "🎨",
        "description": "2D/3D Görsel sanatlar ile ilgileniyorum."
    },
    1430627405600391208: {
        "label": "Level Designer",
        "emoji": "👾", # Veya 🎮
        "description": "Oyun tasarımı ile ilgileniyorum."
    },
    1430627431152091327: {
        "label": "Storyteller",
        "emoji": "✏️", # Veya 📝
        "description": "Hikaye anlatımı ile ilgileniyorum."
    },
    1430627474206625924: {
        "label": "UI/UX Designer",
        "emoji": "🚥", # Veya 🚦
        "description": "UI/UX tasarımı ile ilgileniyorum."
    },
    1430627494805110784: {
        "label": "Sound Artist",
        "emoji": "🎤", # Veya 🎧
        "description": "Ses ve müzik ile ilgileniyorum."
    },
    1430627516778942484: {
        "label": "Playtester",
        "emoji": "🕹️", # Veya ❔
        "description": "Oyun testi ve QA ile ilgileniyorum. Oyununuzun testi için @Playtester rolünü çağırabilirsiniz."
    },
    1430627543849111763: {
        "label": "Gamer",
        "emoji": "🎮", # Veya 🕹️
        "description": "Oyuncuyum ve oyun oynamayı seviyorum."
    },
    1430627564829020340: {
        "label": "Mentor",
        "emoji": "👑", # Veya 🌟
        "description": "İşaretlediğim konumda bilgiliyim ve diğer geliştiricilere rehberlik ediyorum."
    },
    1430627593274785862: {
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
        custom_id="kalici_kayit_butonu",
        emoji="👋" 
    )
    async def register_button_callback(self, interaction: discord.Interaction, button: Button):
        await interaction.response.send_modal(RegistrationModal())
        await interaction.user.remove_roles(interaction.guild.get_role(KAYITSIZ_ROLE_ID))
        print(f"Başarılı: {interaction.user.name} kullanıcısından 'Kayıtsız' rolü alındı.")
        await interaction.user.add_roles(interaction.guild.get_role(TOPLULUK_ROLU_ID))
        print(f"Başarılı: {interaction.user.name} kullanıcısına 'Topluluk Üyesi' rolü verildi.")

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
    kayit_channel = bot.get_channel(KAYIT_KANALI_ID)
    welcome_channel = bot.get_channel(WELCOME_CHANNEL_ID)


    try:
        guild = member.guild
        
        topluluk_rol = guild.get_role(TOPLULUK_ROLU_ID)
        kayitsiz_rol = guild.get_role(KAYITSIZ_ROLE_ID)

        if topluluk_rol is not None:
            await member.add_roles(kayitsiz_rol)
            print(f"Başarılı: {member.name} kullanıcısına '{kayitsiz_rol.name}' rolü verildi.")
        else:
            print(f"HATA: {KAYITSIZ_ROLE_ID} ID'li Kayıtsız rolü bulunamadı. Lütfen kontrol et.")
    
    except discord.Forbidden:
        print(f"HATA: {member.name} kullanıcısına rol verilemedi.")
    except Exception as e:
        print(f"ROL VERME HATASI: {e}")


    if welcome_channel is not None: 
            try:
                print(f"{member.name} için karşılama görseli oluşturuluyor...")
                
                background = Image.open("background.png").convert("RGBA")
                font_user = ImageFont.truetype("font.ttf", 50)
                font_welcome = ImageFont.truetype("font.ttf", 25)
                
               
                if member.avatar:
                    avatar_data = await member.avatar.read()
                else:
                    avatar_data = await member.default_avatar.read()
                avatar_image = Image.open(io.BytesIO(avatar_data)).convert("RGBA")
                
               
                avatar_size = (180, 180)
                avatar_image = avatar_image.resize(avatar_size)

                
                mask = Image.new("L", avatar_size, 0)
                draw_mask = ImageDraw.Draw(mask)
                draw_mask.ellipse((0, 0) + avatar_size, fill=255)
                
                
                draw_surface = background.copy()
                
                
                avatar_pos = (25, 35)
                draw_surface.paste(avatar_image, avatar_pos, mask)
                
                draw = ImageDraw.Draw(draw_surface)
                text_user = member.display_name
                user_pos = (210, 45)
                draw.text(user_pos, text_user, font=font_user, fill="#000000") 
                
                text_welcome = f"{member.guild.name}'a Hoşgeldin"
                welcome_pos = (210, 125)
                draw.text(welcome_pos, text_welcome, font=font_welcome, fill="#505050") 


                final_buffer = io.BytesIO()
                draw_surface.save(final_buffer, "PNG")
                final_buffer.seek(0)
                
                file_to_send = discord.File(final_buffer, filename="welcome.png")


                await welcome_channel.send(
                    f"Sunucumuza hoş geldin, {member.mention}! :tada:",
                    file=file_to_send
                )
                print(f"Görsel karşılama mesajı {member.name} için gönderildi.")

            except Exception as e:
                print(f"!!! GÖRSEL KARŞILAMA HATASI: {e} !!!")
                print(f"Eski tip metin mesajı gönderiliyor...")
                await welcome_channel.send(f"Aramıza hoş geldin, {member.mention}! :tada:")



    if kayit_channel is not None:

        message_content = f"Aramıza hoş geldin, {member.mention}! \n\nSunucumuzu tam olarak kullanabilmek için lütfen aşağıdaki butona basarak kayıt ol."
        await kayit_channel.send(message_content, view=RegistrationView())
    else:
        print(f"HATA: {KAYIT_KANALI_ID} ID'li kanal bulunamadı. Lütfen kontrol et.")

# KOMUTLAR

@bot.command()
async def kayittest(ctx):
    print(f"{ctx.author} tarafından !kayittest komutu kullanıldı.")
    
    message_content = (
        f"Merhaba, {ctx.author.mention}! Bu bir kayıt sistemi testidir. \n\n"
        f"Sistemi denemek için lütfen aşağıdaki butona basarak kayıt olmayı dene."
    )
    await ctx.send(message_content, view=RegistrationView())


#kayıt alma başlangıç

@bot.command()
async def kayital(ctx):
    print(f"{ctx.author} tarafından !kayital komutu kullanıldı.")
    
    message_content = (
        f"Merhaba, {ctx.author.mention}! Kayıt sistemini başlatmak için lütfen aşağıdaki butona basarak kayıt ol."
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

#Rolleri anlatan mesaj

@bot.command()
@commands.has_permissions(administrator=True) # Sadece Yöneticiler kullanabilsin
async def rolbilgi(ctx):
    """
    Rol bilgilendirme embed'ini bu komutun kullanıldığı kanala gönderir.
    """
    # Neden yapıyoruz? ROLE_OPTIONS'daki tüm rolleri ve açıklamalarını
    # listeleyen şık bir embed mesajı oluşturmak için.
    print(f"{ctx.author} tarafından !rolbilgi komutu kullanıldı.")
    
    try:
        # 1. Ana Embed Mesajını Oluştur
        embed = discord.Embed(
            title="📜 Sunucu Rolleri ve Açıklamaları",
            description="Aşağıdaki listeden rollerimizin ne anlama geldiğini öğrenebilirsiniz.\nRollerinizi almak veya değiştirmek için bu mesajın altındaki açılır menüyü kullanın.",
            color=0xFEE75C # Hoş bir sarı tonu (veya istediğin renk)
        )
        
        if ctx.guild.icon:
            embed.set_author(name=f"{ctx.guild.name} Rol Rehberi", icon_url=ctx.guild.icon.url)

        # 2. ROLE_OPTIONS Ayarlarını Döngüye Al ve Alan (Field) Olarak Ekle
        # Neden yapıyoruz? Ayar dosyasındaki tüm rolleri otomatik olarak
        # embed'e ekliyoruz. Yeni rol eklediğinde burayı değiştirmen gerekmez.
        if not ROLE_OPTIONS:
            await ctx.send("Hata: `ROLE_OPTIONS` ayarları boş görünüyor. Lütfen kod dosyasını kontrol et.")
            return

        for role_id, data in ROLE_OPTIONS.items():
            # data'dan bilgileri al, eğer emoji/açıklama yoksa varsayılan metin kullan
            emoji = data.get("emoji", "🔹") # Emoji yoksa mavi kare
            label = data.get("label", "İsimsiz Rol")
            description = data.get("description", "Açıklama belirtilmemiş.")
            
            # Embed'e yeni bir alan ekle
            embed.add_field(
                name=f"{emoji} {label}", # Başlık: 💻 Game Developer
                value=description,       # İçerik: Oyun geliştirme ile...
                inline=False # Her rolün tüm satırı kaplamasını sağlar (daha okunaklı)
                             # 'inline=True' yaparsan yan yana sıralar
            )

        # 3. Embed'i kanala gönder
        await ctx.send(embed=embed)
        
        # Komut mesajını temizle
        await ctx.message.delete()
        print(f"Rol bilgilendirme mesajı '{ctx.channel.name}' kanalına başarıyla gönderildi.")

    except discord.Forbidden:
        print(f"HATA: {ctx.channel.name} kanalına rol bilgi mesajı gönderilemedi. İZİN EKSİK.")
        await ctx.author.send(f"Hata: `{ctx.channel.name}` kanalına mesaj gönderemedim. 'Mesaj Gönder' ve 'Gömüleri Bağla' izinlerimi kontrol et.")
    except Exception as e:
        print(f"ROLBİLGİ KOMUTU HATASI: {e}")
        await ctx.author.send(f"`!rolbilgi` komutunda beklenmedik bir hata oluştu: `{e}`")

@rolbilgi.error
async def rolbilgi_error(ctx, error):
    # Neden yapıyoruz? Komutu yetkisi olmayan biri kullanırsa uyarıyoruz.
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Üzgünüm, bu komutu sadece sunucu yöneticileri kullanabilir.", delete_after=10)
        await ctx.message.delete(delay=10)
# --- YENİ BÖLÜM SONU ---

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


#Linkleri paylaşan komut

@bot.command()
async def link(ctx):

    print(f"{ctx.author} tarafından !link komutu kullanıldı.")
    
    uyeolma_link = "https://sks.nisantasi.edu.tr/uye-talep"
    instagram_link = "https://www.instagram.com/nishdott"
    linkedin_link = "https://www.linkedin.com/company/nishdot/about"
    whatsapp_link = "https://chat.whatsapp.com/DiufgZg3t1C2a4Y5L4iOLi"
    discord_link = "https://discord.gg/ddumxQaG"


    message_content = (
        f"**Sosyal medya hesaplarımız:**\n\n"
        f"**Kulübümüze üye olmak için:** <{uyeolma_link}>\n"
        f"**İnstagram:** <{instagram_link}>\n"
        f"**Whatsapp:** <{whatsapp_link}>\n"
        f"**Linkedin:** <{linkedin_link}>\n"
        f"**Discord:** <{discord_link}>\n"
    )

    try:

        await ctx.send(message_content)
        # await ctx.message.delete()
        
    except discord.Forbidden:
        print(f"HATA: {ctx.channel.name} kanalına !link mesajı gönderilemedi. İZİN EKSİK.")
    except Exception as e:
        print(f"!link KOMUTU HATASI: {e}")

#Kulüp bilgisi komutu

@bot.command()
async def bilgi(ctx):
    print(f"{ctx.author} tarafından !bilgi komutu kullanıldı.")
    
    message_content = (
        "İstanbul Nişantaşı Üniversitesi Dijital Oyun Tasarımı Kulübü yani kısaca **Nishdot**,\n Oyun geliştirmeyi, oyun tasarlamayı ve bu süreçte ekip çalışmasını öğrenmek isteyen herkes için kuruldu. Amacımız; fikirlerinizi hayata geçirebileceğiniz, yeni beceriler kazanabileceğiniz ve oyun dünyasına adım atabileceğiniz bir topluluk oluşturmak. Burada birlikte öğreniyor, üretiyor ve oyunların arkasındaki yaratıcı süreci keşfediyoruz!"
    )

    try:
        await ctx.send(message_content)
        # await ctx.message.delete()
        
    except discord.Forbidden:
        print(f"HATA: {ctx.channel.name} kanalına !bilgi mesajı gönderilemedi.")
    except Exception as e:
        print(f"!bilgi KOMUTU HATASI: {e}")

#Yardım komutu

@bot.command()
async def yardim(ctx):
    print(f"{ctx.author} tarafından !yardim komutu kullanıldı.")

    message_content = (
        "**Tonishbot Komutları:**\n\n"
        "**!link:**\nNishdot'un tüm hesaplarına ulaşmak için kullanabileceğiniz komut.\n\n" 
        "**!yk:**\nNishdot yönetim kurulunu görüntülemek için kullanabileceğiniz komut.\n"
    )

    try:
        await ctx.send(message_content)
        # await ctx.message.delete()

    except discord.Forbidden:
        print(f"HATA: {ctx.channel.name} kanalına !yk mesajı gönderilemedi.")
    except Exception as e:
        print(f"!yk KOMUTU HATASI: {e}")


#Yönetim kurulu komutu

@bot.command()
async def yk(ctx):
    print(f"{ctx.author} tarafından !yk komutu kullanıldı.")

    message_content = (
        "**Nishdot Yönetim Kurulu:**\n\n\n"
        "**Başkan:** \nYurdakul Efe Arıkan\n\n"
        "**Başkan Vekili:** \nMehmet Boran Bulut\n\n"
        "**Başkan Yardımcısı:** \nÖmer Soysal\n\n"
        "**Genel Sekreter:** \nEbru Karademir\n\n"
        "**Organizasyon Sorumlusu:** \nOğulcan Danişment\n\n"
        "**Sosyal Medya Koordinatörü:** \nFeyzanur Sarı\n\n"
        "**Etkinlik Sorumlusu:** \nKaan Mersin\nKerem Çetin\n\n"
    )

    try:
        await ctx.send(message_content)
        # await ctx.message.delete()

    except discord.Forbidden:
        print(f"HATA: {ctx.channel.name} kanalına !yk mesajı gönderilemedi.")
    except Exception as e:
        print(f"!yk KOMUTU HATASI: {e}")

#duyuru komutu

@bot.command()
@commands.has_permissions(administrator=True) 
async def duyuru(ctx, *, message: str):
    """
    Kullanım: !duyuru [@rol] <mesajınız>
    """
    
    if ctx.channel.id != ADMIN_COMMAND_CHANNEL_ID:
        try:
            await ctx.send(f"Duyuru komutu sadece <#{ADMIN_COMMAND_CHANNEL_ID}> kanalında kullanılabilir.", delete_after=10)
            await ctx.message.delete(delay=10)
        except discord.Forbidden:
            pass
        return

    target_channel = bot.get_channel(ANNOUNCEMENT_CHANNEL_ID)
    if not target_channel:
        print(f"HATA: {ANNOUNCEMENT_CHANNEL_ID} ID'li duyuru kanalı bulunamadı.")
        await ctx.send("Duyuru kanalı bulunamadı. Lütfen Railway 'Variables' panelini kontrol et.", ephemeral=True)
        return
    
    print(f"{ctx.author.display_name} bir duyuru yapıyor...")
    
#Embed oluşturma
    
    
    ping_content = None         
    description_content = message 

    if message.startswith("<@&"):
        end_index = message.find('>')
        if end_index != -1:
            ping_content = message[:end_index+1]
            description_content = message[end_index+1:].lstrip() 
    
    elif message.startswith("@everyone"):
        ping_content = "@everyone"
        description_content = message.replace("@everyone", "", 1).lstrip()
    elif message.startswith("@here"):
        ping_content = "@here"
        description_content = message.replace("@here", "", 1).lstrip()

    embed = discord.Embed(
        title="📣 Yeni Duyuru!",
        description=description_content,   
        color=0xFFEA00
    )
#duyuran 
    if ctx.author.avatar:
        embed.set_author(name=f"Duyuran: {ctx.author.display_name}", icon_url=ctx.author.avatar.url)
    else:
        embed.set_author(name=f"Duyuran: {ctx.author.display_name}")

#sunucu logosu
    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url)
    
#bot imzası
    if bot.user.avatar:
        embed.set_footer(text=f"{ctx.guild.name} | TonishBot", icon_url=bot.user.avatar.url)
    else:
        embed.set_footer(text=f"{ctx.guild.name} | TonishBot")
        
    embed.timestamp = discord.utils.utcnow() #zaman
    
    try:

        await target_channel.send(content=ping_content, embed=embed)
        print(f"Duyuru kanalı '{target_channel.name}' kanalına duyuru gönderildi.")
        await ctx.send("✅ Duyurun başarıyla gönderildi.", ephemeral=True, delete_after=10)

        await ctx.message.delete()
        
    except discord.Forbidden:
        print("HATA: Duyuru kanalına mesaj gönderme iznim yok.")
        await ctx.send("Hata: Duyuru kanalına mesaj gönderme iznim yok. İzinlerimi kontrol et.")
    except Exception as e:
        print(f"DUYURU KOMUTU HATASI: {e}")
        await ctx.send(f"Bilinmeyen bir hata oluştu: {e}")

@duyuru.error
async def duyuru_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Bu komutu kullanmak için 'Yönetici' iznine sahip olmalısın.", delete_after=10)
    elif isinstance(error, commands.MissingRequiredArgument):

        await ctx.send("Hata: Lütfen duyuru için bir mesaj gir. Örnek: `!duyuru @everyone Herkese merhaba!`", delete_after=15)
    else:
        print(f"Duyuru komutunda beklenmeyen hata: {error}")
    
    try:
        await ctx.message.delete()
    except:
        pass

@bot.command()
@commands.has_permissions(administrator=True)
async def etkinliksayaci(ctx, tarih_str: str, saat_str: str, etkinlik_adi: str, *, aciklama: str):
    """
    Kullanım: !etkinliksayaci "GG.AA.YYYY" "HH:MM" "Etkinlik Adı" "Etkinlik hakkında bilgi..."
    (Çok kelimeli adlar ve açıklamalar için tırnak " " kullanın!)
    """

    if ctx.channel.id != ADMIN_COMMAND_CHANNEL_ID:
        await ctx.send(f"Bu komut sadece <#{ADMIN_COMMAND_CHANNEL_ID}> kanalında kullanılabilir.", delete_after=10)
        await ctx.message.delete(delay=10)
        return

    target_channel = bot.get_channel(EVENT_COUNTER_CHANNEL_ID)
    if not target_channel:
        print(f"HATA: {EVENT_COUNTER_CHANNEL_ID} ID'li etkinlik kanalı bulunamadı.")
        await ctx.send("Etkinlik kanalı bulunamadı. Lütfen Railway 'Variables' panelini kontrol et.", ephemeral=True)
        return

    try:
        turkey_tz = pytz.timezone("Europe/Istanbul")

        dt_str = f"{tarih_str} {saat_str}"
        local_dt = datetime.datetime.strptime(dt_str, "%d.%m.%Y %H:%M")
        
        aware_dt = turkey_tz.localize(local_dt)
        
        timestamp_unix = int(aware_dt.timestamp())

    except ValueError:
        await ctx.send("Hata: Tarih veya saat formatı yanlış. Lütfen `GG.AA.YYYY` ve `HH:MM` formatlarını kullanın.\nÖrnek: `!etkinliksayaci \"28.10.2025\" \"19:00\" \"Oyun Gecesi\" \"Açıklama\"`", delete_after=20)
        await ctx.message.delete(delay=20)
        return
    except Exception as e:
        print(f"ETKİNLİKSAYACI ZAMAN HATASI: {e}")
        await ctx.send(f"Bilinmeyen bir zaman hatası oluştu: {e}", ephemeral=True)
        return


    embed = discord.Embed(
        title=f"🗓️ {etkinlik_adi}", 
        description=aciklama,  
        color=0xeb596d 
    )
    
    embed.add_field(
        name="Etkinlik Zamanı",
        value=f"<t:{timestamp_unix}:F>",
        inline=False
    )
    
    embed.add_field(
        name="Kalan Süre",
        value=f"<t:{timestamp_unix}:R>",
        inline=False
    )

    if ctx.guild.icon:
        embed.set_thumbnail(url=ctx.guild.icon.url) 
    
    embed.set_footer(text=f"{ctx.guild.name} Etkinlik Takvimi")
    embed.timestamp = discord.utils.utcnow()

    try:
        await target_channel.send(embed=embed)
        await ctx.send("✅ Etkinlik sayacı başarıyla duyuru kanalına gönderildi.", ephemeral=True, delete_after=10)
        await ctx.message.delete()
        
    except Exception as e:
        print(f"ETKİNLİKSAYACI GÖNDERME HATASI: {e}")
        await ctx.send(f"Embed gönderilirken hata oluştu: {e}", ephemeral=True)

@etkinliksayaci.error
async def etkinliksayaci_error(ctx, error):
    if isinstance(error, commands.MissingPermissions):
        await ctx.send("Bu komutu kullanmak için 'Yönetici' iznine sahip olmalısın.", delete_after=10)
    elif isinstance(error, commands.MissingRequiredArgument):
        await ctx.send(
            "Hata: Eksik argüman girdin.\n**Kullanım:** `!etkinliksayaci \"Tarih\" \"Saat\" \"Başlık\" \"Açıklama\"`\n"
            "**Örnek:** `!etkinliksayaci \"28.10.2025\" \"21:00\" \"Büyük Oyun Gecesi\" \"Herkes davetlidir!\"`\n"
            "(Lütfen çok kelimeli kısımlar için tırnak işareti `\" \"` kullanın.)",
            delete_after=30
        )
    else:
        print(f"Etkinlik sayacı komutunda beklenmeyen hata: {error}")
    
    try:
        await ctx.message.delete()
    except:
        pass



# ÇALIŞTIR

bot.run(TOKEN)