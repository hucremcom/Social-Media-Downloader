# YouTube Downloader Derleme Script'i
# Konsol penceresini genişlet
try {
    $host.UI.RawUI.WindowSize = New-Object System.Management.Automation.Host.Size(120, 40)
    $host.UI.RawUI.BufferSize = New-Object System.Management.Automation.Host.Size(120, 1000)
} catch {
    Write-Host "Konsol boyutu ayarlanamadı, atlanıyor..." -ForegroundColor Yellow
}

Write-Host "YouTube Downloader derleniyor..." -ForegroundColor Cyan
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
import base64, os
from PIL import Image, ImageDraw
# Turkce karakter uyumlu islem
icon = Image.new('RGBA', (256, 256), (0, 0, 0, 0))
draw = ImageDraw.Draw(icon)
# YouTube kirmizi arkaplan
draw.ellipse((10, 10, 246, 246), fill='#FF0000')
# Play ikonu
draw.polygon([(90, 70), (190, 128), (90, 186)], fill='white')
icon.save('youtube_icon.ico')
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
if (Test-Path "youtube_icon.ico") {
    Write-Host "Simge basariyla olusturuldu." -ForegroundColor Green
    $iconParam = "--icon=youtube_icon.ico"
} else {
    Write-Host "Simge olusturulamadi, simgesiz devam ediliyor..." -ForegroundColor Yellow
}

# Ana Python kodunu güncelle - başlığı değiştir
Write-Host "Youtube indirici başlığı güncelleniyor..." -ForegroundColor Yellow
$pythonDosyasi = "youtube_downloader.py"
$icerik = Get-Content -Path $pythonDosyasi -Encoding UTF8
$icerik = $icerik -replace 'self\.root\.title\("YouTube İndirici"\)', 'self.root.title("YouTube Downloader")'
Set-Content -Path $pythonDosyasi -Value $icerik -Encoding UTF8

# Dil dosyalarını kontrol et
Write-Host "Dil dosyalari kontrol ediliyor..." -ForegroundColor Yellow
if (-not (Test-Path "lang")) {
    New-Item -ItemType Directory -Path "lang" -Force | Out-Null
    Write-Host "lang klasoru olusturuldu." -ForegroundColor Green
}

# Dil dosyalarını dahil etmek için parametreler hazırla
$langDataParam = "--add-data 'appdata\bin\yt-dlp.exe;appdata\bin' --add-data 'youtube_icon.ico;.'"

# Eğer lang klasörü varsa ve içinde dosyalar varsa dahil et
if (Test-Path "lang" -PathType Container) {
    if ((Get-ChildItem -Path "lang" -Filter "*.txt").Count -gt 0) {
        $langDataParam += " --add-data 'lang;lang'"
        Write-Host "Dil dosyalari pakete dahil edilecek: lang/*.txt" -ForegroundColor Green
    }
}

# Uygulama derleme
Write-Host "Uygulama derleniyor..." -ForegroundColor Cyan
$derleKomutu = "pyinstaller --clean --noconfirm --onefile --windowed $iconParam $langDataParam youtube_downloader.py --name 'YouTube_Downloader'"
Write-Host "Çalıştırılan komut: $derleKomutu" -ForegroundColor DarkGray
Invoke-Expression $derleKomutu

if ($LASTEXITCODE -ne 0) {
    Write-Host "Derleme sirasinda hata olustu!" -ForegroundColor Red
} else {
    Write-Host "Derleme basariyla tamamlandi!" -ForegroundColor Green
    Write-Host "Calistirilabilir dosya: dist\YouTube_Downloader.exe" -ForegroundColor Cyan
    
    # Derleme sonrası, exe'nin yanına ikon dosyasını da kopyala
    if (Test-Path "youtube_icon.ico") {
        Copy-Item -Path "youtube_icon.ico" -Destination "dist\youtube_icon.ico" -Force
        Write-Host "İkon dosyası exe ile aynı dizine kopyalandı." -ForegroundColor Green
    }

    # Dil klasörünü dist klasörüne kopyala
    if (Test-Path "lang" -PathType Container) {
        Copy-Item -Path "lang" -Destination "dist\lang" -Recurse -Force
        Write-Host "Lang klasörü exe ile aynı dizine kopyalandı." -ForegroundColor Green
    }
}

# Temizlik
Write-Host "Gecici dosyalar temizleniyor..." -ForegroundColor Yellow
if (Test-Path "create_icon.py") { Remove-Item "create_icon.py" -Force }
if (Test-Path "youtube_icon.png") { Remove-Item "youtube_icon.png" -Force }
if (Test-Path "__pycache__") { Remove-Item "__pycache__" -Recurse -Force }
if (Test-Path "build") { Remove-Item "build" -Recurse -Force }
Get-ChildItem -Filter "*.spec" | ForEach-Object { Remove-Item $_.FullName -Force }

Write-Host ""
Write-Host "Islem tamamlandi." -ForegroundColor Green
Read-Host "Çıkmak için Enter tuşuna basın" 