## 📌 AI Documentation
File ini dibuat sebagai bahan penilaian terkait Documentation & AI Disclosure dimana setiap anggota akan mencantumkan terkait penggunaan AI beserta strategi & masalah yang dihadapi.

### 👤 Angelica Christilia Talumewo
- Modul: Perbandingan 2–3 Produk melalui Eco-Score dan Nutri-Score.
- Menggunakan ChatGPT untuk membantu memahami Git, menyusun tes, [Link Chat] (https://chatgpt.com/share/6ae3dfa4-a1d8-83ec-9f0b-e5acdcef342e)
  implementasi Django dan HTMX, menyesuaikan tampilan Compare,
  serta melakukan debugging berdasarkan kode dan hasil terminal.
- Bantuan implementasi meliputi pemilihan produk dari data Discover,
  validasi 2–3 produk berbeda, Clear selection, serta CRUD
  perbandingan tersimpan dengan pemeriksaan login dan kepemilikan.
- Kode disesuaikan dengan model Product, autentikasi, template,
  dan komponen desain yang sudah digunakan kelompok.
- Strategi pengembangan menggunakan commit tes sebelum implementasi
  pada subfitur yang dikerjakan dengan TDD. Sebagian tes keamanan
  Delete dan edge cases ditambahkan setelah implementasi sebagai
  tes regresi; tidak seluruh tes ditulis sebelum implementasi.
- Masalah yang ditangani meliputi URL yang belum tersedia, integrasi
  pilihan produk dengan Discover, ekspektasi redirect pada tes,
  mock yang mengganggu registry model Django, dan tag template
  resep yang terpotong saat integrasi main.
- Laporan coverage lokal yang telah diukur menunjukkan 100%
  statement dan branch coverage pada main/comparison_forms.py,
  main/comparison_selection.py, dan main/comparison_views.py:
  total 284 statement dan 84 cabang.
  Angka tersebut bukan coverage seluruh website dan tidak mencakup
  pengujian interaksi JavaScript di browser.

### 👤 Celine Nafisa Setiawan
- Modul: Inventaris Bahan Makanan (Pantry)
- Menggunakan Gemini untuk membantu memahami apa yang harus dilakukan saat terjadi error/hal yang tak terduga terjadi saat ingin pull dari main ke branch lain agar repo tidak hancur/berantakan seperti command git apa yang perlu di run etc.
- Menggunakan Figma AI dalam membuat beberapa komponen seperti dropdown box pada wireframing mobile dan light mode dark mode switch pada navbar.
- Menggunakan bantuan Gemini saat meng-export styling dari wireframe Figma ke file CSS (inventory.css) dan juga untuk merapihkan lagi styling css later on.
- Menggunakan Gemini untuk membantu dalam perbaikan styling css saat modal card add dan edit ingredients tidak dapat/fail terus dalam menerapkan dark mode padahal page inventory.html sudah bisa switch dari light to dark (Karena saya capek scrolling mencari class yang benar)
[LINK CHAT](https://share.gemini.google/NAN1sbOSWkDb)

### 👤 Ferdinandus Pakasi
Chat link: https://chatgpt.com/s/cx_6ae49ba189b881919b915888a4280b8d 
- Memanfaatkan Codex dan Figma AI untuk membantu merancang dan mengimplementasikan Recipe Analyzer di Website HEF. Pengerjaannya mencakup penyesuaian desain Figma, integrasi Spoonacular, form analisis resep, saved dan created recipes, serta halaman detail. Strateginya, saya mendiskusikan terlebih dahulu requirements setiap webpage yang ingin dicapai dan keterbatasan APInya apa saja, dari situ baru menerapkan sejumlah penyesuaian desain maupun requirements yang lebih realistis untuk dicapai.
- Memanfaatkan Codex untuk implementasi backend dan frontend Django, termasuk CRUD resep, validasi input dan foto, template, CSS, Bootstrap, serta interaksi HTMX, semuanya dengan pendekatan TDD. Selain itu, Codex juga digunakan untuk meninjau penggunaan data Spoonacular. Dalam prosesnya, saya memastikan informasi mana yang benar-benar disediakan API. 
- Kendala yang dijumpai yakni berkaitan dengan konfigurasi API key dan migrasi yang sempat terkendala, serta beberapa edge cases yang menyebabkan bug. Strategi yang diterapkan yakni harus melakukan pengujian secara mandiri dan bertahap untuk memastikan fungsionalitas setiap webpage.

### 👤 Muhammad Raihananta Adzaky Yuwono
- Utilize Figma AI untuk membantu saat membuat wireframing e.g. mengatur autolayout, merapihkan framing, membantu convert dari wireframing desktop to mobile, membuat vector-vector simple untuk buttons. Masalah yang dihadapi adalah mengatur scope untuk agentnya atau frame yang bisa di edit e.g. restrict AInya mengubah main component/design system yang sudah disepakati dari awal.
- Utilize Gemini untuk membantu convert wireframing ke HTML dan CSS menggunakan Bootstrap, mostly banyak copy paste disini. [Link Chat](https://drive.google.com/file/d/1syAy3yiVgIRtsVKnvOlGvCGC0z5D0ri0/view?usp=sharing)
- Utilize Claude and Codex untuk implement authentication. Jujur disini banyak banget yang dislop, terutama awalnya ingin menggunakan modals dan HTMX untuk login/register (implemented by Claude) tapi setelah further review saya merasa bahwa saya tidak akan bisa menjelaskan/replicate frontend dan backend yang cukup complicated, sehingga saya utilize Codex untuk bantu refactoring agar menggunakan dedicated pages saja untuk login/registering. Also used Codex to regenerate tests untuk menyesuaikan setelah refactoring selesai. [Link Chat untuk Claude](https://claude.ai/share/c478ba9c-77d2-4256-88c8-326fab3fd25f) [Link Chat untuk Codex](https://chatgpt.com/s/cx_6addc92976388191b932b275905f28af)
- Utilize Claude and Codex untuk implement user profile page, editing via HTMX, dynamic updating of navbar, dan toast messages + dark mode. Jujur Bu Dosen/Kak Asdos disini udah pure vibes... Main strategy adalah untuk make sure TDDnya di setup dulu, baru work on implementasinya yang bikin tests nya green. Masalah yang dihadapi mostly terkait switching context between every chat semisal chatnya udah cukup besar agar tokennya tidak cepet abis. [Link Chat Claude 2](https://claude.ai/share/f66a57e9-7010-40b3-8ec2-7fb302b24242) [Link Chat Claude 3](https://claude.ai/share/097e3d93-02b2-4100-85e9-90d1db3303b4) [Link Chat Codex 2](https://chatgpt.com/s/cx_6ae027bb86248191b4697848cd6f69f1) 

### 👤 Yazid Khairul Firmansyah
- Modul: Discover Products, Barcode Scanner (Open Food Facts API v2), Product Detail, & Bookmark.
-Utilize Gemini untuk implementasi service integrasi Open Food Facts API v2 (`main/services/open_food_facts.py`) dan menyusun unit test menggunakan `unittest.mock.patch` agar pengujian tidak bergantung pada koneksi internet. Masalah yang dihadapi adalah banyak produk di database Open Food Facts yang mengembalikan `ecoscore_grade` atau `nutriscore_grade` bernilai `"unknown"` atau `"not-applicable"`, pemetaan tag ke 5 kategori aplikasi, serta ekstraksi data jejak karbon `agribalyse`, sehingga perlu dinormalisasi terlebih dahulu sebelum disimpan dengan `update_or_create`.
- Utilize Gemini untuk mendesain model `Product`, custom `ProductQuerySet`, dan `Bookmark`, serta memisahkan shared layout (`header.html` dan `footer.html` dengan atribusi wajib Open Food Facts ODbL) dari `base.html`. Strategi utama pengembangan menggunakan pendekatan TDD (menyusun tes terlebih dahulu sebelum implementasi). Masalah yang dihadapi pada QuerySet adalah memastikan pengurutan `sort="eco"` tetap menempatkan produk dengan `eco_grade` kosong (`""`) di urutan paling bawah setelah grade `a`–`e` menggunakan `Case/When` di Django ORM.
- Utilize Gemini untuk implementasi halaman Discover (`discover.html`), live filtering & search menggunakan HTMX (`hx-get`, `hx-target="#discover-results"`, `hx-push-url`), load-more pagination (`discover_more.html`), serta fitur kamera Barcode Scanner (`discover_scanner.js` menggunakan `BarcodeDetector` dengan fallback `Html5Qrcode`). Masalah yang dihadapi adalah menjaga state query parameter saat pengguna melakukan filter kategori/Eco-Score/Nutri-Score sambil menekan tombol *Load More*, mengatasi race condition request HTMX saat mengetik cepat dengan `hx-sync="closest form:abort"`, serta mengatur layout card produk agar responsif 2 kolom di layar mobile (`col-6 col-lg-4`).
- Utilize Gemini untuk implementasi halaman Product Detail (`product_detail.html`) dengan auth-gating (guest hanya dapat melihat ringkasan skor, sedangkan rincian nutrisi per 100g dan breakdown persentase siklus hidup CO2 hanya ditampilkan untuk pengguna yang sudah login), fitur toggle Bookmark dengan HTMX Out-of-Band (`hx-swap-oob`) toast notification, CRUD produk manual (`ProductForm`) dengan validasi kepemilikan (`403 Forbidden`), serta JSON API endpoints (`/api/products/`). Juga menggunakan Gemini untuk membantu debugging dan menyelesaikan merge conflict pada `models.py`, `views.py`, `urls.py`, serta pembuatan merge migration Django (`makemigrations --merge`) saat mengintegrasikan branch Discover dengan fitur anggota lain di `main`. [Link Chat Gemini](https://share.gemini.google/GssZ9lyqMWew) 

