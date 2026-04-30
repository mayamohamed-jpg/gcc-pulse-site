import pandas as pd
import numpy as np
import os
import json
import requests
from io import BytesIO
from typing import Optional, Tuple, Dict, Any

FRD_FILE_URL = "https://frd-prod-webapps.aws.insideidc.com/ferda-rest/api?fileId=28aafb73-b4ac-4624-9d9e-a60481d750b9"

AUTH_TYPE = "none"

GCC_COUNTRIES = [
    "Saudi Arabia", "United Arab Emirates", "Qatar", "Kuwait", 
    "Oman", "Bahrain", "Iraq"
]

COUNTRY_MAPPING = {
    "KSA": "Saudi Arabia",
    "UAE": "United Arab Emirates",
    "Qatar": "Qatar",
    "Kuwait": "Kuwait",
    "Oman": "Oman",
    "Bahrain": "Bahrain",
    "Iraq": "Iraq",
    "Saudi Arabia": "Saudi Arabia",
    "United Arab Emirates": "United Arab Emirates",
    "Rest of Middle East": "Rest of Middle East",
    "Rest of Africa": "Rest of Africa",
    "Morocco": "Morocco",
    "Ghana": "Ghana",
    "Uganda": "Uganda",
    "Israel": "Israel",
    "Nigeria": "Nigeria",
    "Tunisia": "Tunisia",
    "Turkey": "Turkey"
}

def load_excel_from_frd(url: str, auth_type: str = "none", **auth_params) -> Optional[pd.DataFrame]:
    """Load Excel file from FRD API or local path."""
    try:
        if url.startswith(('http://', 'https://')):
            print(f"Downloading from: {url}")
            
            headers = {'User-Agent': 'Mozilla/5.0'}
            auth = None
            
            if auth_type == "bearer_token" and auth_params.get("token"):
                headers["Authorization"] = f"Bearer {auth_params['token']}"
            elif auth_type == "api_key" and auth_params.get("api_key"):
                headers["X-API-Key"] = auth_params["api_key"]
            elif auth_type == "basic" and auth_params.get("username"):
                auth = (auth_params["username"], auth_params.get("password", ""))
            
            response = requests.get(url, headers=headers, auth=auth, timeout=30)
            
            if response.status_code != 200:
                print(f"HTTP {response.status_code}: {response.text[:200]}")
                return None
            
            df = pd.read_excel(BytesIO(response.content), sheet_name=0)
        else:
            print(f"Reading local file: {url}")
            df = pd.read_excel(url, sheet_name=0)
        
        print(f"Loaded {len(df)} rows, columns: {list(df.columns)}")
        return df
        
    except Exception as e:
        print(f"Error loading data: {e}")
        return None


