import anthropic, json, requests

# real OpenFDA call (free, no API key) ---
def get_faers_count(drug):
    r = requests.get(
        "https://api.fda.gov/drug/event.json",
        params={"search": f'patient.drug.medicinalproduct:"{drug}"', "limit": 1}
    )
    total = r.json().get("meta", {}).get("results", {}).get("total", 0)
    return {"drug": drug, "faers_report_cases": total}

