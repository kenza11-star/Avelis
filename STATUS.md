# Avelis V2

- Checkout V1 dipertahankan. V2 menambah package ID Gradle, penghapusan
  SDK billing, jalur UI donasi dan unduhan supporter, serta permintaan
  penghapusan permission jaringan di manifest Android.
- Pemeriksaan statis dan integritas bundle aset sukses. Build APK, signature,
  pengujian perangkat, konfigurasi mode pesawat dan audit fitur penuh tertunda.
- Pembungkus build berhenti pada preflight toolchain. Checkout resep KDE
  terbaca, tetapi binary SDK/NDK dan Qt Android yang sesuai belum tersedia.
- Engine C++/Qt tetap dipakai. Rust belum ditambahkan karena baseline Android
  belum terukur dan belum ada komponen yang terbukti membutuhkan migrasi.

## Cakupan perangkat

Target mencakup perangkat Android lintas merek. Workflow menyiapkan
arm64-v8a, armeabi-v7a, dan x86_64. Build, instalasi, kompatibilitas GPU,
memori dan pengujian perangkat per ABI masih tertunda.