def build_gcc_dashboard(
    file_source: str,
    output_dir: str = ".",
    auth_type: str = "none",
    **auth_params
) -> Tuple[Optional[Dict], Optional[pd.DataFrame]]:

    df = load_excel_from_frd(file_source, auth_type, **auth_params)
    if df is None:
        return None, None
    
    print("\n" + "="*60)
    print("CLEANING AND STANDARDIZING DATA")
    print("="*60)
    
    df["Country"] = df["Country"].map(COUNTRY_MAPPING).fillna(df["Country"])
    
    df["Quarter"] = df["Quarter"].astype(str).str.strip()
    
    df["Year"] = df["Quarter"].str[:4].astype(int)
    df["Q_Num"] = df["Quarter"].str[5:].str.replace('Q', '').astype(int)
    
    df["Units"] = pd.to_numeric(df["Units"], errors='coerce').fillna(0).astype(int)
    
    df["Quarter_Sort"] = df["Year"] * 10 + df["Q_Num"]
    
    print(f"Data shape: {df.shape}")
    print(f"Countries found: {sorted(df['Country'].unique())}")
    print(f"Quarters range: {df['Quarter'].min()} to {df['Quarter'].max()}")
    print(f"Total GCC countries data: {len(df[df['Country'].isin(GCC_COUNTRIES)])} rows")
    
    print("\n" + "="*60)
    print("BUILDING DASHBOARD AGGREGATIONS")
    print("="*60)
    
    dashboard = {}
    
    df_gcc = df[df["Country"].isin(GCC_COUNTRIES)].copy()
    
    all_quarters = sorted(df_gcc["Quarter_Sort"].unique())
    latest_quarter_sort = all_quarters[-1] if all_quarters else None
    previous_quarter_sort = all_quarters[-2] if len(all_quarters) > 1 else None
    previous_year_quarter_sort = latest_quarter_sort - 10 if latest_quarter_sort else None  # Same quarter last year
    
    latest_quarter = df_gcc[df_gcc["Quarter_Sort"] == latest_quarter_sort]["Quarter"].iloc[0] if latest_quarter_sort else "N/A"
    previous_quarter = df_gcc[df_gcc["Quarter_Sort"] == previous_quarter_sort]["Quarter"].iloc[0] if previous_quarter_sort else "N/A"
    previous_year_quarter = df_gcc[df_gcc["Quarter_Sort"] == previous_year_quarter_sort]["Quarter"].iloc[0] if previous_year_quarter_sort else "N/A"
    
    print(f"Latest quarter: {latest_quarter}")
    print(f"Previous quarter: {previous_quarter}")
    print(f"Same quarter last year: {previous_year_quarter}")
    
    print("\n1. Building Country Overview...")
    
    country_quarterly = df_gcc.pivot_table(
        values="Units",
        index="Country",
        columns="Quarter",
        aggfunc="sum",
        fill_value=0
    )
    
    if latest_quarter in country_quarterly.columns and previous_quarter in country_quarterly.columns:
        country_quarterly["QoQ_Growth_%"] = (
            (country_quarterly[latest_quarter] - country_quarterly[previous_quarter]) / 
            country_quarterly[previous_quarter].replace(0, np.nan) * 100
        ).round(2)
    
    if latest_quarter in country_quarterly.columns and previous_year_quarter in country_quarterly.columns:
        country_quarterly["YoY_Growth_%"] = (
            (country_quarterly[latest_quarter] - country_quarterly[previous_year_quarter]) / 
            country_quarterly[previous_year_quarter].replace(0, np.nan) * 100
        ).round(2)
    
    country_quarterly["Total_All_Quarters"] = country_quarterly.drop(columns=["QoQ_Growth_%", "YoY_Growth_%"], errors='ignore').sum(axis=1)
    
    country_quarterly = country_quarterly.reset_index()
    dashboard["country_overview"] = country_quarterly.to_dict(orient="records")
    
    print(f"   Countries analyzed: {len(country_quarterly)}")
    
    print("\n2. Building Brand Performance by Country...")
    
    latest_data = df_gcc[df_gcc["Quarter_Sort"] == latest_quarter_sort]
    prev_data = df_gcc[df_gcc["Quarter_Sort"] == previous_quarter_sort]
    prev_year_data = df_gcc[df_gcc["Quarter_Sort"] == previous_year_quarter_sort]
    
    brand_country_latest = latest_data.groupby(["Country", "Brand"])["Units"].sum().reset_index()
    brand_country_latest.rename(columns={"Units": f"Units_{latest_quarter}"}, inplace=True)
    
    brand_country_prev = prev_data.groupby(["Country", "Brand"])["Units"].sum().reset_index()
    brand_country_prev.rename(columns={"Units": f"Units_{previous_quarter}"}, inplace=True)
    
    brand_country_prevyear = prev_year_data.groupby(["Country", "Brand"])["Units"].sum().reset_index()
    brand_country_prevyear.rename(columns={"Units": f"Units_{previous_year_quarter}"}, inplace=True)
    
    brand_analysis = brand_country_latest.merge(
        brand_country_prev, on=["Country", "Brand"], how="outer"
    ).merge(
        brand_country_prevyear, on=["Country", "Brand"], how="outer"
    ).fillna(0)
    
    brand_analysis["QoQ_Growth_%"] = np.where(
        brand_analysis[f"Units_{previous_quarter}"] > 0,
        ((brand_analysis[f"Units_{latest_quarter}"] - brand_analysis[f"Units_{previous_quarter}"]) / 
         brand_analysis[f"Units_{previous_quarter}"] * 100).round(2),
        np.nan
    )
    
    brand_analysis["YoY_Growth_%"] = np.where(
        brand_analysis[f"Units_{previous_year_quarter}"] > 0,
        ((brand_analysis[f"Units_{latest_quarter}"] - brand_analysis[f"Units_{previous_year_quarter}"]) / 
         brand_analysis[f"Units_{previous_year_quarter}"] * 100).round(2),
        np.nan
    )
    
    country_totals = brand_analysis.groupby("Country")[f"Units_{latest_quarter}"].transform("sum")
    brand_analysis["Market_Share_%"] = (
        (brand_analysis[f"Units_{latest_quarter}"] / country_totals.replace(0, np.nan) * 100).round(2)
    )
    
    brand_analysis["Rank"] = brand_analysis.groupby("Country")[f"Units_{latest_quarter}"].rank(
        ascending=False, method="min"
    ).astype(int)
    
    dashboard["brand_analysis"] = brand_analysis.to_dict(orient="records")
    print(f"   Brand-Country combinations: {len(brand_analysis)}")

    print("\n3. Building Country Comparison...")
    
    country_comparison = []
    for country in GCC_COUNTRIES:
        country_data = df_gcc[df_gcc["Country"] == country]
        if len(country_data) > 0:
            total_units = country_data["Units"].sum()
            latest_units = country_data[country_data["Quarter_Sort"] == latest_quarter_sort]["Units"].sum()
            
            top_brands = latest_data[latest_data["Country"] == country].groupby("Brand")["Units"].sum().nlargest(5).to_dict()
            
            num_brands = country_data["Brand"].nunique()
            
            country_comparison.append({
                "Country": country,
                "Total_Units_All_Time": int(total_units),
                f"Units_{latest_quarter}": int(latest_units),
                "Num_Brands": num_brands,
                "Top_5_Brands": top_brands,
                "Avg_Units_Per_Quarter": int(total_units / country_data["Quarter"].nunique()) if country_data["Quarter"].nunique() > 0 else 0
            })
    
    dashboard["country_comparison"] = country_comparison
    print(f"   Countries compared: {len(country_comparison)}")
    
    print("\n4. Building Quarterly Trends...")
    
    gcc_total_quarterly = df_gcc.groupby(["Year", "Q_Num", "Quarter"])["Units"].sum().reset_index()
    gcc_total_quarterly = gcc_total_quarterly.sort_values(["Year", "Q_Num"])
    
    gcc_total_quarterly["QoQ_Growth_%"] = gcc_total_quarterly["Units"].pct_change() * 100
    
    gcc_total_quarterly["Units_LY"] = gcc_total_quarterly.groupby("Q_Num")["Units"].shift(1)
    gcc_total_quarterly["YoY_Growth_%"] = (
        (gcc_total_quarterly["Units"] - gcc_total_quarterly["Units_LY"]) / 
        gcc_total_quarterly["Units_LY"].replace(0, np.nan) * 100
    ).round(2)
    
    dashboard["quarterly_trends"] = gcc_total_quarterly.to_dict(orient="records")
    print(f"   Quarters tracked: {len(gcc_total_quarterly)}")

    print("\n5. Building Brand Rankings...")
    
    brand_total_all = df_gcc.groupby("Brand").agg(
        Total_Units=("Units", "sum"),
        Countries_Present=("Country", "nunique"),
        Avg_Quarterly_Units=("Units", "mean")
    ).reset_index()
    
    brand_total_all["Rank"] = brand_total_all["Total_Units"].rank(ascending=False, method="min").astype(int)
    brand_total_all = brand_total_all.sort_values("Total_Units", ascending=False)
    
    dashboard["brand_rankings"] = brand_total_all.to_dict(orient="records")
    print(f"   Total brands: {len(brand_total_all)}")

    if "Product Category" in df_gcc.columns:
        print("\n6. Building Product Category Analysis...")
        
        category_quarterly = df_gcc.pivot_table(
            values="Units",
            index=["Country", "Product Category"],
            columns="Quarter",
            aggfunc="sum",
            fill_value=0
        ).reset_index()
        
        dashboard["category_analysis"] = category_quarterly.to_dict(orient="records")
        print(f"   Categories found: {df_gcc['Product Category'].nunique()}")
    
    print("\n" + "="*60)
    print("SAVING DASHBOARD FILES")
    print("="*60)
    
    os.makedirs(output_dir, exist_ok=True)
    
    dashboard_json_path = os.path.join(output_dir, "gcc_dashboard.json")
    with open(dashboard_json_path, "w") as f:
        json.dump(dashboard, f, indent=2, default=str)
    print(f"✓ Dashboard JSON: {dashboard_json_path}")
    
    parquet_path = os.path.join(output_dir, "gcc_full_data.parquet")
    df_gcc.to_parquet(parquet_path, index=False)
    print(f"Full data (Parquet): {parquet_path}")
    
    excel_path = os.path.join(output_dir, "gcc_dashboard.xlsx")
    with pd.ExcelWriter(excel_path, engine='openpyxl') as writer:
        df_gcc.to_excel(writer, sheet_name="Raw Data (GCC)", index=False)
        
        pd.DataFrame(dashboard["country_overview"]).to_excel(writer, sheet_name="Country Overview", index=False)
        
        pd.DataFrame(dashboard["brand_analysis"]).to_excel(writer, sheet_name="Brand Analysis", index=False)
        
        pd.DataFrame(dashboard["country_comparison"]).to_excel(writer, sheet_name="Country Comparison", index=False)
        
        pd.DataFrame(dashboard["quarterly_trends"]).to_excel(writer, sheet_name="Quarterly Trends", index=False)
        
        pd.DataFrame(dashboard["brand_rankings"]).to_excel(writer, sheet_name="Brand Rankings", index=False)
        
        if "category_analysis" in dashboard:
            pd.DataFrame(dashboard["category_analysis"]).to_excel(writer, sheet_name="Category Analysis", index=False)
    
    print(f"Excel dashboard: {excel_path}")
    
    print("\n" + "="*60)
    print("DASHBOARD SUMMARY")
    print("="*60)
    print(f"\nData Period: {df_gcc['Quarter'].min()} to {df_gcc['Quarter'].max()}")
    print(f"GCC Countries: {df_gcc['Country'].nunique()}")
    print(f"Total Brands: {df_gcc['Brand'].nunique()}")
    print(f"Total Units (GCC): {df_gcc['Units'].sum():,}")
    
    print(f"\nTop 5 Countries by Units ({latest_quarter}):")
    country_latest = latest_data.groupby("Country")["Units"].sum().sort_values(ascending=False)
    for i, (country, units) in enumerate(country_latest.head(5).items(), 1):
        print(f"   {i}. {country}: {units:,} units")
    
    print(f"\nTop 5 Brands in GCC ({latest_quarter}):")
    brand_latest = latest_data.groupby("Brand")["Units"].sum().sort_values(ascending=False)
    for i, (brand, units) in enumerate(brand_latest.head(5).items(), 1):
        print(f"   {i}. {brand}: {units:,} units")
    
    return dashboard, df_gcc


if __name__ == "__main__":
    output_dir = "."
    
    print("="*60)
    print("GCC CONSUMER PULSE - MARKET DASHBOARD BUILDER")
    print("="*60)
    
    dashboard, df_clean = build_gcc_dashboard(
        file_source=FRD_FILE_URL,
        output_dir=output_dir,
        auth_type=AUTH_TYPE
    )
    
    if dashboard is not None:
        print("\n" + "="*60)
        print("DASHBOARD BUILD COMPLETE!")
        print("="*60)
        print(f"\nFiles created in: {os.path.abspath(output_dir)}")
        print("  - gcc_dashboard.json (all aggregations)")
        print("  - gcc_full_data.parquet (cleaned GCC data)")
        print("  - gcc_dashboard.xlsx (Excel with all sheets)")
    else:
        print("\n" + "="*60)
        print("DASHBOARD BUILD FAILED")
        print("="*60)
        print("\nTry these steps:")
        print("1. Download the Excel file manually from the API")
        print("2. Save it as 'gcc_data.xlsx' in the current directory")
        print("3. Change FRD_FILE_URL to './gcc_data.xlsx'")