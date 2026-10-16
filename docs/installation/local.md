# Lokální instalace (Python)

Tento návod popisuje spuštění aplikace přímo na hostitelském systému ve virtuálním prostředí Pythonu.

---

## 📋 Požadavky na systém

- **Operační systém:** Linux (Ubuntu 20.04+, Debian 11+, Fedora, Arch), macOS nebo Windows 11 (WSL2 doporučeno).
- **Python:** Verze 3.10 nebo novější.
- **Písma TrueType (doporučeno):** Balíček `fonts-dejavu-core` pro perfektní sazbu české diakritiky v exportovaných PDF souborech.

Na systému Ubuntu/Debian nainstalujte závislosti:
```bash
sudo apt update
sudo apt install -y python3 python3-venv python3-pip fonts-dejavu-core
```

---

## 🛠 Postup instalace

### 1. Klonování repozitáře
```bash
git clone https://github.com/TheLittleRock/Praktika.git
cd Praktika
```

### 2. Vytvoření virtuálního prostředí
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Instalace Python knihoven
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Nastavení proměnných prostředí (volitelné)
Můžete vytvořit soubor `.env` v kořenovém adresáři:
```env
PRAKTIKA_DATA_DIR=data
PRAKTIKA_SECRET_KEY=zvolte-tajny-nahodny-klic
GEMINI_API_KEY=vas-gemini-api-klic
```

### 5. Spuštění serveru
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

Aplikace bude spuštěna na adrese `http://127.0.0.1:8000`. Databáze SQLite a potřebné adresáře se inicializují automaticky při prvním startu.
