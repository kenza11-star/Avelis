# Matriks fitur Avelis

Audit statis. Semua pengujian APK dan workflow pengguna di bawah berstatus NOT RUN.

| ID | Fitur | Status pada checkpoint |
|---|---|---|
| P01 | No ads or monetization SDKs, no subscriptions, no credit counter; offline access to installed tools | Diubah pada source V2 — BillingClient, startup donasi dan menu unduh supporter dilepas. Mode pesawat dan manifest gabungan belum diuji. |
| P02 | Watermark-free image, animation and drawing-process exports, optional user-defined signature only | Belum diuji — plugins/impex dan pipeline animasi upstream. |
| P03 | Unlimited custom brush-pattern imports subject only to safe file and device limits | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P04 | Unlimited vector editing time | Mesin tersedia — libs/flake serta plugins/impex/svg. |
| P05 | Advanced vector operations | Parsial upstream — libs/flake. Operasi UI belum diinventarisasi. |
| P06 | Advanced shapes | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P07 | Special pen equivalents | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P08 | Tone curves | Kandidat upstream — plugins/filters/colorsfilters. |
| P09 | Gradient map | Filter upstream — plugins/filters/gradientmap. |
| P10 | Levels | Filter upstream — plugins/filters/levelfilter. |
| P11 | Color replacement | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P12 | Procedural clouds/noise effect | Kandidat parsial — plugins/filters/noisefilter. Awan dan seed belum dikonfirmasi. |
| P13 | Watercolor effect | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P14 | High-quality relief/emboss effect | Filter upstream — plugins/filters/embossfilter. Kualitas dan kontrol belum diuji. |
| P15 | Non-destructive adjustment/filter layers and masks with editable settings; avoid destructive fallback unless explicitly chosen by user | Mesin tersedia — libs/image/kis_filter_mask.cpp. |
| P16 | Gallery manual ordering with durable metadata and sorting | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P17 | Nested artwork folders, move/rename/search; avoid breaking project paths | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P18 | Recycle bin with restore, explicit permanent delete, optional retention and disk warning | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P19 | Ranking/featured artwork equivalent | Alternatif lokal direncanakan — favorit dan portofolio belum dibuat. |
| P20 | Customize workspace background independently of artwork pixels; light/dark/system and neutral/custom colors | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P21 | Optional artwork anti-training/AI-disturbance export | Di luar lingkup V2 — semua fitur AI dikecualikan. |
| P22 | Animation creation with no artificial resolution caps; enforce memory/storage feasibility with clear estimates, onion skin, frame/timeline editing, playback, frame duplication and export | Mesin tersedia — libs/image/kis_image_animation_interface.cpp. |
| P23 | Audio for animations | Belum diuji — jalur audio/mux Android belum diverifikasi. |
| P24 | 3D drawing references | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P25 | Materials | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P26 | Fonts | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P27 | Canvas paper textures | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P28 | Surrounding fill/eraser | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P29 | Multiple custom color palettes | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P30 | CMYK export | Kandidat upstream — plugins/impex/tiff. Hasil kanal dan ICC belum diperiksa. |
| P31 | Custom keyboard shortcuts | Belum diimplementasikan atau diverifikasi pada Avelis. |
| P32 | Local storage alternative to paid 20 GB cloud | Alternatif lokal direncanakan — backup versi dan restore belum dibuat. |
| P33 | AI-assisted super-resolution (not necessarily premium-exclusive) | Di luar lingkup V2 — semua fitur AI dikecualikan. |

## Core dan tambahan

- Kanvas, undo/redo, eraser, warna, layer, preset dan file actions memiliki titik integrasi Qt Widgets dalam libs/ui/mobile. Alur pengguna Android belum diuji.
- Raster, seleksi, transformasi, mask dan swap memakai mesin upstream. Audit per alat, gesture, stylus, stabilisasi, orientasi dan aksesibilitas masih tertunda.
- Galeri lokal, onboarding, mode satu tangan, pengaturan bahasa, timelapse, reference board, template, dan backup/recovery Avelis belum diverifikasi atau dikembangkan.
- Plugin KRA, PNG, JPEG, WebP, PSD dan SVG ada di plugins/impex. Putar balik format dan integritas layer/ICC Android belum dites.
- Tidak ada aset baru. Inventaris aset individual belum selesai. Lisensi upstream ada di COPYING, LICENSES dan file aset/sumber terkait.

## Lingkup V2

| ID | Kelompok fitur | Bukti sumber atau gap |
|---|---|---|
| F01 | Proyek, galeri dan workspace | Recent documents ada pada welcome page upstream. Galeri, trash dan backup baru belum tersedia. |
| F02 | Brush engine dan brush studio | Presets dan panel mobile diwarisi. Audit brush studio dan impor belum dijalankan. |
| F03 | Layer dan komposit | Panel layer di libs/ui/mobile. Workflow mask, clipping dan blend belum dites. |
| F04 | Warna, seleksi dan fill | Engine dan color sheet tersedia upstream. Cakupan impor palet, fill dan gesture belum diuji. |
| F05 | Vektor, shape, ruler dan transform | libs/flake dan plugins/impex/svg. Paritas shape dan vektor mobile belum diuji. |
| F06 | Filter lokal dan adjustment | plugins/filters memuat filter upstream. Filter tambahan dan paritas belum selesai. |
| F07 | Teks, manga dan print | Engine teks upstream tersedia. Comic panel, proyek multipage dan CMYK belum diuji. |
| F08 | Animasi, timelapse dan audio | Mesin animasi diwarisi. Timelapse dan mux Android belum diverifikasi. |
| F09 | Material lokal, font, paper dan 3D | Tiga paket aset Android upstream terinventarisasi. Target koleksi tambahan dan viewer 3D belum dibuat. |
| F10 | File, export, aksesibilitas dan kenyamanan | Format upstream dan Android bridge diwarisi. Pengujian ekspor, recovery, aksesibilitas dan performa belum dijalankan. |
