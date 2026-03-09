import sys
import subprocess
import os

def install_and_import():
    try:
        import pandas as pd
        import openpyxl
        import PyPDF2
    except ImportError:
        print("Installing dependencies...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "pandas", "openpyxl", "PyPDF2", "xlrd"], stdout=subprocess.DEVNULL)
    
if __name__ == '__main__':
    install_and_import()
    import pandas as pd
    import PyPDF2

    base_path = r'c:\Users\asus\Documents\ECO-TWIN ORACLE'

    try:
        df1 = pd.read_excel(os.path.join(base_path, '_h_batch_process_data.xlsx'), nrows=10)
        with open(os.path.join(base_path, 'excel1_info.txt'), 'w', encoding='utf-8') as f:
            f.write("-- _h_batch_process_data.xlsx columns --\n")
            f.write(str(df1.dtypes) + "\n\n")
            f.write(str(df1.head()) + "\n")
    except Exception as e:
        with open(os.path.join(base_path, 'excel1_info.txt'), 'w', encoding='utf-8') as f:
            f.write(f"Error: {e}\n")

    try:
        df2 = pd.read_excel(os.path.join(base_path, '_h_batch_production_data.xlsx'), nrows=10)
        with open(os.path.join(base_path, 'excel2_info.txt'), 'w', encoding='utf-8') as f:
            f.write("-- _h_batch_production_data.xlsx columns --\n")
            f.write(str(df2.dtypes) + "\n\n")
            f.write(str(df2.head()) + "\n")
    except Exception as e:
        with open(os.path.join(base_path, 'excel2_info.txt'), 'w', encoding='utf-8') as f:
            f.write(f"Error: {e}\n")

    try:
        reader1 = PyPDF2.PdfReader(os.path.join(base_path, 'Hackathon_Problem Statement.pdf'))
        with open(os.path.join(base_path, 'pdf1_info.txt'), 'w', encoding='utf-8') as f:
            for i in range(len(reader1.pages)):
                f.write(f"--- Page {i+1} ---\n")
                text = reader1.pages[i].extract_text()
                if text: f.write(text + "\n")
    except Exception as e:
        with open(os.path.join(base_path, 'pdf1_info.txt'), 'w', encoding='utf-8') as f:
            f.write(f"Error: {e}\n")

    try:
        reader2 = PyPDF2.PdfReader(os.path.join(base_path, 'SpicyJalebi_EcoTwinOracle (2).pdf'))
        with open(os.path.join(base_path, 'pdf2_info.txt'), 'w', encoding='utf-8') as f:
            for i in range(len(reader2.pages)):
                f.write(f"--- Page {i+1} ---\n")
                text = reader2.pages[i].extract_text()
                if text: f.write(text + "\n")
    except Exception as e:
        with open(os.path.join(base_path, 'pdf2_info.txt'), 'w', encoding='utf-8') as f:
            f.write(f"Error reading pdf2: {e}\n")

    print("Data extraction complete.")
