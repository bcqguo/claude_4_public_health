"""
MCP server exposing OpenFDA FAERS query tools.

Run standalone:
    python mcp_faers_server.py

Or via Claude Code settings.json:
    {
      "mcpServers": {
        "faers_query": {
          "command": "/home/dada/anaconda3/bin/python",
          "args": ["/home/dada/Barn/GQ/ADR/Meetings/Yale_talk/utils/mcp_faers_server.py"]
        }
      }
    }
"""

import sys, os
sys.path.insert(0, os.path.dirname(__file__))

import requests, pickle, json, re, zipfile, datetime, urllib.parse
import numpy as np
import pandas as pd
from mcp.server.fastmcp import FastMCP

mcp = FastMCP("faers_query")

# --- paths / constants ---------------------------------------------------
# Default location for processed quarterly .pkl output (per project convention)
DEFAULT_OUTPUT_PATH = "/home/dada/Barn/GQ/ADR/Meetings/Yale_talk"
DEFAULT_RAW_DIR = os.path.join(DEFAULT_OUTPUT_PATH, "faers_raw")
FAERS_ZIP_URL = "https://fis.fda.gov/content/Exports/faers_ascii_{label}.zip"

# drug-name -> RxNorm ingredient / ATC4 mapping (resolved relative to this file)
_MAP_PATH = os.path.join(os.path.dirname(__file__), "..", "..", "..", "RxNorm", "name_map_atc4.pkl")
(name_map, name_atc4) = pickle.load(open(os.path.normpath(_MAP_PATH), "rb"))


def cleanCol(df, col):
    """Lowercase string columns; normalize nulls / 'UNK' to the literal 'nan'."""
    for i in col:
        if df[i].dtype == "float64":
            df[i] = df[i].astype(str)
        else:
            df[i] = np.where((df[i].isnull()) | (df[i] == "UNK"), "nan", df[i].str.lower())
    return df


def _derive_label(ascii_dir: str) -> str:
    """Derive a quarter label like '2026q1' from a FAERS ASCII filename (e.g. DRUG26Q1.txt)."""
    for fn in os.listdir(ascii_dir):
        m = re.search(r"(\d{2})Q(\d)", fn.upper())
        if m:
            return f"20{m.group(1)}q{m.group(2)}"
    return os.path.basename(ascii_dir.rstrip("/"))

@mcp.tool()
def get_faers_count(drug: str) -> dict:
    """Return total FAERS adverse event report count for a drug via OpenFDA.

    Args:
        drug: Generic drug name, e.g. 'metformin', 'atorvastatin'
    """
    r = requests.get(
        "https://api.fda.gov/drug/event.json",
        params={"search": f'patient.drug.medicinalproduct:"{drug}"', "limit": 1},
        timeout=10,
    )
    r.raise_for_status()
    total = r.json().get("meta", {}).get("results", {}).get("total", 0)
    return {"drug": drug, "faers_report_cases": total}


@mcp.tool()
def get_faers_top_events(drug: str, top_n: int = 5) -> dict:
    """Return the top adverse event PT terms reported for a drug in FAERS.

    Args:
        drug: Generic drug name, e.g. 'metformin'
        top_n: Number of top events to return (max 10)
    """
    top_n = min(top_n, 10)
    r = requests.get(
        "https://api.fda.gov/drug/event.json",
        params={
            "search": f'patient.drug.medicinalproduct:"{drug}"',
            "count": "patient.reaction.reactionmeddrapt.exact",
            "limit": top_n,
        },
        timeout=10,
    )
    r.raise_for_status()
    results = r.json().get("results", [])
    return {
        "drug": drug,
        "top_adverse_events": [
            {"meddra_pt": item["term"], "report_count": item["count"]}
            for item in results
        ],
    }


