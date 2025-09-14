Telegram Komut ➝ Bot Trigger ➝ Gmail Kontrol ➝
➝ Excel Ayıklama ➝ Veri Dağıtımı ➝ 
➝ Grup Excel Oluşturma / Ekleme ➝ 
➝ SMTP ile Gönderim ➝
➝ Telegram Rapor ➝ Loglama (message-id)


🔄 Genel Akış
/kontrol komutu → mail’leri kontrol et
Gelen mailleri sıraya al
Message-ID’si logda olmayanları işlenmek üzere beklet

/işlem_yap komutu geldiğinde, işlenmemişleri sırayla işle:
Excel ayıkla
Gruplara göre dağıt
Excel dosyalarını oluştur
SMTP ile gönder

TEKNİK YAPI 
-----------------
aiogram 3.x + asyncio + sqlite + openpyxl + pandas yapısı
Render / Railway gibi cloud deploy ortamında çalışacak
Mail kontrol sırasında → .env + DB birleşiminden oluşan listeye bakılır. sadece bu maillerle işlem yapılır


project_root/
│── main.py                      # Bot giriş noktası (webhook/polling .env ile seçmeli)
│── config.py                    # Ortak config ayarları (dotenv ile)
│── .env                         # Gmail, SMTP, Telegram Token vs.
│── requirements.txt             # Gerekli bağımlılıklar
│── .gitignore
│
├── data/
│   ├── groups.json              # Grup bilgileri (grup_no, grup_ad=grup_name, il=şehir=city, mail adresleri)
│   ├── database.db              # SQLite veritabanı
│   ├── group_manager.py         #Grup Yönetim Scripti
│   ├── db_manager.py            #Veritabanı Yönetim Scripti
│   ├── setup.py                 #Kurulum Scripti
│   └── __init__.py
│
├── temp/                        # Geçici dosya (indirilen mailler, excel’ler)
│   └── (UUID_timestamp.xlsx)
│
├── handlers/                    # Telegram bot komutları
│   ├── __init__.py
│   ├── dar_handler.py           #/dar, /dar k, /dar z, /dar t
│   ├── email_handlers.py        # işlem komutları (/checkmail, /process, /process_ex, /retry_failed)
│   ├── commands.py              # Genel komutlar (/start, /help, /status, /rapor  )
│   └── admin_handlers.py        # Yönetici komutları (/gruplar, /grup_ekle, /grup_sil, /grup_reviz, /kaynak_ekle,/kaynak_sil, /log, /cleanup)
│
├── utils/                       # Yardımcı fonksiyonlar
│   ├── __init__.py
utils/temp_utils.py
│   ├── metrics.py               #  Performans izleme ve optimizasyon için, Tüm metric fonksiyonları tek yerde toplanır
│   ├── async_utils.py           # Async pattern'ler ve rate limiting için, Async Context Manager ile Resource Yönetimi
│   ├── handler_loader.py	 # otomotik handler yükleme belirtilen klasördeki tüm handler modüllerini async olarak keşfeder, import eder ve içindeki Router nesnelerini yoksa  register_handlers fonksiyonlarını bulup kaydeder. load_handlers_from_directory fonksiyonu, tüm modülleri tarar ve Dispatcher'a dahil eder
│   ├── gmail_client.py          # Gmail API / IMAP ile mail çekme
│   ├── smtp_client.py           # SMTP ile gönderim
│   ├── excel_utils.py           # Excel işleme (normalize, split, append, Excel’e şehir bazlı dağıtım)
│   ├── file_utils.py            # Temp dosya oluştur/sil
│   ├── normalize_utils.py       # Başlık, il(city) adı normalize etme
│   ├── db_utils.py              # Veri tutarlılığı ve kalıcı depolama için, SQLite CRUD işlemleri
│   ├── source_utils.py          # Dinamik kaynak yönetimi için, Takip edilecek (kaynak) mail listeleri 
│   └── report_utils.py          # Monitoring ve dashboard için, Rapor formatlama (tablo/json)
│
├── jobs/
│   ├── __init__.py
│   ├── cleanup.py               # Temp & eski log temizleme (cron/async job)
│   └── scheduler.py             # Zamanlayıcı görevler
│
└── logs/
    ├── bot.log                  # Genel loglar
    └── process.log              # İşlem logları (Message-ID vs.)


