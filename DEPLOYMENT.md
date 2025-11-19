# TonishBot Ubuntu VDS Kurulum ve Dağıtım Rehberi

Bu rehber, botunuzu Railway'den kendi Ubuntu sunucunuza (VDS) taşımanız için gereken adımları içerir.

> [!TIP] > **İpucu:** Bu dosyayı VS Code'da okuyorsanız, sağ üstteki **"Open Preview"** butonuna (veya `CTRL + SHIFT + V` tuşlarına) basarak okuma moduna geçin. Böylece kodları kopyalarken yanlışlıkla tırnak işaretlerini (` ``` `) kopyalamazsınız.

## 1. Gerekli Paketlerin Kurulumu

Sunucuya bağlandıktan sonra, sistemi güncelleyin ve gerekli araçları kurun:

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install python3 python3-pip python3-venv git -y
```

## 2. Projeyi Çekme (GitHub)

Botunuzu sunucuya indirin.

### 🔒 Özel (Private) Repo Kullanıyorsanız

Eğer reponuz gizliyse, GitHub'dan bir **Personal Access Token (Classic)** oluşturmanız gerekir.

1.  GitHub Ayarları -> Developer Settings -> Personal Access Tokens -> Tokens (Classic) yolunu izleyin.
2.  "Generate new token" deyin, `repo` yetkisini seçin ve tokeni kopyalayın.
3.  Sunucuda şu formatta klonlayın:

```bash
cd /home
git clone https://Omercekadam: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@github.com/Omercekadam/tonishbot.git
cd tonishbot
```

_(Not: `kullaniciadi` ve `tokeniniz` kısımlarını kendi bilgilerinizle değiştirin.)_

### 🌍 Herkese Açık (Public) Repo Kullanıyorsanız

```bash
cd /home
git clone https://github.com/kullaniciadi/tonishbot.git
cd tonishbot
```

## 3. Sanal Ortam ve Kütüphaneler

Python kütüphanelerini izole etmek için sanal ortam (venv) kurun:

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

## 4. .env Dosyası (ÖNEMLİ!)

Railway'deki değişkenlerinizi buraya eklemelisiniz.

1. Dosyayı oluşturun:

```bash
nano .env
```

2. Açılan ekrana `.env.example` dosyasındaki değişkenleri yapıştırın ve **kendi değerlerinizi** eşittir işaretinden sonra boşluk bırakmadan yazın.

   - `DISCORD_TOKEN=...`
   - `GEMINI_API_KEY=...`
   - Diğer ID'ler...

3. Kaydetmek için: `CTRL + O`, sonra `Enter`.
4. Çıkmak için: `CTRL + X`.

## 5. Botu Arka Planda Çalıştırma (Systemd)

Botun terminali kapatsanız bile çalışması ve sunucu yeniden başladığında otomatik açılması için bir servis oluşturun.

1. Servis dosyasını oluşturun:

```bash
sudo nano /etc/systemd/system/tonishbot.service
```

2. İçine şunları yapıştırın:

```ini
[Unit]
Description=TonishBot Discord Botu
After=network.target

[Service]
User=root
WorkingDirectory=/home/tonishbot
ExecStart=/home/tonishbot/venv/bin/python /home/tonishbot/bot.py
Restart=always

[Install]
WantedBy=multi-user.target
```

3. Servisi başlatın:

```bash
sudo systemctl daemon-reload
sudo systemctl enable tonishbot
sudo systemctl start tonishbot
```

4. Durumunu kontrol etmek için:

```bash
sudo systemctl status tonishbot
```

## 6. Güncelleme Nasıl Yapılır?

Bilgisayarınızda kodları düzenleyip GitHub'a `push` attıktan sonra sunucuda şu komutları girmeniz yeterli:

```bash
cd /home/tonishbot
git pull
sudo systemctl restart tonishbot
```

Bu işlem botu son sürüme günceller ve yeniden başlatır.