@mcp.tool()
def get_faers_drug_event_pair(drug: str, event_pt: str) -> dict:
    """Return co-report count for a specific drug + MedDRA PT pair (for PRR/ROR signal detection).

    Args:
        drug: Generic drug name, e.g. 'atorvastatin'
        event_pt: MedDRA preferred term, e.g. 'rhabdomyolysis'
    """
    import urllib.parse
    search = (
        f'patient.drug.medicinalproduct:"{drug}"'
        f' AND patient.reaction.reactionmeddrapt:"{event_pt}"'
    )
    url = (
        "https://api.fda.gov/drug/event.json?"
        + urllib.parse.urlencode({"search": search, "limit": 1})
    )
    r = requests.get(url, timeout=10)
    r.raise_for_status()
    total = r.json().get("meta", {}).get("results", {}).get("total", 0)
    return {"drug": drug, "meddra_pt": event_pt, "co_report_count": total}

@mcp.tool()
def mergeFAERS(path_in: str, path_out: str = DEFAULT_OUTPUT_PATH) -> dict:
    """Merge a quarter's FAERS ASCII files into one processed dataframe and pickle it.

    Reads DEMO/DRUG/OUTC/INDI/REAC `.txt` files from `path_in`, enriches drugs with
    RxNorm ingredient + ATC4 class, merges on (primaryid, caseid), and writes
    `{path_out}/{quarter}.pkl` (e.g. 2026q1.pkl).

    Args:
        path_in: Path to the ASCII folder containing the quarter's *.txt files.
        path_out: Directory to write the processed .pkl (default: Yale_talk folder).
    """
    # quarter label (e.g. '2026q1') derived from a raw filename suffix
    file_out = _derive_label(path_in)

    # merge all files(DEMO, DRUG, REAC, OUTC, INDI) in path_in
    for filename in os.listdir(path_in):

        if "DEMO" in filename.upper() and "TXT" in filename.upper():
            try:
                demo_df = pd.read_csv(path_in + "/" + filename, sep = "$", low_memory=False)
            except:
                demo_df = pd.read_csv(path_in + "/" + filename, sep = "$", encoding='iso-8859-1', low_memory=False)   
                
            if "sex" in demo_df.columns:
                demo_df.rename(columns = {"sex":'gndr_cod'}, inplace = True)
            #demo_df = demo_df[['primaryid','caseid','age','age_cod','gndr_cod','wt','wt_cod','occp_cod','reporter_country','occr_country']]
            demo_df = demo_df[['fda_dt','rept_cod', 'primaryid','caseid','age','age_cod','gndr_cod','wt','wt_cod']]
            demo_df = demo_df[(demo_df.wt.isnull() == False) & (demo_df.age.isnull() == False)]
            #demo_df.drop('caseid', axis = 1, inplace = True)
            
        if "DRUG" in filename.upper() and "TXT" in filename.upper():
            try:
                drug_df = pd.read_csv(path_in + "/" + filename, sep = "$", low_memory=False)
            except:
                drug_df = pd.read_csv(path_in + "/" + filename, sep = "$", encoding='iso-8859-1', low_memory=False)   
            
            # drugname	route	dose_vbm	dose_amt	dose_unit	dose_form	dose_freq	dose
            drug_df = drug_df[['primaryid', "caseid", 'drugname','route','dose_vbm','dose_amt',
                               'dose_unit','dose_form','dose_freq']]

            #lower col values
            drug_df = cleanCol(drug_df, ['drugname','route','dose_vbm','dose_amt', 'dose_unit','dose_form','dose_freq'])
            drug_df = drug_df[(drug_df.drugname != "nan") & (drug_df.drugname != "unk")]   

            # get ingredient and atc4
            drug_df = preProcess(drug_df, "FAERS")            
            drug_df['treatment'] = [re.sub(r"[|+|\\+]", "", json.dumps(i.to_dict())) for _, i in
                      drug_df[['drugname','ingredient', 'atc4', 'route','dose']].iterrows()]
            #group treatment by each report and separate by "; " without duplicates
            drug_df = drug_df.groupby(['primaryid', 'caseid']).treatment.apply(lambda x: "; ".join(set(x.astype(str)))).reset_index()
            
        if "OUTC" in filename.upper() and "TXT" in filename.upper():            
            outc_df = pd.read_csv(path_in + "/" + filename, sep = "$", low_memory=False)                   
            outc_df = outc_df.groupby(['primaryid', 'caseid'])[outc_df.columns[2]].apply("; ".join).reset_index()
            #outc_df = outc_df.groupby(['primaryid', 'caseid'])[outc_df.columns[2]].last()

        if "INDI" in filename.upper() and "TXT" in filename.upper():            
            indi_df = pd.read_csv(path_in + "/" + filename, sep = "$", low_memory=False) 
            indi_df = indi_df.groupby(['primaryid', 'caseid']).indi_pt.apply(lambda x: "; ".join(x.astype(str).str.lower())).reset_index()
            #indi_df = indi_df.groupby(['primaryid', 'caseid']).indi_pt.last()
            
        if "REAC" in filename.upper() and "TXT" in filename.upper():            
            reac_df = pd.read_csv(path_in + "/" + filename, sep = "$",low_memory=False)            
            reac_df = reac_df.groupby(['primaryid', 'caseid']).pt.apply(lambda x: "; ".join(x.astype(str).str.lower())).reset_index()
            #reac_df = reac_df.groupby(['primaryid', 'caseid']).pt.last()

    #merge files based on primary report id and case id
    quarter_df = pd.merge(demo_df, drug_df[['primaryid', 'caseid', 'treatment']], 
                          on=['primaryid', 'caseid'], how='inner')  
    quarter_df = pd.merge(quarter_df, outc_df, on=['primaryid', 'caseid'], how = "left")  
    quarter_df = pd.merge(quarter_df, indi_df, on=['primaryid', 'caseid']) # how='inner'
    quarter_df = pd.merge(quarter_df, reac_df, on=['primaryid', 'caseid']) # how='inner'
        
    print(f"The shape of {file_out} is {quarter_df.shape}")

    os.makedirs(path_out, exist_ok=True)
    out_pkl = os.path.join(path_out, f"{file_out}.pkl")
    pickle.dump(quarter_df, open(out_pkl, "wb"))

    return {
        "label": file_out,
        "rows": int(quarter_df.shape[0]),
        "cols": list(quarter_df.columns),
        "output_pkl": out_pkl,
    }

