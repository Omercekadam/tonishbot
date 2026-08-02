# TonishBot

Nishdot (İstanbul Nişantaşı Üniversitesi Dijital Oyun Tasarımı Kulübü) Discord sunucusunun botu.
Kayıt sistemi, sanal ekonomi/oyunlar, Steam entegrasyonu, ticket sistemi ve Gemini destekli
sohbet asistanı içerir.

## Kurulum

```bash
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt
```

`.env.example` dosyasını `.env` olarak kopyalayıp kendi değerlerinizi girin:

```bash
cp .env.example .env && chmod 600 .env
```

Sonra çalıştırın:

```bash
python bot.py
```

Sunucuya (VDS) kurulum ve systemd servisi için: [DEPLOYMENT.md](DEPLOYMENT.md)

> [!WARNING]
> `.env` dosyasını **asla** commit etmeyin. Token, API anahtarı gibi sırları
> hiçbir kod veya doküman dosyasına yazmayın.

## Yapılandırma

Tüm ayarlar `.env` üzerinden okunur — tam liste için `.env.example`'a bakın.
`GEMINI_API_KEY` veya `STEAM_API_KEY` boş bırakılırsa ilgili komutlar kendini
devre dışı bırakır, bot yine de çalışır.

Rol seçim menüsündeki roller `cogs/registration.py` içindeki `ROLE_OPTIONS`
sözlüğünde tanımlıdır (ID, etiket, emoji ve açıklama birlikte durur).

## Komutlar

Prefix: `!`

### Genel
| Komut | Açıklama |
|---|---|
| `!yardim` | Komut listesi (`!help`, `!komutlar`, `!yardım`) |
| `!bilgi` | Kulüp hakkında bilgi |
| `!link` | Sosyal medya ve üyelik linkleri |
| `!yk` | Yönetim kurulu listesi |
| `!oyunfikri` | Rastgele oyun fikri üretir (tür + tema + kısıtlama) |

### Ekonomi ve oyunlar
| Komut | Açıklama |
|---|---|
| `!bakiye [@kişi]` | Bakiye gösterir (`!tonishcoin`, `!cuzdan`) |
| `!gunluk` | 24 saatte bir 50 coin |
| `!liderlik` | En zengin 5 kişinin görsel tablosu (`!top`, `!zenginler`) |
| `!blackjack <bahis>` | Blackjack (`!bj`) |
| `!slot <bahis>` | Slot makinesi |
| `!zindan` | Zindan savaşı, giriş 50 coin (`!dungeon`, `!rpg`) |
| `!sistemkirici` | Şifre kırma oyunu, giriş 100 coin (`!hacker`) |
| `!tahmin <5 hane>` | Sistem Kırıcı tahmini |
| `!vazgec` | Sistem Kırıcı görevinden çıkar |
| `!bilmece` | Emoji bilmecesi (5 dk bekleme) |

Bahisli oyunlarda **bahis oyun başında düşülür**; aynı anda tek oyun açabilirsiniz.

### Steam
| Komut | Açıklama |
|---|---|
| `!steam_bagla <ID/link>` | Steam hesabını bağlar |
| `!oyunsuresi` | Son 2 haftanın oyun süreleri sıralaması |
| `!ortak @kişi` | Ortak oyunlardan rastgele öneri |
| `!kimoyunda` | Şu an kim ne oynuyor |
| `!kart [@kişi]` | Görsel Gamer Kart (`!kimlik`) |
| `!analiz [@kişi]` | Gamer DNA tür grafiği |
| `!sunucu-istatistik` | Sunucunun kolektif Steam istatistikleri |

Steam profilinizde **Oyun Detayları** ve **Envanter** herkese açık olmalıdır.

### Yapay zeka
| Komut | Açıklama |
|---|---|
| `@Tonish <mesaj>` | Botu etiketleyerek sohbet |
| `!sor <soru>` | Doğrudan soru |
| `!benzeroner <oyun>` | Benzer oyun önerisi (`!oner`, `!tavsiye`) |
| `!sohbetisifirla` | Sohbet geçmişini siler |

### Yönetim
| Komut | Yetki | Açıklama |
|---|---|---|
| `!duyuru <mesaj>` | Admin | Duyuru kanalına embed duyuru |
| `!etkinliksayaci "gg.aa.yyyy" "SS:DD" "Başlık" Açıklama` | Admin | Geri sayımlı etkinlik duyurusu |
| `!kayital` / `!rolmenusu` / `!rolbilgi` | Admin | Kayıt butonu ve rol menüsü |
| `!ticketkur` | Admin | Ticket oluşturma panelini kurar |
| `!bakiyeguncelle @kişi <miktar>` | Admin | Bakiye ekler/çıkarır |
| `!cekban` / `!cekkick` / `!cektimeout` / `!cekrolver` / `!cekrolal` / `!temizle` | Bot sahibi | Moderasyon |

`!duyuru` ve `!etkinliksayaci` sadece `ADMIN_COMMAND_CHANNEL_ID` kanalında çalışır.

## Mimari

```
bot.py            Giriş noktası — cog yükleme, global hata yakalayıcı, logging
cogs/
  ai.py           Gemini sohbeti, oyun önerisi
  economy.py      Bakiye, blackjack, slot, zindan, sistem kırıcı, bilmece, liderlik
  general.py      Bilgi komutları, duyuru, etkinlik sayacı, oyun fikri
  moderation.py   Bot sahibine özel moderasyon komutları
  registration.py Kayıt formu, hoş geldin görseli, rol seçim menüsü
  steam.py        Steam profil bağlama ve analiz komutları
  tickets.py      Destek talebi (ticket) sistemi
```

Veritabanları (`economy.db`, `steam.db`) çalışma dizininde SQLite olarak oluşturulur ve
`.gitignore` ile dışlanmıştır. Şema ilk açılışta otomatik kurulur.

Coin harcayan her işlem `Economy.try_spend()` üzerinden **tek atomik SQL** ile yapılır;
bu, eşzamanlı komutlarda çift harcamayı ve eksi bakiyeyi engeller.

## Müzik hakkında

Müzik cog'u kaldırıldı. Mimari (Lavalink v4 + wavelink) hâlâ geçerli yaklaşım;
sorun Lavalink sunucusundaki eskimiş YouTube eklentisiydi. Geri getirmek isterseniz:

1. `git log --all -- cogs/music.py` ile eski kodu bulun
2. Lavalink v4 sunucusu kurun, `application.yml`'a
   `dev.lavalink.youtube:youtube-plugin:1.13.0` ekleyin ve dahili kaynağı kapatın
   (`lavalink.server.sources.youtube: false`)
3. `wavelink>=3.5` bağımlılığını geri ekleyin
