# Social Media Downloader Derleme Script'i
# Konsol penceresini genişlet
try {
    $host.UI.RawUI.WindowSize = New-Object System.Management.Automation.Host.Size(120, 40)
    $host.UI.RawUI.BufferSize = New-Object System.Management.Automation.Host.Size(120, 1000)
} catch {
    Write-Host "Konsol boyutu ayarlanamadı, atlanıyor..." -ForegroundColor Yellow
}

Write-Host "Social Media Downloader derleniyor..." -ForegroundColor Cyan
Write-Host ""

# Python kontrolü
try {
    $pythonVersion = python --version
    Write-Host "Python bulundu: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "Python bulunamadi! Lutfen Python kurun." -ForegroundColor Red
    Write-Host "https://www.python.org/downloads/" -ForegroundColor Cyan
    Read-Host "Devam etmek için Enter tuşuna basın"
    exit 1
}

# Gerekli paketleri kontrol et
Write-Host "Gerekli paketler kontrol ediliyor..." -ForegroundColor Yellow
try {
    python -c "import tkinter" 
} catch {
    Write-Host "tkinter yuklenemiyor. Lutfen Python kurulumunuzu kontrol edin." -ForegroundColor Red
    Read-Host "Devam etmek için Enter tuşuna basın"
    exit 1
}

# PyInstaller kontrolü
try {
    python -c "import PyInstaller"
    Write-Host "PyInstaller bulundu." -ForegroundColor Green
} catch {
    Write-Host "PyInstaller yukleniyor..." -ForegroundColor Yellow
    pip install pyinstaller
    if ($LASTEXITCODE -ne 0) {
        Write-Host "PyInstaller yuklenemedi!" -ForegroundColor Red
        Read-Host "Devam etmek için Enter tuşuna basın"
        exit 1
    }
}

# Klasör yapısını kontrol et
Write-Host "Klasor yapisi olusturuluyor..." -ForegroundColor Yellow
if (-not (Test-Path "appdata\bin")) {
    New-Item -ItemType Directory -Path "appdata\bin" -Force | Out-Null
}

# yt-dlp güncellik kontrolü
Write-Host "yt-dlp guncelligi kontrol ediliyor..." -ForegroundColor Yellow
$ytdlpPath = "appdata\bin\yt-dlp.exe"
$ytdlpUrl = "https://github.com/yt-dlp/yt-dlp/releases/latest/download/yt-dlp.exe"

if (Test-Path $ytdlpPath) {
    Write-Host "Mevcut yt-dlp surumu bulundu, guncellik kontrol ediliyor..." -ForegroundColor Yellow
    
    $localFileDate = (Get-Item $ytdlpPath).LastWriteTime
    
    # Geçici dosya indir
    Write-Host "Son surum indiriliyor..." -ForegroundColor Yellow
    $tempFile = "appdata\bin\yt-dlp_temp.exe"
    Invoke-WebRequest -Uri $ytdlpUrl -OutFile $tempFile
    
    $remoteFileDate = (Get-Item $tempFile).LastWriteTime
    
    # Eğer yeni sürüm varsa güncelle
    if ($remoteFileDate -gt $localFileDate) {
        Write-Host "Yeni surum bulundu, guncelleniyor..." -ForegroundColor Green
        Move-Item -Path $tempFile -Destination $ytdlpPath -Force
    } else {
        Write-Host "yt-dlp guncel, yeniden indirmeye gerek yok." -ForegroundColor Green
        Remove-Item -Path $tempFile -Force
    }
} else {
    Write-Host "yt-dlp indiriliyor..." -ForegroundColor Yellow
    Invoke-WebRequest -Uri $ytdlpUrl -OutFile $ytdlpPath
    Write-Host "yt-dlp indirildi." -ForegroundColor Green
}

# Simge oluştur
Write-Host "Uygulama simgesi olusturuluyor..." -ForegroundColor Yellow
$iconPyContent = @"
from PIL import Image, ImageDraw

def lerp(a, b, t):
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))

w = h = 256
icon = Image.new('RGBA', (w, h), (0, 0, 0, 0))

# Mavi -> mor dikey gradyan arka plan
grad = Image.new('RGBA', (w, h))
g = ImageDraw.Draw(grad)
top = (37, 99, 235)
bot = (124, 58, 237)
for y in range(h):
    g.line([(0, y), (w, y)], fill=lerp(top, bot, y / h) + (255,))

mask = Image.new('L', (w, h), 0)
m = ImageDraw.Draw(mask)
m.rounded_rectangle([8, 8, w - 8, h - 8], radius=60, fill=255)
icon.paste(grad, (0, 0), mask)