Akışta Hangi Dosya Ne Yapacak?
main.py → Botu başlatır, dispatcher & router yükler, webhook/polling ayarı.
config.py → .env dosyasını okur (SMTP, Gmail, TELEGRAM_TOKEN, ADMIN_IDS vs.)
data/database.db → SQLite kayıtları:
tablo: mails (message_id, status, created_at, updated_at)
tablo: logs (işlem detayları)

utils/gmail_client.py → Gmail API/IMAP ile gelen mail + attachment indir.
utils/excel_utils.py → openpyxl/pandas ile Excel normalize, grup bazlı dağıtma.
utils/db_utils.py → SQLite kayıt ekle/güncelle/sil (Message-ID duplicate check burada yapılır).
utils/smtp_client.py → Dosyaları SMTP ile gönder, retry mekanizması.
jobs/cleanup.py →
+10 gün sonra success mailleri sil
+15 gün sonra log temizle
temp klasöründe orphan dosya varsa sil

handlers/
email_handlers.py
commands.py 
admin_handlers.py 
KOMUT AÇIKLAMA YAPISI

📌 email_handlers.py (Mail ve İşlem Komutları)
Asıl iş akışı → mail kontrolü, excel işleme, gönderim.
→ İşin kalbi (mail → excel → dağıtım → gönderim)
# email_handlers.py
/checkmail       → Gmail’i kontrol et, kaynakta tanımlı maillerden gelenleri kuyruğa ekle (mailin Message-ID’sini al, pending)
/process         → Pending mailleri işle (SQLite’ten pending kayıtları sırayla işler → Excel ayıkla → grup bazlı böl → SMTP gönder → status=success/failed.İşlem başarılı ise → status = success güncelle. Hatalı ise → status = failed (retry için).)
/process_ex      → Sadece Excel işle, SMTP gönderimi yapma
/retry_failed    → Daha önce failed olanları yeniden dene



📌📌 commands.py (Genel Kullanıcı Komutları)
Genel bot fonksiyonları → herkesin görebileceği, sistemle ilgili şeyler.
→ Kullanıcı dostu, durum/rapor komutları
# commands.py
/start           → Botu tanıtır, yardım menüsü gösterir
/help            → Komut listesini ve açıklamalarını gösterir
/status          → Sistemin genel durumu (kaç mail beklemede, kaç işlenmiş, hata var mı)
/rapor           → Son X işlemin özet raporu (mail sayısı, excel sayısı, gönderilen dosyalar)


📌📌📌 admin_handlers.py (Yönetici Komutları)
Sadece ADMIN_IDS erişebilir. Sistem ayarları + grup yönetimi.
→ Yönetici kontrolü (grup ve sistem ayarları)
# admin_handlers.py
/gruplar         → Kayıtlı grupları listeler
/grup_ekle       → Yeni grup ekler (ör: /grup_ekle GrupAdı mail@ornek.com)
/grup_sil        → Grup siler
/grup_revize     → Grup city=il, mail adresini değiştirir
/kaynak_ekle     → kaynak(takip edilen) mail ekler
/kaynak_sil      → kaynak(takip edilen) maili siler
/log             → Hata loglarını getirir
/cleanup         → Manuel temizlik başlatır (İşlem bitmiş temp klasörlerini sil + son 20 success kaydı dışındakileri sil + Failed ve pending kayıtlar silinmez)
/debug_system    → Sistem CPU, memory, disk kullanımı
/debug_db        → Sistem Veritabanı istatistikleri
/debug_queue     → Sistem İşlem kuyruğu durumu
# Detaylı Log Görüntüleme:
/debug_logs      → Log Son log kayıtları (filtreli)
/debug_errors    → Log Son hataları göster
/debug_mail <message_id>  → Log Belirli mailin işlem detayı
#Konfigürasyon Görüntüleme:
/debug_config    → Mevcut config ayarlarını göster (şifreler hariç)
/debug_groups    → Grup yapılandırmasını detaylı göster
/debug_sources   → Kaynak mail listesini göster
#Test Komutları:
/debug_test_smtp    # SMTP bağlantı testi
/debug_test_gmail   # Gmail bağlantı testi
/debug_test_excel   # Excel işleme testi




