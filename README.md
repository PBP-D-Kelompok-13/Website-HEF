# 🍉 HEF (Healthy Eco Foody)

## 📌 Application Overview
HEF (Healthy Eco Foody) adalah platform website yang membantu pengguna menerapkan gaya hidup Sustainable Food & Diet dengan menganalisis kandungan nutrisi dari produk makanan serta resep harian. Dengan mengintegrasikan Open Food Facts API dan Spoonacular API, platform ini menyediakan fitur pemindaian barcode untuk mengecek Eco/Nutri-Score, perbandingan produk secara berdampingan, analisis keberlanjutan resep, serta manajemen inventaris bahan makanan rumah tangga lengkap dengan pengingat tanggal kadaluarsa untuk mencegah food waste. 

## 📌 Important Links
### - [Link Figma](https://www.figma.com/design/5cLDNeCMSgbMMEc6GVnsEz/HEF-Website?node-id=403-244&t=96ZWLJc0fwdndt1T-1)
### - [Link PWS](https://muhammad-raihananta-websitehef.pws.cs.ui.ac.id/#welcome)

## 📋 Daftar Anggota Kelompok dan Pembagian Modul
| Nama | NPM | Modul |
| :---: | :---: | :---: |
| Angelica Christilia Talumewo | 2506536313 | Perbandingan 2-3 Produk melalui Eco/Nutrition Score
| Celine Nafisa Setiawan | 2506590201 | Inventaris Bahan Makanan di Rumah beserta Pengingat Tanggal Kadaluarsa
| Ferdinandus Pakasi | 2506602643 | Recipe Sustainability Analyzer
| Muhammad Raihananta Adzaky Yuwono | 2506547853 | Sistem Login dan Otentikasi Akun Pengguna
| Yazid Khairul Firmansyah | 2506537064 | Pencarian Produk dan Eco/Nutrition Score melalui Scan Barcode

## 👤 Peran Pengguna
### 🧑‍🤝‍🧑 Jenis User:
1. Pembelanja peduli lingkungan
2. Pelaku diet sehat dan berkelanjutan
3. Edukator dan content creator lingkungan

### 📖 User Persona & Story: 
Persona 1: Sarah — Ibu Rumah Tangga Peduli Lingkungan
- Sebagai Sarah, saya ingin scan/cari barcode produk di supermarket, supaya saya bisa langsung tahu eco-score-nya sebelum beli.
- Sebagai Sarah, saya ingin membandingkan 2-3 produk sejenis, supaya saya bisa pilih yang paling ramah lingkungan untuk keluarga saya.
- Sebagai Sarah, saya ingin melihat histori pencarian saya, supaya saya nggak perlu cari ulang produk yang sama tiap belanja.

Persona 2: Raihananta — Mahasiswa Vegetarian Baru
- Sebagai Nanta, saya ingin memasukkan bahan yang saya punya, supaya sistem bisa kasih tahu nutrisi dan apakah resep saya cukup plant-based.
- Sebagai Nanta, saya ingin mendapat rekomendasi resep otomatis berdasarkan diet vegetarian, supaya saya nggak perlu cari-cari resep sendiri di internet.
- Sebagai Nanta, saya ingin filter resep berdasarkan kalori, supaya sesuai dengan kebutuhan diet saya sehari-hari.

Persona 3: Rina — Content Creator Sustainability
- Sebagai Rina, saya ingin menyimpan produk favorit ke daftar saya, supaya saya bisa kumpulkan referensi produk sustainable buat konten.
- Sebagai Rina, saya ingin melihat detail lengkap eco-score dan alasan di baliknya, supaya saya bisa jelaskan ke followers dengan akurat.
- Sebagai Rina, saya ingin akun login, supaya data favorit dan histori saya tersimpan permanen dan bisa diakses kapan saja.


## 📈 Public API yang digunakan
- Open Food Facts API : https://world.openfoodfacts.org/data 
- Spoonacular API : https://spoonacular.com/food-api 

## ⚙️ Setup  Instructions
You can follow these steps to run the application locally on your machine. 

### 1. Clone the repository: 
```bash
   git clone https://github.com/PBP-D-Kelompok-13/Website-HEF.git
   cd your-repo-name
```

### 2. Setup & Activate Virtual Environment  
**Windows:** 
```bash
python -m venv env
env\Scripts\activate
```

**Unix (macOS, Linux):**
```bash
python3 -m venv env
source env/bin/Activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Configure Environment Variables
Create a `.env` file in the root directory and configure local settings:
```
PRODUCTION=False
```

### 5. Run Migrations & Start Server
```bash
python manage.py migrate
python manage.py runserver
```
Open http://localhost:8000 in your browser.

## 📦 Tech Stack & Core Dependencies
- Django: Core web framework handling routing, logic, and page generation.
- Gunicorn: WSGI HTTP server for production environment handling.
- WhiteNoise: Static file (CSS/JS) management for production.
- psycopg2-binary: Database driver for PostgreSQL integration.
- python-dotenv: Reads secrets securely from .env.
- requests & urllib3: Facilitates external API communication.
