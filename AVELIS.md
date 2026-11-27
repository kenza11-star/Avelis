# Avelis Android checkpoint

Sumber memuat KriTap pada commit dalam UPSTREAM-REVISION beserta perubahan
label aplikasi dan jalur build. Lisensi dan pemberitahuan upstream tersedia
dalam COPYING, LICENSES, header sumber, dan folder aset terkait.
Engine Krita C++ dan Qt Widgets dipertahankan. Panel Android ada di
libs/ui/mobile, packaging ada di packaging/android/apk.

## Build baseline dan checkpoint

Siapkan lingkungan Linux yang setara dengan VM KDE krita-android-sdk36-2204.
Ikuti build-tools/ci-scripts/android.yml untuk SDK/NDK, Qt, paket dependensi
native, metadata, dan lingkungan Python KDE CI. Gunakan checkout dependensi
yang dipin dan catat SHA-nya. Checkpoint ini belum menetapkan pin dependensi
KDE karena jalur bootstrap tersebut belum berhasil diverifikasi.

Setel AVELIS_KDE_ENV ke skrip setup lingkungan KDE Android,
AVELIS_KDE_DEPS ke direktori krita-deps-management (dengan ci-utilities di
dalamnya), dan AVELIS_KDE_PYTHON ke Python di lingkungan CI tersebut.
Jalankan `bash build-tools/avelis-android.sh`. Script memakai target
arm64-v8a dan mode package debug. Untuk baseline, pakai checkout upstream
yang bersih dan perintah di build-tools/ci-scripts/android.yml. Workflow
manual ikut dikemas dan memerlukan runner Linux dengan label
avelis-kde-android serta konfigurasi di atas. Bootstrap pada runner GitHub
hosted dan build end-to-end belum diverifikasi.

## Data dan pembaruan

Simpan salinan KRA melalui pemilih dokumen ketika build tersedia, lalu
validasi salinan dengan membukanya kembali sebelum mengganti sumber.
Backup, recovery dan migrasi Avelis belum diuji. Untuk rilis, tetapkan
application ID produksi dan signing key milik pengguna, lalu pertahankan
keduanya bersama versionCode yang meningkat untuk memperbarui APK.

## Avelis V2

Gradle menetapkan application ID `org.avelis.paint` dengan sufiks
`.debug` dan `.next` sesuai varian upstream. Namespace Java/JNI tetap
`org.krita`. Manifest meminta manifest merger membuang INTERNET dan
ACCESS_NETWORK_STATE. BillingClient, layar donasi Android dan menu unduh
paket supporter dinonaktifkan pada jalur aplikasi. Paket aset Krita bawaan
dan impor lokal tetap tersedia lewat jalur upstream.

Checkout dependensi KDE yang diperiksa pada V2:
- https://invent.kde.org/packaging/krita-deps-management.git pada
  `3e9eb8a143c114aa33520421a67c8edfeef649ee`.
- https://invent.kde.org/packaging/krita-ci-utilities.git pada
  `b591f0ef834d061329707e8841b97ff6a0b3c48b`.

Letakkan checkout kedua di subdirektori `ci-utilities` pada checkout pertama.
Kedua commit tersebut adalah titik audit, belum terbukti berhasil membangun
APK bersama. Build masih bergantung pada paket prabangun KDE CI dan
lingkungan SDK/NDK, Qt Android serta Python yang sesuai. Tidak ada APK V2
dan alur mode pesawat belum diuji.

## Target distribusi Android

Avelis menargetkan HP Android dari berbagai merek dan kelas perangkat.
Baseline manifest adalah Android 7.0 (API 24). Ketiga ABI di bawah mengikuti
job upstream pada commit yang tercatat di UPSTREAM-REVISION.

| ABI build | Target |
|---|---|
| arm64-v8a | HP Android ARM 64-bit |
| armeabi-v7a | HP dengan OS Android ARM 32-bit yang menerima ABI ini |
| x86_64 | Android x86-64, termasuk emulator yang sesuai |

Jalankan `bash build-tools/avelis-android.sh <ABI>` pada toolchain yang sudah
disiapkan. Tanpa argumen, skrip memilih arm64-v8a. GitHub Actions menjalankan
satu job per ABI. APK dan checksum ditempatkan di `_packaging/<ABI>/`.
Gunakan `adb shell getprop ro.product.cpu.abilist` untuk membaca ABI OS.
Versi Android, ABI, ruang penyimpanan, RAM, dan driver GPU tetap menentukan
dukungan perangkat. Uji rilis perlu mencakup kelas RAM rendah, menengah,
tinggi, layar kecil/besar, serta perangkat atau emulator untuk setiap ABI.
iPhone memakai platform berbeda dan berada di luar target build Android.
