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

## Validasi manusia (wajib sebelum submit)
```
python run_llm.py export --items items_llm600.jsonl --out human_validation.xlsx   # sampel 20% dari E1, I1, I3 (jalankan setelah paraphrase)
python run_llm.py score --sheet human_validation_filled.xlsx --out validation.json
```
`human_validation.xlsx` (dibuat oleh `hitl_sheet.py`) berisi lembar bertahap:

| Lembar | Diisi oleh | Isi |
|---|---|---|
| `0_PETUNJUK` | dibaca semua | Langkah 0–5, peringatan konten, teks kebijakan, kriteria 1/0 per MR, contoh, legenda warna |
| `1_PENILAI_1` | Penilai 1 | Kolom NILAI (dropdown 1/0) + catatan; kata yang dihapus/ditukar ditandai merah, penggantinya biru |
| `2_PENILAI_2` | Penilai 2 (terpisah) | Sama dengan lembar 1 |
| `3_ADJUDIKASI` | Adjudikator | Status otomatis; baris "BEDA" berwarna oranye, isi ADJ (1/0) + alasan |
| `4_REKAP` | otomatis | Progres, % sepakat, Cohen's κ, tingkat validitas per MR |

`score` membaca langsung sel yang diketik (bukan hasil rumus), dan masih menerima format lama (kolom rater1/rater2, `ADJ=1/0` di notes).

## Menjalankan semua tahap LLM sekaligus
`run_all.sh` menjalankan parafrase → lembar HITL → baseline pada 600 postingan → 6 run LLM → evaluasi. Bisa dilanjutkan bila terputus (jalankan ulang perintah yang sama):
```
nohup caffeinate -is ./run_all.sh > logs/run_all.log 2>&1 &
tail -f logs/run_all.log
```
