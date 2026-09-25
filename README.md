# ECRS Risk Console

Dashboard Streamlit untuk memantau risiko kontribusi pemberi kerja berdasarkan tiga sinyal dari Engine Wave 1:

- **Module A:** registration volatility / penurunan headcount yang tidak dijelaskan resign.
- **Module B:** peer-group wage benchmarking.
- **Module C:** selisih expected dan actual remittance.

Dataset yang digunakan adalah data sintetis/dummy, bukan data BPJS asli.

## 1. Prasyarat

Pastikan sudah tersedia:

- Python 3.10 atau lebih baru
- Git, jika proyek diambil dari repository
- Terminal atau command prompt

Cek versi Python:

```bash
python3 --version
```

Di Windows, gunakan:

```powershell
python --version
```

## 2. Masuk ke folder proyek

```bash
cd /home/allo/Code/Healthkathon
```

Jika memakai Windows, sesuaikan path dengan lokasi folder proyek.

## 3. Buat virtual environment

Linux/macOS:

```bash
python3 -m venv .venv
source .venv/bin/activate
```

Windows PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
```

Jika berhasil, nama `(.venv)` akan muncul di awal prompt terminal.

## 4. Install dependency

Dengan virtual environment yang masih aktif, jalankan:

```bash
python -m pip install --upgrade pip
python -m pip install -r requirements.txt
```

Dependency utama yang dipasang:

- `streamlit` untuk dashboard
- `pandas` untuk pengolahan data
- `numpy` untuk perhitungan dan simulasi data

## 5. Siapkan data

### Opsi A: Jalankan dengan data demo

Tidak perlu menyiapkan CSV. Jika file Wave 0 belum ada, dashboard otomatis memakai dataset demo sintetis yang deterministik.

### Opsi B: Pakai output Engine Wave 0

1. Buka notebook berikut di VS Code atau Jupyter:

	`Engine/ECRS_Wave0_Data_Setup.ipynb`

2. Jalankan semua cell notebook.

3. Ambil enam file CSV hasil generate:

	- `employer_master.csv`
	- `headcount_timeseries.csv`
	- `payroll_timeseries.csv`
	- `remittance_timeseries.csv`
	- `resign_records.csv`
	- `ground_truth.csv`

4. Simpan keenam file tersebut ke folder:

	`data/dummy/`

	Folder tersebut boleh dibuat jika belum ada:

	```bash
	mkdir -p data/dummy
	```

5. Jalankan dashboard. Dashboard akan otomatis beralih dari mode demo ke data CSV ketika file wajib tersedia.

## 6. Jalankan Wave 2 composite scoring (opsional)

Wave 2 menggabungkan skor Module A, B, dan C menjadi satu `composite_score`,
band risiko (`Tinggi`, `Sedang`, `Rendah`), ranking, coverage, serta penjelasan
per employer.

1. Pastikan enam CSV sudah tersedia di `data/dummy/`.
2. Buka notebook:

	`Engine/wave2_composite_scoring(1).ipynb`

3. Untuk eksekusi lokal, set `HK_DATA_DIR` ke folder CSV sebelum menjalankan
	semua cell notebook:

	```bash
	export HK_DATA_DIR=data/dummy
	```

	Di Windows PowerShell:

	```powershell
	$env:HK_DATA_DIR = "data/dummy"
	```

4. Jalankan semua cell notebook. Secara lokal, output akan dibuat di:

	`output_wave2/output_scores.json`

	dan `output_wave2/output_scores.csv`.

5. Jalankan atau refresh dashboard. Dashboard akan otomatis mendeteksi
	`output_scores.json` dan beralih ke mode **Wave 2 Composite**.

Tanpa output Wave 2, dashboard tetap berjalan menggunakan scoring langsung
dari tiga sinyal Wave 1.

## 7. Jalankan dashboard

Pastikan virtual environment aktif, lalu jalankan:

```bash
streamlit run app/streamlit_app.py
```

Browser biasanya terbuka otomatis. Jika tidak, buka alamat berikut:

```text
http://localhost:8501
```

Untuk menjalankan pada port lain:

```bash
streamlit run app/streamlit_app.py --server.port 8511
```

## 8. Menggunakan dashboard

1. Gunakan filter **Sektor**, **Wilayah**, dan **Status risiko** di sidebar.
2. Tab **Ringkasan risiko** menampilkan antrian pemeriksaan dan komposisi sinyal.
3. Tab **A · Headcount** menampilkan perubahan peserta aktif dan catatan keluar.
4. Tab **B · Peer wage** membandingkan DPI dengan median kelompok sejenis.
5. Tab **C · Reconciliation** membandingkan expected contribution dengan actual remittance.
6. Pilih employer pada tab Module A untuk melihat tren detail perusahaan.

Skor dashboard adalah alat prioritas investigasi, bukan keputusan atau vonis otomatis.

## 9. Troubleshooting

### `streamlit: command not found`

Pastikan virtual environment aktif. Alternatifnya, panggil Streamlit sebagai module:

```bash
python -m streamlit run app/streamlit_app.py
```

### Error `externally-managed-environment`

Jangan install package ke Python sistem. Buat dan aktifkan `.venv` seperti pada langkah 3, lalu ulangi langkah 4.

### Dashboard masih menampilkan mode demo

Pastikan nama file dan lokasinya tepat. Semua file berikut harus berada langsung di `data/dummy/`, bukan di subfolder lain:

```text
data/dummy/employer_master.csv
data/dummy/headcount_timeseries.csv
data/dummy/payroll_timeseries.csv
data/dummy/remittance_timeseries.csv
data/dummy/resign_records.csv
data/dummy/ground_truth.csv
```

Setelah menambahkan file, refresh halaman browser atau restart Streamlit.

### Dashboard belum menampilkan Wave 2

Pastikan file berikut sudah ada:

```text
output_wave2/output_scores.json
```

Jika notebook menghasilkan output di lokasi lain, salin `output_scores.json` ke
`output_wave2/` atau ke `data/dummy/`. Setelah itu refresh halaman dashboard.

### Port sudah digunakan

Jalankan dengan port berbeda:

```bash
streamlit run app/streamlit_app.py --server.port 8511
```

## Struktur penting

```text
app/streamlit_app.py                 # entrypoint dashboard
data/dummy/                          # input CSV Wave 0
output_wave2/output_scores.json      # output composite scoring Wave 2
Engine/ECRS_Wave0_Data_Setup.ipynb   # generator dataset sintetis
Engine/wave2_composite_scoring(1).ipynb # composite score + explainability
Engine/module_a_registration_volatility.ipynb
Engine/module_b_peer_group_wage.ipynb
requirements.txt                     # dependency Python
```
