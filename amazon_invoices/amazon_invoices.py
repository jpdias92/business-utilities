import os
import re
import pdfplumber
from PyPDF2 import PdfReader, PdfWriter
from decimal import Decimal, InvalidOperation
import argparse
import warnings

warnings.filterwarnings("ignore", category=UserWarning, message="CropBox missing.*")

SPANISH_MONTHS = {
    "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
    "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
    "septiembre": "09", "setiembre": "09", "octubre": "10",
    "noviembre": "11", "diciembre": "12"
}

def is_invoice_page(text):
    return "Factura" in text and "Número de la factura" in text

def extract_invoice_info(text, fallback_index):
    SPANISH_MONTHS = {
        "enero": "01", "febrero": "02", "marzo": "03", "abril": "04",
        "mayo": "05", "junio": "06", "julio": "07", "agosto": "08",
        "septiembre": "09", "setiembre": "09", "octubre": "10",
        "noviembre": "11", "diciembre": "12"
    }

    # Extract invoice number
    num_match = re.search(r"Número de la factura\s+([A-Z0-9]+)", text, re.IGNORECASE)
    invoice_number = num_match.group(1) if num_match else f"unknown_{fallback_index}"

    # Updated date pattern
    date_match = re.search(
        r"Fecha de la factura(?:/Fecha de la entrega)?\s+(\d{1,2})\s+([a-záéíóúñ]+)\s+(\d{4})",
        text,
        re.IGNORECASE
    )
    if date_match:
        day, month_name, year = date_match.groups()
        month_num = SPANISH_MONTHS.get(month_name.lower(), "00")
        invoice_date = f"{year}{month_num}{int(day):02d}"
    else:
        invoice_date = "unknown_date"

    # Extract total amount
    amount_match = re.search(r"Total(?:[^0-9]+)?(\d+,\d{2})", text)
    if amount_match:
        amount_str = amount_match.group(1).replace(',', '.')
        try:
            amount = Decimal(amount_str)
        except InvalidOperation:
            amount = Decimal('0.00')
    else:
        amount = Decimal('0.00')

    return invoice_date, amount, invoice_number

def split_invoices_in_file(file_path, output_dir):
    log_entries = []
    total_amount = Decimal('0.00')
    try:
        pdf_reader = PdfReader(file_path)
        with pdfplumber.open(file_path) as pdf:
            invoice_writer = None
            invoice_info = None
            split_files = []

            for i, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    continue

                if is_invoice_page(text):
                    # Save previous invoice
                    if invoice_writer and invoice_info:
                        date_str, amount, inv_number = invoice_info
                        file_name = f"{date_str}_{str(amount).replace('.', '_')}_{inv_number}.pdf"
                        out_path = os.path.join(output_dir, file_name)
                        with open(out_path, "wb") as f_out:
                            invoice_writer.write(f_out)
                        split_files.append(file_name)
                        total_amount += amount

                    # Start new invoice
                    invoice_writer = PdfWriter()
                    invoice_writer.add_page(pdf_reader.pages[i])
                    invoice_info = extract_invoice_info(text, i + 1)
                else:
                    # Continuation of current invoice
                    if invoice_writer:
                        invoice_writer.add_page(pdf_reader.pages[i])

            # Save last invoice
            if invoice_writer and invoice_info:
                date_str, amount, inv_number = invoice_info
                file_name = f"{date_str}_{str(amount).replace('.', '_')}_{inv_number}.pdf"
                out_path = os.path.join(output_dir, file_name)
                with open(out_path, "wb") as f_out:
                    invoice_writer.write(f_out)
                split_files.append(file_name)
                total_amount += amount

            if split_files:
                log_entries.append(f"Processed '{os.path.basename(file_path)}': split into {', '.join(split_files)}")
            else:
                log_entries.append(f"Ignored '{os.path.basename(file_path)}': no invoices found")

    except Exception as e:
        log_entries.append(f"Error processing '{os.path.basename(file_path)}': {e}")

    return log_entries, total_amount

def process_directory(directory, output_dir):
    all_logs = []
    grand_total = Decimal('0.00')
    for root, _, files in os.walk(directory):
        for filename in files:
            if filename.lower().endswith(".pdf"):
                file_path = os.path.join(root, filename)
                logs, total = split_invoices_in_file(file_path, output_dir)
                all_logs.extend(logs)
                grand_total += total
    return all_logs, grand_total

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Split Amazon Business invoices into separate PDFs.")
    parser.add_argument("directory", help="Directory to recursively scan for PDF invoices.")
    parser.add_argument("--output", default="invoices_output", help="Directory to save split invoices.")
    args = parser.parse_args()

    os.makedirs(args.output, exist_ok=True)
    logs, grand_total = process_directory(args.directory, args.output)

    print("\n=== Processing Log ===")
    for log in logs:
        print(log)

    print(f"\n✅ Total invoice value processed: {grand_total:.2f} EUR")