@mcp.tool()
def get_latest_faers_quarter() -> dict:
    """Discover the most recent FAERS quarterly ASCII release available from the FDA.

    Probes the FDA export URLs backwards from the current calendar quarter until it
    finds one that exists, returning its download URL and label (e.g. '2026q1').
    """
    today = datetime.date.today()
    cur_q = (today.month - 1) // 3 + 1
    year, quarter = today.year, cur_q

    for _ in range(6):  # probe up to ~6 quarters back
        label = f"{year}q{quarter}"
        url = FAERS_ZIP_URL.format(label=label)
        try:
            # Accept-Encoding: identity — the FDA server mislabels ranged zip bytes
            # as gzip, which corrupts auto-decoding; ask for raw bytes instead.
            r = requests.get(
                url,
                headers={"Range": "bytes=0-3", "Accept-Encoding": "identity"},
                timeout=20,
            )
            if r.status_code in (200, 206) and r.content[:2] == b"PK":
                return {
                    "year": year,
                    "quarter": quarter,
                    "label": label,
                    "url": url,
                    "content_type": r.headers.get("Content-Type", ""),
                }
        except requests.RequestException:
            pass
        # step back one quarter
        quarter -= 1
        if quarter == 0:
            quarter, year = 4, year - 1

    return {"error": "No FAERS quarterly release found in the last 6 quarters."}