# Beyaz indirme oku (genel indirme ikonu)
d = ImageDraw.Draw(icon)
cx = 128
d.rectangle([cx - 24, 44, cx + 24, 148], fill='white')
d.polygon([(70, 136), (186, 136), (128, 214)], fill='white')
d.rounded_rectangle([42, 172, 214, 208], radius=18, fill='white')

icon.save('social_icon.ico', sizes=[(16, 16), (32, 32), (48, 48), (64, 64), (128, 128), (256, 256)])
"@

Set-Content -Path "create_icon.py" -Value $iconPyContent

# PIL kütüphanesini kontrol et
try {
    python -c "import PIL" 
} catch {
    Write-Host "PIL (Pillow) yukleniyor..." -ForegroundColor Yellow
    pip install pillow
}

python create_icon.py

$iconParam = ""
if (Test-Path "social_icon.ico") {
    Write-Host "Simge basariyla olusturuldu." -ForegroundColor Green
    $iconParam = "--icon=social_icon.ico"
} else {
    Write-Host "Simge olusturulamadi, simgesiz devam ediliyor..." -ForegroundColor Yellow
}

# Ana Python kodunu güncelle - başlığı değiştir
Write-Host "Uygulama başlığı güncelleniyor..." -ForegroundColor Yellow
$pythonDosyasi = "social_media_downloader.py"
$icerik = Get-Content -Path $pythonDosyasi -Encoding UTF8
$icerik = $icerik -replace 'self\.root\.title\("YouTube[^"]*"\)', 'self.root.title("Social Media Downloader")'
Set-Content -Path $pythonDosyasi -Value $icerik -Encoding UTF8

# Dil dosyalarını kontrol et
Write-Host "Dil dosyalari kontrol ediliyor..." -ForegroundColor Yellow
if (-not (Test-Path "lang")) {
    New-Item -ItemType Directory -Path "lang" -Force | Out-Null
    Write-Host "lang klasoru olusturuldu." -ForegroundColor Green
}

# Dil dosyalarını dahil etmek için parametreler hazırla
$langDataParam = "--add-data 'appdata\bin\yt-dlp.exe;appdata\bin' --add-data 'social_icon.ico;.'"

# Eğer lang klasörü varsa ve içinde dosyalar varsa dahil et
if (Test-Path "lang" -PathType Container) {
    if ((Get-ChildItem -Path "lang" -Filter "*.txt").Count -gt 0) {
        $langDataParam += " --add-data 'lang;lang'"
        Write-Host "Dil dosyalari pakete dahil edilecek: lang/*.txt" -ForegroundColor Green
    }
}

# Uygulama derleme
Write-Host "Uygulama derleniyor..." -ForegroundColor Cyan
$derleKomutu = "python -m PyInstaller --clean --noconfirm --onefile --windowed $iconParam $langDataParam social_media_downloader.py --name 'Social_Media_Downloader'"
Write-Host "Çalıştırılan komut: $derleKomutu" -ForegroundColor DarkGray
Invoke-Expression $derleKomutu

if ($LASTEXITCODE -ne 0) {
    Write-Host "Derleme sirasinda hata olustu!" -ForegroundColor Red
} else {
    Write-Host "Derleme basariyla tamamlandi!" -ForegroundColor Green
    Write-Host "Calistirilabilir dosya: dist\Social_Media_Downloader.exe" -ForegroundColor Cyan
    
    # Derleme sonrası, exe'nin yanına ikon dosyasını da kopyala
    if (Test-Path "social_icon.ico") {
        Copy-Item -Path "social_icon.ico" -Destination "dist\social_icon.ico" -Force
        Write-Host "İkon dosyası exe ile aynı dizine kopyalandı." -ForegroundColor Green
    }

    # Dil klasörünü dist klasörüne kopyala (mevcut eski dosyaları da temizle)
    if (Test-Path "lang" -PathType Container) {
        if (Test-Path "dist\lang") { Remove-Item "dist\lang" -Recurse -Force }
        Copy-Item -Path "lang" -Destination "dist\lang" -Recurse -Force
        Write-Host "Lang klasörü exe ile aynı dizine kopyalandı." -ForegroundColor Green
    }
}

# Temizlik
Write-Host "Gecici dosyalar temizleniyor..." -ForegroundColor Yellow
if (Test-Path "create_icon.py") { Remove-Item "create_icon.py" -Force }
if (Test-Path "social_icon.png") { Remove-Item "social_icon.png" -Force }
if (Test-Path "dist\youtube_icon.ico") { Remove-Item "dist\youtube_icon.ico" -Force }
if (Test-Path "__pycache__") { Remove-Item "__pycache__" -Recurse -Force }
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
Get-ChildItem -Filter "*.spec" | ForEach-Object { Remove-Item $_.FullName -Force }

Write-Host ""
Write-Host "Islem tamamlandi." -ForegroundColor Green
Read-Host "Çıkmak için Enter tuşuna basın" 