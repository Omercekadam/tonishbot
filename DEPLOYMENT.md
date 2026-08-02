# TonishBot Ubuntu VDS Kurulum ve Dağıtım Rehberi

Bu rehber, botunuzu Railway'den kendi Ubuntu sunucunuza (VDS) taşımanız için gereken adımları içerir.

> [!TIP]
> **İpucu:** Bu dosyayı VS Code'da okuyorsanız, sağ üstteki **"Open Preview"** butonuna (veya `CTRL + SHIFT + V` tuşlarına) basarak okuma moduna geçin. Böylece kodları kopyalarken yanlışlıkla tırnak işaretlerini (` ``` `) kopyalamazsınız.

> [!WARNING]
> **Bu dosyaya ASLA gerçek token, şifre veya API anahtarı yazmayın.** Bu dosya git ile
> takip ediliyor; buraya yazılan her sır repo geçmişine kalıcı olarak işlenir.
> Sırlar sadece sunucudaki `.env` dosyasında durmalıdır (`.env` `.gitignore`'da).

> [!CAUTION]
> **Bu VDS aynı anda bir web sitesi (nginx + gunicorn + PostgreSQL + Redis) ve başka
> bir bot barındırıyor, ve RAM'i sınırın çok yakınında çalışıyor** (hosting sağlayıcının
> VMware balloon driver ile RAM'in büyük bir kısmını host'a geri çektiği tespit edildi —
> bkz. [Bölüm 10](#10-vmware-balloon-ram-sorunu-paylaşımlı-vdslerde), sağlayıcıya bildirildi,
> yanıt bekleniyor). Bu yüzden **6. Bölümdeki systemd tanımına sert bir `MemoryMax` konuldu**
> — bot RAM sınırını aşarsa sadece kendisi kapanıp yeniden başlar, site veya diğer bot
> etkilenmez. Yine de kurulumdan hemen sonra `journalctl -u tonishbot -f` ile birkaç dakika
> izleyin ve sağlayıcıdan yanıt gelene kadar sunucunun genel RAM durumunu (`free -h`,
> `vmware-toolbox-cmd stat balloon`) takip edin.

## 1. Gerekli Paketlerin Kurulumu

Sunucuya bağlandıktan sonra, sistemi güncelleyin ve gerekli araçları kurun:

```bash
sudo apt update && sudo apt upgrade -y
```

```bash
sudo apt install python3 python3-pip python3-venv git -y
```

## 2. Özel Kullanıcı Oluşturma

Bot bu sunucuda web sitesi ve başka bir botla aynı kaynağı paylaşıyor. Botu `root` yerine
kendi izole sistem kullanıcısıyla çalıştırmak (PostgreSQL ve Redis'in zaten yaptığı gibi),
biri ele geçirilirse diğerlerinin etkilenmemesini sağlar.

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin tonishbot
```

```bash
sudo mkdir -p /opt/tonishbot
```

```bash
sudo chown tonishbot:tonishbot /opt/tonishbot
```

Bu, giriş yapılamayan (`nologin`), sadece bu bot için var olan bir kullanıcı ve ona ait
`/opt/tonishbot` dizini oluşturur. Aşağıdaki adımların çoğu `sudo -u tonishbot` ile bu
kullanıcı adına çalıştırılacak — dosyaların sahibi karışmasın diye.

## 3. Projeyi Çekme (GitHub)

Botu `/opt/tonishbot` içine, `tonishbot` kullanıcısı adına indirin.

### 🔒 Özel (Private) Repo Kullanıyorsanız

Eğer reponuz gizliyse, GitHub'dan bir **Personal Access Token (Classic)** oluşturmanız gerekir.

1.  GitHub Ayarları -> Developer Settings -> Personal Access Tokens -> Tokens (Classic) yolunu izleyin.
2.  "Generate new token" deyin, `repo` yetkisini seçin ve tokeni kopyalayın.
3.  Sunucuda şu formatta klonlayın (`KULLANICI_ADI` ve `TOKEN` kısımlarını kendi bilgilerinizle değiştirin):

```bash
sudo -u tonishbot git clone https://KULLANICI_ADI:TOKEN@github.com/KULLANICI_ADI/tonishbot.git /opt/tonishbot
```

> [!CAUTION]
> Token'ı yazdığınız komut sunucuda `~/.bash_history` dosyasına kaydolur ve
> `.git/config` içinde düz metin olarak durur. Daha güvenli yöntem: HTTPS yerine
> **SSH deploy key** kullanmak, ya da klonladıktan sonra
> `sudo -u tonishbot git -C /opt/tonishbot remote set-url origin https://github.com/KULLANICI_ADI/tonishbot.git`
> yapıp `git config credential.helper store` ile kimliği ayrı tutmak.

### 🌍 Herkese Açık (Public) Repo Kullanıyorsanız

```bash
sudo -u tonishbot git clone https://github.com/KULLANICI_ADI/tonishbot.git /opt/tonishbot
```

## 4. Sanal Ortam ve Kütüphaneler

Python kütüphanelerini izole etmek için sanal ortam (venv) kurun:

```bash
sudo -u tonishbot python3 -m venv /opt/tonishbot/venv
```

```bash
sudo -u tonishbot /opt/tonishbot/venv/bin/pip install -r /opt/tonishbot/requirements.txt
```

## 5. .env Dosyası (ÖNEMLİ!)

Railway'deki değişkenlerinizi buraya eklemelisiniz.

1. Dosyayı oluşturun:

```bash
sudo -u tonishbot nano /opt/tonishbot/.env
```

2. Açılan ekrana `.env.example` dosyasındaki değişkenleri yapıştırın ve **kendi değerlerinizi** eşittir işaretinden sonra boşluk bırakmadan yazın.

   - `DISCORD_TOKEN=...`
   - `GEMINI_API_KEY=...`
   - Diğer ID'ler...

3. Kaydetmek için: `CTRL + O`, sonra `Enter`.
4. Çıkmak için: `CTRL + X`.

5. Dosyayı sadece sahibinin okuyabilmesi için izinleri daraltın:

```bash
sudo chmod 600 /opt/tonishbot/.env
```

## 6. Botu Arka Planda Çalıştırma (Systemd)

Botun terminali kapatsanız bile çalışması ve sunucu yeniden başladığında otomatik açılması için bir servis oluşturun.

1. Servis dosyasını oluşturun:

```bash
sudo nano /etc/systemd/system/tonishbot.service
```

2. İçine şunları yapıştırın:

```ini
[Unit]
Description=TonishBot Discord Botu
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
User=tonishbot
Group=tonishbot
WorkingDirectory=/opt/tonishbot
ExecStart=/opt/tonishbot/venv/bin/python /opt/tonishbot/bot.py
Restart=always
RestartSec=5

# Bu sunucu aynı anda başka servisler barındırıyor ve RAM sınırının yakınında
# çalışıyor (bkz. Bölüm 10). Bot bu tavanı aşarsa systemd SADECE BOTU kapatıp
# yeniden başlatır — site veya diğer bot etkilenmez.
#
# 512M/384M başlangıç değeri — normal çalışırken hiç yaklaşılmayacak kadar geniş
# tutuldu (google-generativeai'nin gerçek import maliyeti henüz ölçülmedi).
# Bot birkaç gün çalıştıktan sonra `systemctl status tonishbot` ile gerçek
# kullanımına bakıp bu değerleri ölçüme göre sıkılaştırın.
MemoryMax=512M
MemoryHigh=384M

# Ek izolasyon: bot sadece kendi dizinine (SQLite dosyaları için) yazabilir,
# sistemin geri kalanı bu servis için salt okunur.
NoNewPrivileges=true
PrivateTmp=true
ProtectSystem=strict
ProtectHome=true
ReadWritePaths=/opt/tonishbot

[Install]
WantedBy=multi-user.target
```

3. Servis tanımını sisteme tanıtın:

```bash
sudo systemctl daemon-reload
```

```bash
sudo systemctl enable tonishbot
```

```bash
sudo systemctl start tonishbot
```

4. Durumunu kontrol edin ve **birkaç dakika** logları izleyin — sunucu RAM sınırının
   yakınında olduğu için (bkz. [Bölüm 10](#10-vmware-balloon-ram-sorunu-paylaşımlı-vdslerde))
   ilk dakikalarda sorun çıkarsa hemen görmek istiyoruz:

```bash
sudo systemctl status tonishbot
```

```bash
journalctl -u tonishbot -f
```

`[+] Eklenti Yüklendi` satırlarının 7 kez (7 cog) ve ardından `... olarak giriş yapıldı!`
mesajının görünmesi beklenir. `journalctl`'den çıkmak için `CTRL + C`.

## 7. Güncelleme Nasıl Yapılır?

Bilgisayarınızda kodları düzenleyip GitHub'a `push` attıktan sonra sunucuda şu komutları girmeniz yeterli:

```bash
sudo -u tonishbot git -C /opt/tonishbot pull
```

```bash
sudo -u tonishbot /opt/tonishbot/venv/bin/pip install -r /opt/tonishbot/requirements.txt
```

```bash
sudo systemctl restart tonishbot
```

(İkinci komut sadece `requirements.txt` değiştiyse gerekli, ama zararı yok — pip zaten
güncel olanları atlar.)

> [!TIP]
> Veritabanı şeması değişen bir güncellemede önce yedek alın:
> `sudo -u tonishbot cp /opt/tonishbot/economy.db /opt/tonishbot/economy.db.bak && sudo -u tonishbot cp /opt/tonishbot/steam.db /opt/tonishbot/steam.db.bak`

## 8. Sunucu Yönetim Komutları

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

## 9. Sorun Giderme (Troubleshooting)

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

## 10. VMware Balloon RAM Sorunu (Paylaşımlı VDS'lerde)

Bu VDS'te (2026-08-02) yaşanan ciddi bir kesintinin kök nedeni buydu — aynı belirtileri
görürseniz teşhis dakikalar sürer.

### Belirtiler

- Sunucu aniden aşırı yavaşlıyor veya tamamen erişilemez hale geliyor (SSH dahil ping'e **%100 kayıp**)
- Hosting sağlayıcının panelinde sunucu "AÇIK" görünüyor, CPU/RAM kullanımı **düşük** (örn. %1-4)
- Ama sunucunun **içinden** `free -h` çalıştırınca "used" çok yüksek çıkıyor (%80+)
- `ps aux --sort=-%mem` ve `smem -tk` toplamı, `free -h`'nin gösterdiği kullanılan RAM'e
  yakın bile değil — aradaki fark GB mertebesinde ve hiçbir process'e ait değil

### Sebep

VMware hypervisor'ı, fiziksel host RAM baskısı altındayken guest VM'lerden **balloon
driver** (`vmw_balloon`) ile zorla RAM geri alır. Bu geri alınan RAM, guest içinden
"kullanılan" RAM gibi görünür ama hiçbir process'e ait değildir — bu yüzden `ps`/`smem`
onu hiç göremez. Host paneli ise RAM'i zaten geri aldığı için düşük kullanım gösterir.
Kısacası: **sağlayıcının fiziksel host'u overcommit (kapasitesinden fazla) satıyor.**

### Teşhis

```bash
sudo vmware-toolbox-cmd stat balloon
```

Çıktı, kaç MB'ın host tarafından geri çekildiğini gösterir. Planınızın önemli bir yüzdesi
çıkıyorsa (örn. 4GB'lık bir planda 2GB+) teşhis kesinleşir.

### İzleme

Tekrarını yakalamak ve sağlayıcıya somut kanıt sunmak için:

```bash
(crontab -l 2>/dev/null; echo "*/5 * * * * echo \"\$(date '+%Y-%m-%d %H:%M:%S') \$(vmware-toolbox-cmd stat balloon)\" >> /var/log/balloon-watch.log") | crontab -
```

```bash
tail -50 /var/log/balloon-watch.log
```

### Çözüm

Bu, sunucu içinden düzeltilebilecek bir şey **değil** — sağlayıcının host'u nasıl
paylaştırdığıyla ilgili. Sağlayıcıya **kesintinin ne kadar sürdüğünü** ve
`vmware-toolbox-cmd stat balloon` çıktısını kanıt olarak bildirin; VM'in daha az yüklü
bir host'a taşınmasını veya overcommit oranının düşürülmesini isteyin. Bu tekrarladığı
sürece bu sunucuya yeni servis (TonishBot dahil) eklemek riski büyütür — bkz. dosyanın
başındaki uyarı.

## 11. GitHub Token Süresi Dolunca (Authentication Failed Hatası)

Eğer `git pull` yaparken "Authentication failed" veya "Password authentication was removed" hatası alıyorsanız, tokeninizin süresi dolmuştur.

1. **Eski tokeni iptal edin:** GitHub -> Settings -> Developer settings -> Personal access tokens -> ilgili tokenin yanından **Revoke**.
2. **Yeni Token Alın:** Aynı ekrandan yeni bir token oluşturun (`repo` yetkisi yeterli).
3. **Sunucuda URL'yi Güncelleyin:**

```bash
sudo -u tonishbot git -C /opt/tonishbot remote set-url origin https://KULLANICI_ADI:YENI_TOKEN@github.com/KULLANICI_ADI/tonishbot.git
```

4. **Test Edin:** `sudo -u tonishbot git -C /opt/tonishbot pull` yazarak hatasız çalıştığını doğrulayın.

> [!IMPORTANT]
> Yeni tokeni bu dosyaya **yazmayın**. Sadece sunucudaki komuta yapıştırın.
> Bu rehberde daha önce gerçek tokenler bulunuyordu; hepsi iptal edilmiştir.
