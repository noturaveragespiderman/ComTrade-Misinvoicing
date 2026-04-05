import comtradeapicall
import pandas as pd
import requests
import os
import glob
import time
import ssl

ssl._create_default_https_context = ssl._create_unverified_context 

from config import COMTRADE_API_KEY, DIRECTORY, YEARS, COUNTRY_CODES, HS_CODES, SLEEP_TIMEOUT
from notifier import send_telegram_message, wait_for_telegram_approval

def get_expected_count(year, reporters, hs_codes):
    """Safely asks the UN API for the expected row count using the official comtradeapicall library."""
    reporter_list = reporters.split(',')
    # We keep the batch size at 3 to be safe with URL limits
    chunks = [",".join(reporter_list[i:i+3]) for i in range(0, len(reporter_list), 3)]
    total_count = 0
    
    print(f"Counting expected rows for {year} (Checking {len(chunks)} batches)...")
    
    for chunk in chunks:
        try:
            # Using the official getCountFinalData exactly as specified in the GitHub docs
            count_df = comtradeapicall.getCountFinalData(
                COMTRADE_API_KEY, 
                typeCode='C', 
                freqCode='A', 
                clCode='HS', 
                period=str(year), 
                reporterCode=chunk, 
                cmdCode=hs_codes, 
                flowCode='M,X,RM,RX', 
                partnerCode=None, 
                partner2Code=None, 
                customsCode=None, 
                motCode=None, 
                aggregateBy=None, 
                breakdownMode='classic'
            )
            
            # The library returns a pandas DataFrame where 'count' is a column
            if count_df is not None and isinstance(count_df, pd.DataFrame) and 'count' in count_df.columns:
                batch_count = int(count_df['count'].sum())
                total_count += batch_count
                print(f"  └─ Batch success: {batch_count:,} expected rows.")
            else:
                print(f"  ⚠️ Count failed for chunk [{chunk}]: Dataframe empty. (Check API limits)")
                
        except Exception as e:
            # Now, if it fails, it will tell us the EXACT library error instead of failing silently
            print(f"  ⚠️ API Count Error on chunk [{chunk}]: {str(e)}")
            
        time.sleep(2) # Respect UN API rate limits
            
    return total_count if total_count > 0 else "Unknown"

