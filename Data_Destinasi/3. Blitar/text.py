import csv
import os
import re

def clean_csv_file(input_path, output_path):
    """
    Membersihkan file CSV yang berantakan karena text multi-line
    dan memastikan setiap baris memiliki format: name,rating,date,text
    """
    cleaned_rows = []
    
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Parse menggunakan csv reader yang bisa handle quoted fields
        reader = csv.reader(content.splitlines(), quotechar='"', skipinitialspace=True)
        
        header = None
        for row in reader:
            if header is None:
                header = row
                cleaned_rows.append(row)
                continue
            
            # Pastikan row memiliki minimal 4 kolom
            if len(row) >= 4:
                name = row[0].strip()
                rating = row[1].strip()
                date = row[2].strip()
                # Gabungkan semua kolom setelah index 3 jika ada
                text = ' '.join(row[3:]).strip()
                
                # Bersihkan newline di dalam text
                text = text.replace('\n', ' ').replace('\r', ' ')
                text = re.sub(r'\s+', ' ', text).strip()
                
                # Validasi rating adalah angka 1-5
                if rating.isdigit() and 1 <= int(rating) <= 5:
                    cleaned_rows.append([name, rating, date, text])
                    
            elif len(row) == 3:
                # Handle jika text kosong
                name = row[0].strip()
                rating = row[1].strip()
                date = row[2].strip()
                if rating.isdigit() and 1 <= int(rating) <= 5:
                    cleaned_rows.append([name, rating, date, ''])
        
        # Tulis hasil ke file output
        with open(output_path, 'w', encoding='utf-8', newline='') as f:
            writer = csv.writer(f, quoting=csv.QUOTE_MINIMAL)
            writer.writerows(cleaned_rows)
        
        print(f"✅ Berhasil: {os.path.basename(input_path)} -> {len(cleaned_rows)-1} baris data")
        return True
        
    except Exception as e:
        print(f"❌ Error pada {input_path}: {e}")
        return False


def process_all_csv(base_folder):
    """
    Memproses semua file CSV dalam folder dan subfolder
    """
    total_files = 0
    success_files = 0
    
    for root, dirs, files in os.walk(base_folder):
        for filename in files:
            if filename.endswith('.csv'):
                input_path = os.path.join(root, filename)
                
                # Buat folder output dengan struktur yang sama
                relative_path = os.path.relpath(root, base_folder)
                output_folder = os.path.join(base_folder, 'cleaned', relative_path)
                os.makedirs(output_folder, exist_ok=True)
                
                output_path = os.path.join(output_folder, filename)
                
                total_files += 1
                if clean_csv_file(input_path, output_path):
                    success_files += 1
    
    print(f"\n📊 Total: {success_files}/{total_files} file berhasil diproses")
    print(f"📁 Hasil tersimpan di: {os.path.join(base_folder, 'cleaned')}")


if __name__ == "__main__":
    base_folder = r"d:\Scrapping_Skripsi\Data_Destinasi"
    
    print("🚀 Memulai proses pembersihan CSV...\n")
    process_all_csv(base_folder)
    print("\n✨ Selesai!")