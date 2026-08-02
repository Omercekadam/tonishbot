# TonishBot Ubuntu VDS Kurulum ve Dağıtım Rehberi

Bu rehber, botunuzu Railway'den kendi Ubuntu sunucunuza (VDS) taşımanız için gereken adımları içerir.

> [!TIP]
> **İpucu:** Bu dosyayı VS Code'da okuyorsanız, sağ üstteki **"Open Preview"** butonuna (veya `CTRL + SHIFT + V` tuşlarına) basarak okuma moduna geçin. Böylece kodları kopyalarken yanlışlıkla tırnak işaretlerini (` ``` `) kopyalamazsınız.

> [!WARNING]
> **Bu dosyaya ASLA gerçek token, şifre veya API anahtarı yazmayın.** Bu dosya git ile
> takip ediliyor; buraya yazılan her sır repo geçmişine kalıcı olarak işlenir.
> Sırlar sadece sunucudaki `.env` dosyasında durmalıdır (`.env` `.gitignore`'da).

## 1. Gerekli Paketlerin Kurulumu

Sunucuya bağlandıktan sonra, sistemi güncelleyin ve gerekli araçları kurun:

```bash
sudo apt update && sudo apt upgrade -y
```

```bash
sudo apt install python3 python3-pip python3-venv git -y
```

## 2. Projeyi Çekme (GitHub)

Botunuzu sunucuya indirin.

### 🔒 Özel (Private) Repo Kullanıyorsanız

Eğer reponuz gizliyse, GitHub'dan bir **Personal Access Token (Classic)** oluşturmanız gerekir.

1.  GitHub Ayarları -> Developer Settings -> Personal Access Tokens -> Tokens (Classic) yolunu izleyin.
2.  "Generate new token" deyin, `repo` yetkisini seçin ve tokeni kopyalayın.
3.  Sunucuda şu formatta klonlayın (`KULLANICI_ADI` ve `TOKEN` kısımlarını kendi bilgilerinizle değiştirin):

```bash
cd /home
git clone https://KULLANICI_ADI:TOKEN@github.com/KULLANICI_ADI/tonishbot.git
cd tonishbot
```

> [!CAUTION]
> Token'ı yazdığınız komut sunucuda `~/.bash_history` dosyasına kaydolur ve
> `.git/config` içinde düz metin olarak durur. Daha güvenli yöntem: HTTPS yerine
> **SSH deploy key** kullanmak, ya da `git clone` sonrası
> `git remote set-url origin https://github.com/KULLANICI_ADI/tonishbot.git` yapıp
> `git config credential.helper store` ile kimliği ayrı tutmak.

### 🌍 Herkese Açık (Public) Repo Kullanıyorsanız

```bash
cd /home
git clone https://github.com/KULLANICI_ADI/tonishbot.git
cd tonishbot
```

## 3. Sanal Ortam ve Kütüphaneler

Python kütüphanelerini izole etmek için sanal ortam (venv) kurun:

```bash
python3 -m venv venv
```

```bash
source venv/bin/activate
```

```bash
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

5. Dosyayı sadece sahibinin okuyabilmesi için izinleri daraltın:

```bash
chmod 600 .env
```

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
```

```bash
sudo systemctl enable tonishbot
```

```bash
sudo systemctl start tonishbot
```

4. Durumunu kontrol etmek için:

```bash
sudo systemctl status tonishbot
```

## 6. Güncelleme Nasıl Yapılır?

Bilgisayarınızda kodları düzenleyip GitHub'a `push` attıktan sonra sunucuda şu komutları girmeniz yeterli:

```bash
cd /home/tonishbot && git pull && sudo systemctl restart tonishbot
```

Bu işlem botu son sürüme günceller ve yeniden başlatır.

> [!TIP]
> Veritabanı şeması değişen bir güncellemede önce yedek alın:
> `cp economy.db economy.db.bak && cp steam.db steam.db.bak`

## 7. Sunucu Yönetim Komutları

Botunuzu yönetmek için aşağıdaki komutları kullanabilirsiniz:

### Botu Durdurma

```bash
sudo systemctl stop tonishbot
```

### Botu Başlatma

```bash
sudo systemctl start tonishbot
```

### Botu Yeniden Başlatma

```bash
sudo systemctl restart tonishbot
```

### Durum Kontrolü

Botun çalışıp çalışmadığını ve son logları görmek için:

```bash
sudo systemctl status tonishbot
```

### Logları Canlı İzleme

Botun loglarını anlık olarak takip etmek için:

```bash
journalctl -u tonishbot -f
```

### Otomatik Başlatmayı Açma/Kapatma

Sunucu yeniden başladığında botun otomatik açılmasını **kapatmak** için:

```bash
sudo systemctl disable tonishbot
```

Tekrar **açmak** için:

```bash
sudo systemctl enable tonishbot
```

### Zorla Kapatma

Bot normal `stop` komutuna yanıt vermiyorsa:

```bash
sudo systemctl kill -s SIGKILL tonishbot
```

## 8. Sorun Giderme (Troubleshooting)

### Bot Çok Yavaş Açılıyor veya Bağlanamıyor (DNS Sorunu)

Eğer loglarda `ClientConnectorDNSError` hatası alıyorsanız veya `/etc/resolv.conf` dosyasında "Do not edit" uyarısı görüyorsanız, kalıcı çözüm şudur:

1. `resolved.conf` dosyasını açın:

```bash
sudo nano /etc/systemd/resolved.conf
```

2. `#DNS=` yazan satırı bulun, başındaki `#` işaretini kaldırın ve şöyle değiştirin:

```ini
DNS=8.8.8.8 8.8.4.4
```

3. Kaydedip çıkın (`CTRL + O`, `Enter`, `CTRL + X`).

4. DNS servisini ve botu yeniden başlatın:

```bash
sudo systemctl restart systemd-resolved && sudo systemctl restart tonishbot
```

### "database is locked" Hatası

Botun birden fazla kopyası aynı anda çalışıyor olabilir. Kontrol edin:

```bash
ps aux | grep bot.py
```

Fazladan süreç varsa `sudo systemctl restart tonishbot` ile tek kopyaya indirin.

## 9. GitHub Token Süresi Dolunca (Authentication Failed Hatası)

Eğer `git pull` yaparken "Authentication failed" veya "Password authentication was removed" hatası alıyorsanız, tokeninizin süresi dolmuştur.

1. **Eski tokeni iptal edin:** GitHub -> Settings -> Developer settings -> Personal access tokens -> ilgili tokenin yanından **Revoke**.
2. **Yeni Token Alın:** Aynı ekrandan yeni bir token oluşturun (`repo` yetkisi yeterli).
3. **Sunucuda URL'yi Güncelleyin:**

```bash
cd /home/tonishbot
git remote set-url origin https://KULLANICI_ADI:YENI_TOKEN@github.com/KULLANICI_ADI/tonishbot.git
```

4. **Test Edin:** `git pull` yazarak hatasız çalıştığını doğrulayın.

> [!IMPORTANT]
> Yeni tokeni bu dosyaya **yazmayın**. Sadece sunucudaki komuta yapıştırın.
> Bu rehberde daha önce gerçek tokenler bulunuyordu; hepsi iptal edilmiştir.