def run_retrieval():
    os.makedirs(DIRECTORY, exist_ok=True)
    send_telegram_message(f"🚀 <b>Pipeline Started</b>\nTargeting HS Chapters: {HS_CODES}")
    
    target_hs_list = [code.strip() for code in HS_CODES.split(',')]
    
    # --- SUMMARY TRACKERS ---
    total_rows_saved = 0
    successful_years = []
    empty_years = []
    stopped_by_user = False
    
    for index, year in enumerate(YEARS):
        print(f"\n{'='*40}")
        print(f"📥 PROCESSING YEAR: {year}")
        print(f"{'='*40}")
        
        expected_rows = get_expected_count(year, COUNTRY_CODES, HS_CODES)
        exp_str = f"{expected_rows:,}" if isinstance(expected_rows, int) else "Unknown"
        send_telegram_message(f"⏳ <b>Year {year}</b>\nExpected: {exp_str}\n<i>Downloading files...</i>")
        
        try:
            comtradeapicall.bulkDownloadFinalFile(
                subscription_key=COMTRADE_API_KEY, directory=DIRECTORY, 
                typeCode='C', freqCode='A', clCode='HS', period=year, 
                reporterCode=COUNTRY_CODES, decompress=True
            )
            
            raw_files = glob.glob(f"{DIRECTORY}/*{year}*.txt")
            all_dfs = []

            for file in raw_files:
                filename = os.path.basename(file)
                try:
                    # Try to read the file
                    df = pd.read_csv(file, sep='\t', low_memory=False, dtype=str)
                    if len(df.columns) < 5:
                        df = pd.read_csv(file, sep=',', low_memory=False, dtype=str)
                    
                    print(f"📄 Processing {filename}...")
                    print(f"   ├─ Raw rows in file: {len(df)}")
                    
                    df.columns = [col.lower().strip() for col in df.columns]
                    
                    # DIAGNOSTIC: Check if columns exist
                    if 'cmdcode' not in df.columns or 'flowcode' not in df.columns:
                        print(f"   ⚠️ ERROR: Columns missing! Found: {list(df.columns[:5])}...")
                        continue

                    # Clean data
                    df['cmdcode_clean'] = df['cmdcode'].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                    df['flowcode_clean'] = df['flowcode'].astype(str).str.upper().str.strip()
                    
                    # 1. HS FILTER CHECK
                    df['hs2_chapter'] = df['cmdcode_clean'].str[:2]
                    hs_mask = df['hs2_chapter'].isin(target_hs_list)
                    hs_count = hs_mask.sum()
                    print(f"   ├─ Rows matching HS Chapters ({HS_CODES}): {hs_count}")
                    
                    # 2. FLOW FILTER CHECK
                    valid_flows = ['M', 'X', 'RM', 'RX', '1', '2', '3', '4', '01', '02', '03', '04']
                    flow_mask = df['flowcode_clean'].isin(valid_flows)
                    flow_count = flow_mask.sum()
                    print(f"   ├─ Rows matching Flows (M/X): {flow_count}")
                    
                    # Final Filter
                    filtered_df = df[flow_mask & hs_mask].copy()
                    print(f"   └─ Final rows kept from this file: {len(filtered_df)}")
                    
                    if not filtered_df.empty:
                        all_dfs.append(filtered_df)
                        
                except Exception as e:
                    print(f"   ❌ Error reading {filename}: {e}")
                finally:
                    # TEMPORARY: Comment this out if you want to inspect the .txt files manually!
                    if os.path.exists(file): os.remove(file)

            # --- SAVE DATA & UPDATE TRACKERS ---
            if all_dfs:
                master_df = pd.concat(all_dfs, ignore_index=True)
                output_path = os.path.join(DIRECTORY, f"cleaned_data_{year}.csv")
                master_df.to_csv(output_path, index=False)
                
                actual_rows = len(master_df)
                total_rows_saved += actual_rows
                successful_years.append(year)
                file_size_mb = os.path.getsize(output_path) / (1024 * 1024)
                
                sample_cols = ['reportercode', 'partnercode', 'cmdcode_clean', 'flowcode_clean', 'primaryvalue']
                available_cols = [c for c in sample_cols if c in master_df.columns]
                sample_str = master_df[available_cols].head(5).to_string(index=False)
                del master_df
                
                send_telegram_message(
                    f"✅ <b>{year} Complete!</b>\n"
                    f"Expected: {exp_str}\n"
                    f"Saved: {actual_rows:,} rows\n"
                    f"Size: {file_size_mb:.2f} MB\n\n"
                    f"<b>Sample:</b>\n<pre>{sample_str}</pre>"
                )
                print(f"✅ Filtered data saved to: {output_path}")
            else:
                empty_years.append(year)
                send_telegram_message(f"⚠️ <b>Year {year} Empty</b>\nNo matching rows.")

            # Cleanup .gz files
            for gz in glob.glob(f"{DIRECTORY}/*{year}*.gz"): os.remove(gz)
                
            # --- THE TELEGRAM LOCK (Skip if it's the last year) ---
            if index < len(YEARS) - 1:
                print("\n" + "="*40)
                user_wants_to_continue = wait_for_telegram_approval()
                if not user_wants_to_continue:
                    stopped_by_user = True
                    break

        except Exception as e:
            print(f"Error: {e}")
            empty_years.append(year)
            stopped_by_user = True
            break

    # ==========================================
    # FINAL SUMMARY REPORT
    # ==========================================
    print("\n" + "="*40)
    print("Generating Final Report...")
    
    header = "🛑 <b>Pipeline Stopped Early</b>" if stopped_by_user else "🎉 <b>Pipeline Finished Successfully!</b>"
    
    success_str = ", ".join(successful_years) if successful_years else "None"
    empty_str = ", ".join(empty_years) if empty_years else "None"
    
    summary_msg = (
        f"{header}\n\n"
        f"📊 <b>FINAL SUMMARY</b>\n"
        f"✅ <b>Years Saved:</b> {success_str}\n"
        f"⚠️ <b>Years Empty/Failed:</b> {empty_str}\n"
        f"📈 <b>Total Rows Collected:</b> {total_rows_saved:,}\n"
    )
    
    send_telegram_message(summary_msg)
    print(f"PIPELINE COMPLETE. Total rows saved: {total_rows_saved:,}")

if __name__ == "__main__":
    run_retrieval()