@mcp.tool()
def download_faers_quarter(year: int, quarter: int, dest_dir: str = DEFAULT_RAW_DIR) -> dict:
    """Download and unzip a FAERS quarterly ASCII release from the FDA.

    Streams the zip to disk (idempotent — skips a valid existing zip), extracts it,
    and locates the ASCII folder of `.txt` files ready for mergeFAERS().

    Args:
        year: 4-digit year, e.g. 2026
        quarter: Quarter number 1-4
        dest_dir: Directory to download/extract into (default: Yale_talk/faers_raw)
    """
    label = f"{year}q{quarter}"
    url = FAERS_ZIP_URL.format(label=label)
    os.makedirs(dest_dir, exist_ok=True)
    zip_path = os.path.join(dest_dir, f"faers_ascii_{label}.zip")
    extract_dir = os.path.join(dest_dir, label)

    # download (skip if a valid zip already exists)
    need_download = True
    if os.path.exists(zip_path):
        try:
            with zipfile.ZipFile(zip_path) as zf:
                if zf.testzip() is None:
                    need_download = False
        except zipfile.BadZipFile:
            need_download = True

    if need_download:
        # Accept-Encoding: identity — avoid the server's bogus gzip labelling that
        # would corrupt the already-compressed zip during streaming decode.
        with requests.get(
            url, stream=True, timeout=120, headers={"Accept-Encoding": "identity"}
        ) as r:
            r.raise_for_status()
            with open(zip_path, "wb") as f:
                for chunk in r.iter_content(chunk_size=1 << 20):  # 1 MB chunks
                    f.write(chunk)

    # extract
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(extract_dir)

    # locate the ASCII subdir (FDA nests the .txt files under ASCII/ or ascii/)
    ascii_dir = None
    for root, dirs, files in os.walk(extract_dir):
        if any(f.upper().endswith(".TXT") for f in files):
            ascii_dir = root
            break

    txt_files = (
        sorted(f for f in os.listdir(ascii_dir) if f.upper().endswith(".TXT"))
        if ascii_dir else []
    )
    return {
        "label": label,
        "zip_path": zip_path,
        "zip_size_bytes": os.path.getsize(zip_path),
        "ascii_dir": ascii_dir,
        "txt_files": txt_files,
    }


def preProcess(drugs, data_type):
    '''
    map drug name with ingredient and ATC4 level info
    '''
    
    global name_map, name_atc4

    if data_type == "FAERS":    
        drugs["ingredient"] = [name_map[k] if k in name_map.keys() else k for k in drugs.drugname]
        drugs["atc4"] = [name_atc4[k].lower() if k in name_atc4.keys() else k for k in drugs.ingredient]
        drugs = cleanCol(drugs, ['route','dose_vbm','dose_amt', 'dose_unit','dose_form','dose_freq'])
        drugs['dose'] = drugs[['dose_amt', 'dose_unit','dose_form','dose_freq']].apply(lambda x: " ".join(x.astype(str)), axis=1)
        drugs.drop(["dose_vbm","dose_amt","dose_unit","dose_form","dose_freq"], axis = 1, inplace = True)

        # get dose rank, the coutn of nan in dose 
        drugs['dose_rank'] = [s.split(" ").count("nan") for s in drugs.dose]
        drugs = (drugs.sort_values(['primaryid', 'caseid', 'drugname', 'dose_rank'], ascending = False)    
        .drop(columns='dose_rank')
        .reset_index(drop=True))
    elif data_type == "AERS":
        drugs["ingredient"] = [name_map[k] if k in name_map.keys() else k for k in drugs.drugname]
        drugs["atc4"] = [name_atc4[k].lower() if k in name_atc4.keys() else k for k in drugs.ingredient]
        drugs = cleanCol(drugs, ['route','dose'])
    else:
        print("Select ADR data type.")        
    
    return drugs


if __name__ == "__main__":
    mcp.run()
