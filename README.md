# Kit Studi Moderasi Konten (JSC Special Issue)

> Isi folder ini memuat ujaran kebencian dari HateXplain. Gunakan hanya untuk riset.

## Isi
| File | Fungsi |
|---|---|
| `build_items.py` | Membangun item MR (E1, E2, R1–R3, I1–I3) beserta oracle-nya dari HateXplain |
| `baseline.py` | Melatih dua klasifier pembanding lokal (word-LR, char-LR) |
| `evaluate.py` | Evaluator dua sumbu: EV1/EV2/EV3, hidden failure, profil, statistik |
| `analysis_residual.py` | Analisis sisa token setelah erasure dan uji berpasangan I1 vs I2 |
| `run_llm.py` | Menjalankan model LLM (Ollama/API), membuat parafrase I3, serta lembar validasi manusia |
| `hitl_sheet.py` | Membuat/membaca workbook validasi manusia (HITL) berlangkah |
| `revise_eval.py` | Evaluator revisi: verdict dan sitasi dinilai terpisah, sumbu kebijakan dipisah, uji I1 vs I2, rekonsiliasi item |
| `run_all.sh` | Menjalankan seluruh tahap LLM secara berurutan dan dapat dilanjutkan |
| `figs.py` | Gambar untuk naskah |
| `items_test_full.jsonl` | 13.617 item (1.888 postingan test) untuk baseline |
| `items_llm600.jsonl` | 4.331 item (600 postingan, 200 per kelas) untuk LLM |
| `results/` | Hasil baseline yang dipakai di naskah (angka nyata) |

Data sumber: `git clone https://github.com/hate-alert/HateXplain` (lisensi MIT). Salin `Data/dataset.json` dan `Data/post_id_divisions.json` ke folder `data/`.

## Mereproduksi hasil baseline (sekitar 15 detik)
```
python build_items.py --data data/dataset.json --splits data/post_id_divisions.json --split test --out items_test_full.jsonl
python baseline.py --data data/dataset.json --splits data/post_id_divisions.json --items items_test_full.jsonl --out-prefix runs/full
python evaluate.py --items items_test_full.jsonl --runs runs/full_word-LR.jsonl runs/full_char-LR.jsonl --out results/baseline_full.json
python analysis_residual.py --items items_test_full.jsonl --runs runs/full_word-LR.jsonl runs/full_char-LR.jsonl --out results/residual_full.json
```

## Menjalankan LLM (dikerjakan di komputer Anda dengan Ollama)
```
ollama pull qwen2.5:7b ; ollama pull llama3.1:8b ; ollama pull gemma2:9b     # contoh pilihan model
# 1) isi item parafrase I3 (pakai model dari keluarga berbeda dengan model yang diuji, plus judge)
python run_llm.py paraphrase --items items_llm600.jsonl --model llama3.1:8b --judge-model gemma2:9b
# 2) jalankan setiap model dengan dua prompt
for m in qwen2.5:7b llama3.1:8b gemma2:9b; do
  for p in direct evidence; do
    python run_llm.py run --items items_llm600.jsonl --model $m --prompt $p --out runs/${m//:/_}_$p.jsonl
  done
done
# 3) evaluasi (sertakan baseline sebagai pembanding)
python evaluate.py --items items_llm600.jsonl --runs runs/*_direct.jsonl runs/*_evidence.jsonl --out results/llm600.json
python evaluate.py --items items_llm600.jsonl --runs runs/*_direct.jsonl runs/*_evidence.jsonl --lenient --out results/llm600_lenient.json
python analysis_residual.py --items items_llm600.jsonl --runs runs/*_direct.jsonl runs/*_evidence.jsonl --out results/residual_llm600.json
```
Satu run berisi sekitar 4.300 panggilan. Dengan model 7–9B di laptop, waktunya kira-kira beberapa jam per run. Run bisa dilanjutkan bila terputus (resumable). Setelah selesai, kirim folder `results/` dan `runs/`, lalu saya isi bagian berwarna merah di naskah.

## Validasi manusia / HITL (R002, wajib sebelum submit)
```
python run_llm.py export --items items_llm600.jsonl --out human_validation.xlsx   # setelah paraphrase selesai
python run_llm.py score --sheet human_validation_filled.xlsx --out validation.json
```
Sampel: 20% acak dari E1, E2, I1, I3 (seed 42), ditambah **semua kasus R2 ambigu** (postingan *offensive* yang dilabeli *hatespeech* oleh minimal satu anotator, 59 item) dan sampel kontrol 20% dari R2 *offensive* lainnya. Daftar kelompok R2 ada di `human_validation_r2_groups.json`.

`human_validation.xlsx` (dibuat oleh `hitl_sheet.py`) hanya berisi dropdown Ya/Tidak; tidak ada isian bebas dan sel lain dikunci (tanpa kata sandi).

| Lembar | Diisi oleh | Isi |
|---|---|---|
| `Petunjuk` | dibaca semua | Empat langkah, arti Ya/Tidak per jenis item, legenda warna |
| `Penilai 1` | Penilai 1 | Satu dropdown per baris; kata yang dihapus/ditukar merah, pengganti/sisipan biru |
| `Penilai 2` | Penilai 2 (tanpa melihat Penilai 1) | Sama dengan Penilai 1 |
| `Keputusan` | Pemutus | Dropdown hanya untuk baris oranye (dua penilai berbeda) |
| `Rekap` | otomatis | Sepakat, Cohen's kappa, validitas per jenis item |

Ya = oracle/transformasi valid, Tidak = tidak valid (item final Tidak masuk `invalid_items`). `score` hanya membaca dropdown dan menolak nilai selain Ya/Tidak. Format lama (kolom rater1/rater2) tetap diterima.

## Menjalankan semua tahap LLM sekaligus (R001)
`run_all.sh` menjalankan parafrase (dua fase: parafrase lalu judge) → lembar HITL → baseline 600 postingan → 6 run LLM → `evaluate.py`, `analysis_residual.py`, dan `revise_eval.py`. Dapat dilanjutkan bila terputus (jalankan ulang perintah yang sama):
```
nohup caffeinate -is ./run_all.sh > logs/run_all.log 2>&1 &
tail -f logs/run_all.log
```
Keluaran yang dikirim: folder `results/` dan `runs/`.

## Audit refusal-aware dan validitas oracle (results/audited/)
Hasil kanonis untuk naskah. Hanya membaca `runs/`, item, dan lembar validasi; tidak memanggil model.
```
~/.venvs/modkit/bin/python -m unittest discover -s tests -v   # uji classifier respons
~/.venvs/modkit/bin/python audit_metrics.py                   # menulis results/audited/*
```
- `response_classifier.py`: enam kategori respons (VALID_VERDICT, ABSTENTION, REFUSAL, UNPARSEABLE, GENERATION_ERROR, EMPTY_RESPONSE) dari teks mentah.
- `audit_metrics.py`: coverage, akurasi bersyarat, tingkat refusal/abstensi, transisi E1/E2/R2/R3, uji I1 vs I2 dengan Holm, analisis I3, validitas oracle bertingkat, dan sensitivitas.
- Laporan: `results/audited/audit_report.md`; konfigurasi dan log perubahan: `results/audited/reproducibility_notes.md`.
- Lingkungan Python ada di `~/.venvs/modkit` (di luar folder iCloud). `.venv/` lama di folder ini sudah dihapus karena sebagian file-nya dipindahkan macOS ke iCloud; buat ulang lingkungan dengan perintah di `results/audited/reproducibility_notes.md` §1.
