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

## Revisi v10 — pekerjaan yang butuh data baru (11 Nov 2026)

Semua skrip di bawah tidak mengubah `runs/`, `results/` utama, atau lembar validasi ronde 1.

| Pekerjaan | Siapa | Perintah | Hasil |
|---|---|---|---|
| Validasi manusia ronde 2 (E1 sisa 318, I1 sisa 107, R2 sisa 513; ada jawaban **Ragu**) | 2 penilai + 1 pemutus | lembar sudah dibuat: `human_validation_round2.xlsx` (ulang: `python run_llm.py export2 --items items_llm600.jsonl`) → simpan terisi sebagai `human_validation_round2_filled.xlsx` → `python audit_metrics.py` | `results/audited/oracle_validity_analysis.csv` (sensus E1, I1, R2 semua strata) |
| Penilaian manusia teks counterfactual (HE-E1CF) | 2 penilai + pemutus | bahan siap di `results/human_eval_e1cf/materials/`; prosedur di `human_evaluation_protocol.md` | `results/human_eval_e1cf/` |
| Run ulang (stabilitas antar-run) | laptop + Ollama | `./run_repeats.sh cf` lalu `./run_repeats.sh main` → `python analysis_repeats.py` | `results/repeats/stability.md` |
| Ablasi prompt | laptop + Ollama | `./run_ablation.sh` → `python analysis_systems.py ablation` | `results/ablation/summary.md` |
| Model tambahan | laptop + Ollama | `MODELS="..." ./run_extra_models.sh` → `python analysis_systems.py extra` | `results/extra_models/summary.md` |

Setiap run menulis `manifest_*.json` (versi macOS, versi Ollama, digest dan kuantisasi model, setelan OLLAMA_*, versi paket Python, SHA-1 item). Panggilan yang gagal dicatat sebagai GENERATION_ERROR (`--log-errors`), tetapi 20 kegagalan berturut-turut menghentikan run (misalnya Ollama mati atau nama model salah). Jalankan ulang perintah yang sama: item yang sudah berhasil dipakai lagi, item yang gagal ditanyakan ulang (`--retry-errors`), dan catatan gagalnya dipindah ke `<file>.errors.jsonl`.

### Cara menjalankan (perbaikan 11 Nov 2026)

Run pertama tanggal 11 Nov gagal karena bug skrip zsh (daftar model/prompt tidak terpecah, misalnya `--prompt 'direct evidence'`). Ketiga skrip sekarang memakai bash (`run_common.sh` berisi pemeriksaan bersama) dan sudah diuji dengan model tiruan. Log run yang gagal disimpan di `logs/failed_20261111/`; output gagalnya sudah dihapus.

```
# Terminal 1 (biarkan berjalan)
OLLAMA_NUM_PARALLEL=6 OLLAMA_CONTEXT_LENGTH=1024 OLLAMA_KEEP_ALIVE=30m ollama serve

# Terminal 2
cd "<folder kit ini>"
chmod +x run_*.sh
export OLLAMA_NUM_PARALLEL=6 OLLAMA_CONTEXT_LENGTH=1024
nohup caffeinate -is ./run_repeats.sh all > logs/repeats.log 2>&1 &      # cf dulu, lalu main
tail -f logs/repeats.log                                                  # cek: harus ada baris 'qwen2.5:7b|direct: 0/440 done, 440 to run'
# setelah 'REPEATS DONE (all)':
nohup caffeinate -is ./run_ablation.sh > logs/ablation.log 2>&1 &
# model tambahan (pull dulu):
ollama pull mistral:7b
MODELS="mistral:7b" nohup caffeinate -is ./run_extra_models.sh > logs/extra.log 2>&1 &
```

Jalankan satu skrip pada satu waktu; dua skrip bersamaan membagi 6 slot Ollama dan memperlambat keduanya. Skrip berhenti sebelum memanggil model kalau: Ollama belum jalan, model belum di-pull, nama prompt salah, atau REPS bukan angka ≥ 2. Folder yang benar: `runs_repeat/rep2/{e1cf,main}/`, `runs_repeat/rep3/{e1cf,main}/`, `runs_ablation/qwen2.5_7b_abl_quote_first.jsonl`, dst. Nama folder atau file yang mengandung spasi berarti ada yang salah.

