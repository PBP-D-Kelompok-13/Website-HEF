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

### 👤 Ferdinandus Pakasi

### 👤 Muhammad Raihananta Adzaky Yuwono
- Utilize Figma AI untuk membantu saat membuat wireframing e.g. mengatur autolayout, merapihkan framing, membantu convert dari wireframing desktop to mobile, membuat vector-vector simple untuk buttons. Masalah yang dihadapi adalah mengatur scope untuk agentnya atau frame yang bisa di edit e.g. restrict AInya mengubah main component/design system yang sudah disepakati dari awal.
- Utilize Gemini untuk membantu convert wireframing ke HTML dan CSS menggunakan Bootstrap, mostly banyak copy paste disini. [Link Chat](https://drive.google.com/file/d/1syAy3yiVgIRtsVKnvOlGvCGC0z5D0ri0/view?usp=sharing)
- Utilize Claude and Codex untuk implement authentication. Jujur disini banyak banget yang dislop, terutama awalnya ingin menggunakan modals dan HTMX untuk login/register (implemented by Claude) tapi setelah further review saya merasa bahwa saya tidak akan bisa menjelaskan/replicate frontend dan backend yang cukup complicated, sehingga saya utilize Codex untuk bantu refactoring agar menggunakan dedicated pages saja untuk login/registering. Also used Codex to regenerate tests untuk menyesuaikan setelah refactoring selesai. [Link Chat untuk Claude](https://claude.ai/share/c478ba9c-77d2-4256-88c8-326fab3fd25f) [Link Chat untuk Codex](https://chatgpt.com/s/cx_6addc92976388191b932b275905f28af)
- Utlizie Claude and Codex untuk implement user profile page, editing via HTMX, dynamic updating of navbar, dan toast messages + dark mode. Jujur Bu Dosen/Kak Asdos disini udah pure vibes... Main strategy adalah untuk make sure TDDnya di setup dulu, baru work on implementasinya yang bikin testsnya green. Masalah yang dihadapi mostly terkait switching context betwen every chat semisal chatnya udah cukup besar agar tokennya tidak cepet abis. [Link Chat Claude 2](https://claude.ai/share/f66a57e9-7010-40b3-8ec2-7fb302b24242) [Link Chat Claude 3](https://claude.ai/share/097e3d93-02b2-4100-85e9-90d1db3303b4) [Link Chat Codex 2](https://chatgpt.com/s/cx_6ae027bb86248191b4697848cd6f69f1) 

### 👤 Yazid Khairul Firmansyah