#Not production - keeping in case the new direction goes down in flames

import os
import logging
import pdfplumber
import pandas as pd
from google.cloud import storage
from parser import SuperHeroFlex
from utils import download_blob, upload_blob

# Configure logging
logging.basicConfig(level=logging.INFO)

def process_pdf(file_path):
    parser = SuperHeroFlex(file_path)
    df = parser.extract_all()
    # use text_dict from parsing context
    with pdfplumber.open(file_path) as pdf:
        text_dict = {f"page_{i + 1}": {"text": page.extract_text()} for i, page in enumerate(pdf.pages)}
    product_type = parser.identify_product(text_dict)
    return df, product_type

def list_files_in_bucket(bucket_name, prefix):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    return list(bucket.list_blobs(prefix=prefix))

def get_processed_files(bucket_name, processed_list_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    processed_list_blob = bucket.get_blob(processed_list_blob_name)
    
    if processed_list_blob:
        processed_files_content = processed_list_blob.download_as_text()
        return set(processed_files_content.splitlines())
    return set()

def update_processed_file_list(bucket_name, processed_list_blob_name, file_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    processed_list_blob = bucket.get_blob(processed_list_blob_name)
    
    if processed_list_blob:
        processed_data = processed_list_blob.download_as_text()
        processed_files = set(processed_data.splitlines())
    else:
        processed_files = set()

    processed_files.add(file_name)
    blob = bucket.blob(processed_list_blob_name)
    blob.upload_from_string("\n".join(processed_files))

def move_file_to_folder(bucket_name, source_blob_name, destination_blob_name):
    storage_client = storage.Client()
    bucket = storage_client.bucket(bucket_name)
    
    # Copy file to new location (processed_files)
    bucket.copy_blob(bucket.get_blob(source_blob_name), bucket, destination_blob_name)
    # Delete original file
    bucket.delete_blob(source_blob_name)

def parse_batch(event=None):
    ingest_bucket_name = "gmp_accounting_tool_ingest_bucket"
    output_bucket_name = "gmp_accounting_tool_output_bucket"
    batch_ingest_prefix = "batch_ingest/"
    processed_files_prefix = "processed_files/"
    processed_list_name = 'list_of_processed_files.txt'

    aggregate_log = {}

    # Get files from batch_ingest folder
    blobs_in_batch = list_files_in_bucket(ingest_bucket_name, batch_ingest_prefix)

    # Get processed files
    processed_files = get_processed_files(ingest_bucket_name, processed_list_name)

    for blob in blobs_in_batch:
        
        file_name = os.path.basename(blob.name)

        if not file_name or not file_name.lower().endswith(".pdf") or blob.name.endswith("/"):
            logging.warning(f"Skipping invalid or non-PDF blob: {blob.name}")
            continue


        # Skip if file is already processed
        if file_name in processed_files:
            logging.info(f"File {file_name} is already processed, attempting to delete from batch_ingest.")
            bucket = storage.Client().bucket(ingest_bucket_name)
            try:
                bucket.delete_blob(blob.name)
                logging.info(f"Deleted {blob.name} from batch_ingest.")
            except Exception as e:
                logging.warning(f"Tried to delete {blob.name}, but it was already gone: {e}")
            continue


        # Construct full file path to avoid directory error
        local_temp_file = f'/tmp/{file_name}'
        try:
            download_blob(ingest_bucket_name, blob.name, local_temp_file)
            logging.info(f"Downloaded file: {file_name}")
        except Exception as e:
            logging.error(f"Failed to download file {file_name}: {str(e)}")
            continue

        try:
            # Process the PDF and generate a CSV file
            df, product_type = process_pdf(local_temp_file)
            logging.info(f"Detected product type for {file_name}: {product_type}")
            logging.info(f"Parsed {len(df)} rows for {file_name}")

            if not df.empty:
                output_csv_path = f"/tmp/{file_name.replace('.pdf', '.csv')}"
                df.to_csv(output_csv_path, index=False)
                logging.info(f"Created CSV: {output_csv_path}")
                aggregate_log[file_name] = product_type

                if not os.path.exists(output_csv_path):
                    logging.error(f"Expected output CSV not found: {output_csv_path}")
                else:
                    logging.info(f"Uploading file: {output_csv_path}")

                # Upload the CSV file to the output bucket
                output_blob_name = f"test_files/{file_name.replace('.pdf', '.csv')}"
                upload_blob(output_bucket_name, output_csv_path, output_blob_name)
                logging.info("Processing successfully completed")

            # Move the processed PDF to processed_files
            processed_file_blob = processed_files_prefix + file_name
            move_file_to_folder(ingest_bucket_name, blob.name, processed_file_blob)

            # Update the processed files list
            update_processed_file_list(ingest_bucket_name, processed_list_name, file_name)

        except Exception as e:
            logging.error(f"Processing failed for file {file_name}: {str(e)}")

    # Upload product type summary
    if aggregate_log:
        agg_df = pd.DataFrame([
            {"Filename": fname, "ProductType": ptype}
            for fname, ptype in aggregate_log.items()
        ])
        agg_output_path = "/tmp/aggregate_summary.csv"
        agg_df.to_csv(agg_output_path, index=False)
        upload_blob(output_bucket_name, agg_output_path, "aggregates/aggregate_summary.csv")
        logging.info("Aggregate summary uploaded.")

    return "Batch processing completed."


## previous parse_batch f(x)

def parse_batch(event=None):
    ingest_bucket_name = "gmp_accounting_tool_ingest_bucket"
    output_bucket_name = "gmp_accounting_tool_output_bucket"
    batch_ingest_prefix = "batch_ingest/"
    processed_files_prefix = "processed_files/"
    processed_list_name = 'list_of_processed_files.txt'

    aggregate_log = {}
    product_dfs = {}

    blobs_in_batch = list_files_in_bucket(ingest_bucket_name, batch_ingest_prefix)
    processed_files = get_processed_files(ingest_bucket_name, processed_list_name)

    for blob in blobs_in_batch:
        file_name = os.path.basename(blob.name)

        if not file_name or not file_name.lower().endswith(".pdf") or blob.name.endswith("/"):
            logging.warning(f"Skipping invalid or non-PDF blob: {blob.name}")
            continue

        if file_name in processed_files:
            logging.info(f"File {file_name} is already processed, attempting to delete from batch_ingest.")
            bucket = storage.Client().bucket(ingest_bucket_name)
            try:
                bucket.delete_blob(blob.name)
                logging.info(f"Deleted {blob.name} from batch_ingest.")
            except Exception as e:
                logging.warning(f"Tried to delete {blob.name}, but it was already gone: {e}")
            continue

        local_temp_file = f'/tmp/{file_name}'
        try:
            download_blob(ingest_bucket_name, blob.name, local_temp_file)
            logging.info(f"Downloaded file: {file_name}")
        except Exception as e:
            logging.error(f"Failed to download file {file_name}: {str(e)}")
            continue

        try:
            df, product_type = process_pdf(local_temp_file)
            logging.info(f"Detected product type for {file_name}: {product_type}")
            logging.info(f"Parsed {len(df)} rows for {file_name}")

            if df is None or df.empty:
                logging.warning(f"No data extracted for {file_name}; skipping.")
                continue

            # Save for grouped output
            aggregate_log[file_name] = product_type
            if product_type not in product_dfs:
                product_dfs[product_type] = [df]
            else:
                product_dfs[product_type].append(df)

            # Move processed file
            processed_file_blob = processed_files_prefix + file_name
            move_file_to_folder(ingest_bucket_name, blob.name, processed_file_blob)
            update_processed_file_list(ingest_bucket_name, processed_list_name, file_name)

        except Exception as e:
            logging.error(f"Processing failed for file {file_name}: {str(e)}")

    # Upload one CSV per product type
    for product_type, dfs in product_dfs.items():
        combined_df = pd.concat(dfs, ignore_index=True)
        grouped_path = f"/tmp/{product_type.lower()}.csv"
        grouped_blob = f"aggregates/{product_type.lower()}.csv"

        try:
            combined_df.to_csv(grouped_path, index=False)
            upload_blob(output_bucket_name, grouped_path, grouped_blob)
            logging.info(f"Uploaded grouped file: {grouped_blob}")
        except Exception as e:
            logging.error(f"Failed to write/upload grouped CSV for {product_type}: {e}")

    # Also upload aggregate_summary.csv
    if aggregate_log:
        agg_df = pd.DataFrame([
            {"Filename": fname, "ProductType": ptype}
            for fname, ptype in aggregate_log.items()
        ])
        agg_output_path = "/tmp/aggregate_summary.csv"
        agg_df.to_csv(agg_output_path, index=False)
        upload_blob(output_bucket_name, agg_output_path, "aggregates/aggregate_summary.csv")
        logging.info("Aggregate summary uploaded.")

    return "Batch processing completed."