dar_handler.py (BUNA AİT TAM KOD YAPISI MEVCUT)
/dar → Klasör yapısını metin olarak gösterir.
/dar k → Komut listesini gösterir (dosyadan veya cache'den).
/dar z → Projeyi zip olarak paketler ve gönderir.
/dar t → Tüm kaynak kodu tek bir txt dosyası halinde gönderir.
/dar f → Komut önbelleğini temizler.

Örnek groups.json yapısı
[
  {
    "grup_no": "GRUP_1",
    "grup_name": "ANTALYA",
    "grup_city": ["Afyon","Aksaray","Ankara","Antalya","Burdur","Çankırı","Isparta","Karaman","Kayseri","Kırıkkale","Kırşehir","Konya","Uşak"],
    "grup_mail": "GRUP_1@gmail.com"
  },
  
  
  

🎯 Avantajlar

Modülerlik → Mail çekme, Excel işleme, DB yönetimi, SMTP ayrı dosyalarda.
Async uyumlu → Aiogram + asyncio + aiohttp tabanlı, CPU boşa harcanmaz.
Düşük kaynak kullanımı → SQLite + temp klasörü disk bazlı çalışır, RAM şişmez.
Kolay bakım → utils/ içinde her iş parçacığı ayrı.
Güvenlik → .env ile yönetim, temp dışarıya açık değil.








🔒 Güvenlik
.env dosyası ile hassas bilgileri (mail, smtp, telegram token) yönetmek iyi.
.env dosyasında SMTP ve Gmail şifrelerini kesinlikle tut (kod içine gömme).
Temp klasörünü dışarıya açık bırakma.
Şifreleme: SQLite veritabanını şifreleyin (SQLCipher veya benzeri)
Input Validation: Tüm kullanıcı girdilerini validate edin
Rate Limiting: Komut başına rate limiting ekleyin
Backup Mekanizması: groups.json ve veritabanı için otomatik yedekleme



.====DİKKAT===
Mail indirme, dosya kaydetme, SMTP gönderim → hepsi asyncio ile çalışırsa CPU beklemede boşa harcanmaz.
Telegram rapor ve log kanalı ayrı tutulursa, bilgi sızıntısı riski azalır.
SQLite loglama + grup yönetimi komutları + temp cleanup olacak

/ Temp Klasörü Kullanımı
İşlem sırasında dosyaları temp/ klasörüne indirip orada aç, işledikten sonra çıktı dosyasını yine temp klasöründe tut.
Bellekte tutmak yerine diskten aç/kapa yaparak RAM kullanımını azalt.
Temp dosyalarına UUID + timestamp ekle → çakışma riskini sıfırlar.
İşlem bitince otomatik temizleme olsun

Performans ve Ölçeklenebilirlik İyileştirmeleri
Veritabanı İndeksleri: SQLite tablolarında sık sorgulanan alanlar için indeksler oluşturun
# db_utils.py'de tablo oluştururken
CREATE INDEX idx_mails_status ON mails(status);
CREATE INDEX idx_mails_message_id ON mails(message_id);
CREATE INDEX idx_logs_timestamp ON logs(timestamp);

Bellek Yönetimi: Büyük Excel dosyaları için generator pattern kullanın
 excel_utils.py'de
def read_excel_chunks(file_path, chunk_size=1000):
    return pd.read_excel(file_path, chunksize=chunk_size)

Async Dosya İşlemleri: aiofiles kütüphanesi ile dosya okuma/yazma işlemlerini async yapın


Monitoring ve Loglama
Prometheus Metrikleri: Performans metrikleri ekleyin
# metrics.py
from prometheus_client import Counter, Histogram
MAILS_PROCESSED = Counter('mails_processed_total', 'Total processed mails')
PROCESSING_TIME = Histogram('mail_processing_seconds', 'Time spent processing mail')
Detaylı Hata Loglama: Hata durumlarında stack trace ve context bilgisi loglayın


Health Check Endpoint: Bot durumunu kontrol edecek basit bir HTTP endpoint


🔄 Retry Mekanizması Geliştirmeleri
Exponential Backoff: SMTP hataları için exponential backoff ile retry

Circuit Breaker Pattern: Sürekli hata veren servisleri geçici devre dışı bırakın

🗃️ Veri Yönetimi
Veri Arşivleme: Eski kayıtları arşivleme özelliği ekleyin

Veri Temizleme Schedule: Otomatik temizlik için cron job

Bulk Operations: Toplu işlemler için batch processing

👥 Kullanıcı Deneyimi
Interactive Menüs: inline keyboard ile etkileşimli menüler

Progress Reporting: Uzun süren işlemler için ilerleme durumu

Template Messages: Mesaj şablonları için Jinja2 benzeri template engine

🧩 Modülerlik Geliştirmeleri
Plugin Sistemi: Yeni özellikler için plugin architecture

Configuration Management: Ayarları dinamik olarak yönetebilme

Dependency Injection: Bağımlılıkları merkezi yönetin

🌐 Deployment İyileştirmeleri
Dockerfile: Containerization için Dockerfile

Health Checks: Container health check configuration

Resource Limits: CPU/Memory limitleri belirleyin

📈 Ölçeklenebilirlik
Redis Entegrasyonu: Dağıtık lock ve cache için Redis

Horizontal Scaling: Birden fazla worker instance çalıştırma desteği

Message Queue: Celery/RQ ile task kuyruğu

🔍 Debug ve Geliştirme Araçları
Debug Komutları: /debug komutu ile sistem durumunu detaylı inceleme

Test Verisi Üretme: Demo için test verisi oluşturma komutları

Dry-run Modu: Gerçek işlem yapmadan test etme özelliği

Örnek Kod: Async Context Manager ile Resource Yönetimi
python
# utils/async_utils.py
import aiofiles
from contextlib import asynccontextmanager

@asynccontextmanager
async async_open_file(path, mode='r'):
    async with aiofiles.open(path, mode) as f:
        yield f

# Kullanımı
async with async_open_file('data.txt', 'w') as f:
    await f.write('content')














.==TEMEL VERİLER - ÖZET===
1 - GRUP BİLGİSİ
grup bilgisi data kasörün ve config de olacak
grup bilgisi komutla ekle/sil/güncelleme yapılacak



.==TEMEL VERİLER - KOMUT===
/gr → Grupları listeler (commands.py)


.===YAPILACAK İŞLEMLER - ÖZET===

1 - MAİL KONTROL
asenkron veya iş kuyruklu yapı (örn. Celery, asyncio)
komut ile bot Gmail’i kontrol eder.
kontrol sadece tanımlı kaynak mail adreslerini kontrol eder
kaynak mail adresleri configdedir,
.env ile düzenlenebilir
excel içeren mail var/ yok (mail 1 den fazla olabilir. her mailde birden fazla excel dosyası olabilir)
Gelen mailleri sıraya al
Message-ID’si logda olmayanları işlenmek üzere beklet
(1 mail geldi daha sonra 3 mail geldi ise işlem için 1+3 = mail var)



2 - EXCEL İŞLEMLERİ (/temp içerisinde yapılacak)
Excel dosyasını alır/ indirir
Excel Validasyonu:
* Excel sütun başlıkları beklenen düzende olmaya bilir (il, İL, CİTY, city) kontrol edilmeli.
*Başlık Normalize: Başlıklar için küçük-büyük harf + trim + Türkçe karakter düzeltme fonksiyonu yaz. (örn: normalize_header("İl ") → "IL")
* Aynı il adı birden fazla şekilde yazılmışsa (İstanbul, istanbul, İSTANBUL) normalize edilmeli.
* Excel dosyalarına tarih ve saat koymak iyi; grup_name_MMDD_HHMM.xlsx formatı
* Başlık satırları tekrarlanmamalı.
* pandas + openpyxl kombinasyonu ideal
* Pandas ile sadece gerekli sütunları işle
* pandas.read_excel() gibi fonksiyonlar genelde dosyayı komple belleğe yükler, bu RAM’i artırabilir.
* openpyxl ile workbook’u açıp satır satır okuyabilir, gereksiz verileri belleğe almadan işlenebilir
* Birleştirme: Aynı grup için Excel eklemelerinde → openpyxl ile append satır satır daha verimli.
* Yeni dosya oluştururken bellekte tüm veriyi tutup sonradan kaydetmek yerine, openpyxl ile satır satır yaz
* Çok fazla veri varsa, chunk’lama (bölerek işleme)
* Chunklama: pandas.read_excel(..., chunksize=10000) bellek dostu olur.


ilk excel dosyası ile işleme başlar
gereken her grup için grup_name_monthDay_hourMinute.xlsx dosyası oluştur
gruplara göre veriyi il = city kriterine göre gruplara dağıtır, 
dağıtım sırası şekli
B: sutunu il = city, diğer bilgiler sırasıyla c,d,e.. sutunlarına aktar
dagıtılmayan il=city varsa bunları yok_monthDay_hourMinute.xlsx aktar

varsa maildeki sonraki excel dosyasına geç,
önceden oluşturulan  grup_name_monthDay_hourMinute.xlsx  dosyasında B sutununa göre dolu son satırdan sonra
yeni veri varsa  il = city kriterine göre ekle

gerekiyorsa eksik grup için grup_name_monthDay_hourMinute.xlsx dosyası oluştur
veriyi il = city kriterine göre gruplara dağıt
dagıtılmayan il=city varsa bunları yok_monthDay_hourMinute.xlsx B sutununa göre dolu son satırdan sonra ekle

maille gelen tüm excel dosyalarını bu şekilde tara,
aynı grup için olanları tek dosya olacak şekilde eklemeler yap
(örnek 3 mail geldi. 3 mailde grup_1 için veri varsa 3 defa dosya açma. 3 mail bilgisini tek grup_1 excel dosyasında olacak şekilde birleştir)
işlem bittikten sonra oluşturulan excel dosyalarını kaydet

*-*
işlem yapılanlar için Message-ID (RFC 5322 standardında tanımlanmıştır) bilgisini kaydet
aynı mail ile tekrarlı işlem yapılmasını önle


3 - MAİL GÖNDERİM İŞLEMLERİ
kaydedilen excel dosyalarını ilgili grup e-posta adreslerine gönderir
Tanımlı alıcıya SMTP üzerinden gönderir.
* SMTP başarısız olursa yeniden deneme (retry) mekanizması olmalı.
* Hangi dosyanın kime gönderildiği bilgisi loglanmalı.
* SMTP retry için tenacity kütüphanesi hafif ve uygun.
* Gönderilen dosyaların loguna → file_path, recipient, status ekle.


4 - BAŞARILI İŞLEM KAYDI Message-ID kaydet
Excel dosyası başarıyla alındı
Veriler gruplara dağıtıldı
Excel çıktı dosyaları oluşturuldu
E-posta gönderimi başarıyla yapıldı (veya opsiyonel olarak en azından dosyalar kaydedildi)
Yani: Tüm işlem zinciri başarıyla tamamlandığında, 
en son adımda Message-ID kaydedilir

5 - RAPORLAma İŞLEM sonucu raporu oluşturur
gönderim sonunda rapor oluşturup telegra bota gönderecek
Telegram üzerinden log ve sonuç mesajlarını gösterir
/rapor komutu ile son X işlem özetini getirebilirsin.
Rapor içeriği JSON + tabular olabilir.

Telegram Raporu İçeriği:

Kaç mail tarandı
Kaç Excel bulundu
Kaç il gruba dağıtıldı
Kaç satır veri işlendi
Hatalı il'ler
Hangi gruplara hangi dosya gönderildi
Log Kanalı:
Telegram’da ayrı bir "log kanalı" belirlenirse daha sessiz/log odaklı bir bildirim yapılabilir.


6 - /TEMP temizleme
işlem başarıyla tamamlandığında hemen temp dosyalarını sil, başarısızsa dosyaları tut (debug/retry için).


.===YAPILACAK İŞLEMLER - KOMUT===

/checkmail → Manuel olarak mail kontrolü yapar (email_handlers.py)
/process ex → Sadece Excel işleme yapar (mail gönderimi yapmaz)
/process   → Excel işlemleri yap + Mail gönder + rapor gönder
/


.=== EK ÖZELLİK VE İŞLEMLER =====
1 - Message-ID
* başarılı her işlem için Message-ID kaydı alınacak
* SQLite ile kayıt ve takip
* kayıt birikmesini önlemek çakışmayı önlemek için periyodik silme işlemi yapıacak
✅ Message-ID kalıcı kayıt ile işlem Tekrarı engellenecek
| İşlem            | Zamanlama                            |
| ---------------- | ------------------------------------ |
| Message-ID kayıt | İşlem anında                         |
| Mail silme       | +10 gün                              |
| Message-ID silme | +11 gün (veya +15 gün bile olabilir) |





En düşük sistem kaynağı tüketen çözüm arıyorsan, kriterlerin muhtemelen şöyle:

🧠 Düşük bellek (RAM) kullanımı
🖥️ Minimum CPU etkisi
🪶 Basit yapı, ek servis kurulumuna gerek yok
🔒 Veri güvenliği (özellikle tekrar işlem engelleme için)
🛠️ Ek sunucu/servis gerekmez

Bu kriterlerle birlikte en ideal seçenekleri aşağıda sıralıyorum:

✅ 1. SQLite (Tavsiye Edilen - Hafif ve Kalıcı)
Neden düşük kaynak tüketir?
🗃️ Dosya tabanlı, tek bir .db dosyası
🛠️ Ek sunucu/servis gerekmez
⚙️ Python’un yerleşik sqlite3 modülü ile çalışır
🌱 Küçük veri setlerinde neredeyse sıfır sistem etkisi vardır
