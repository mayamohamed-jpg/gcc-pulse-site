import os
import json
import logging
import requests
import pandas as pd
import numpy as np
from io import BytesIO
from typing import Optional, Dict

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


FRD_FILE_URL = (
    "https://frd-prod-webapps.aws.insideidc.com/ferda-rest/api?fileId=28aafb73-b4ac-4624-9d9e-a60481d750b9"
)

GCC_COUNTRIES = [
    "Saudi Arabia", "United Arab Emirates", "Qatar",
    "Kuwait", "Oman", "Bahrain", "Iraq"
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
    "United Arab Emirates": "United Arab Emirates"
}


class DataLoadError(Exception):
    """Raised when data cannot be loaded from the source."""
    pass

class ExportError(Exception):
    """Raised when saving output files fails."""
    pass


class DataLoader:
    """
    Loads raw Excel data from a URL or local file path.
    Supports bearer token, API key, and basic auth.
    """

    def __init__(self, url: str, auth_type: str = "none", token: Optional[str] = None, api_key: Optional[str] = None):
        self.url = url
        self.auth_type = auth_type
        self.token = token
        self.api_key = api_key

    def _build_headers(self) -> dict:
        """Build request headers based on auth type."""
        headers = {"User-Agent": "Mozilla/5.0"}
        if self.auth_type == "bearer_token" and self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        elif self.auth_type == "api_key" and self.api_key:
            headers["X-API-Key"] = self.api_key
        return headers

    def _get_auth(self) -> Optional[tuple]:
        """Return basic auth tuple if applicable."""
        if self.auth_type == "basic" and self.username:
            return (self.username, self.password or "")
        return None

    def load(self) -> pd.DataFrame:
        """
        Load Excel file and return as DataFrame.
        Raises DataLoadError if loading fails.
        """
        try:
            if self.url.startswith(("http://", "https://")):
                logger.info(f"Downloading from: {self.url}")
                response = requests.get(
                    self.url,
                    headers=self._build_headers(),
                    auth=self._get_auth(),
                    timeout=30,
                )
                if response.status_code != 200:
                    raise DataLoadError(
                        f"HTTP {response.status_code}: {response.text[:200]}"
                    )
                df = pd.read_excel(BytesIO(response.content), sheet_name=0)
            else:
                logger.info(f"Reading local file: {self.url}")
                df = pd.read_excel(self.url, sheet_name=0)

            logger.info(f"Loaded {len(df):,} rows | columns: {list(df.columns)}")
            return df

        except DataLoadError:
            raise
        except Exception as e:
            raise DataLoadError(f"Failed to load data: {e}") from e


class DataCleaner:
    """
    Cleans and standardizes raw data.
    Filters to GCC countries only.
    """

    def __init__(self, df: pd.DataFrame):
        self.df = df.copy()

    def _standardize_countries(self) -> None:
        """Map all country name variants to standard names."""
        self.df["Country"] = (self.df["Country"].map(COUNTRY_MAPPING).fillna(self.df["Country"]))

    def _parse_quarters(self) -> None:
        """Parse quarter string into Year, Q_Num, and Quarter_Sort columns."""
        self.df["Quarter"] = self.df["Quarter"].astype(str).str.strip()
        self.df["Year"] = self.df["Quarter"].str[:4].astype(int)
        self.df["Q_Num"] = (
            self.df["Quarter"].str[5:].str.replace("Q", "", regex=False).astype(int)
        )
        self.df["Quarter_Sort"] = self.df["Year"] * 10 + self.df["Q_Num"]

    def _fix_units(self) -> None:
        """Coerce Units to numeric, fill nulls with 0."""
        self.df["Units"] = (
            pd.to_numeric(self.df["Units"], errors="coerce").fillna(0).astype(int))

    def clean(self) -> pd.DataFrame:
        """Run all cleaning steps. Returns the full cleaned DataFrame."""
        logger.info("Cleaning and standardizing data...")
        self._standardize_countries()
        self._parse_quarters()
        self._fix_units()
        logger.info(f"Shape: {self.df.shape}")
        logger.info(f"Quarters: {self.df['Quarter'].min()} → {self.df['Quarter'].max()}")
        return self.df

    def filter_gcc(self) -> pd.DataFrame:
        """Return only GCC countries rows."""
        df_gcc = self.df[self.df["Country"].isin(GCC_COUNTRIES)].copy()
        logger.info(f"GCC rows: {len(df_gcc):,} across {df_gcc['Country'].nunique()} countries")
        return df_gcc


class AggregationBuilder:
    """
    Builds all dashboard aggregations from clean GCC data.
    Quarters are resolved once in __init__ and reused across methods.
    """

    def __init__(self, df_gcc: pd.DataFrame):
        self.df = df_gcc
        self.latest_quarter, self.prev_quarter, self.prev_year_quarter = (self._find_quarters())

        # Pre-filter quarter slices used by multiple methods
        self.latest_data = self.df[self.df["Quarter_Sort"] == self._quarter_sort(self.latest_quarter)]
        self.prev_data = self.df[self.df["Quarter_Sort"] == self._quarter_sort(self.prev_quarter)]
        self.prev_year_data = self.df[self.df["Quarter_Sort"] == self._quarter_sort(self.prev_year_quarter)]

    def _find_quarters(self) -> tuple:
        """Identify latest, previous, and same-quarter-last-year values."""
        all_sorts = sorted(self.df["Quarter_Sort"].unique())

        def sort_to_label(sort_val):
            if sort_val is None:
                return "N/A"
            match = self.df[self.df["Quarter_Sort"] == sort_val]["Quarter"]
            return match.iloc[0] if len(match) > 0 else "N/A"

        latest_sort = all_sorts[-1] if all_sorts else None
        prev_sort = all_sorts[-2] if len(all_sorts) > 1 else None
        prev_year_sort = (latest_sort - 10) if latest_sort else None

        latest = sort_to_label(latest_sort)
        prev = sort_to_label(prev_sort)
        prev_year = sort_to_label(prev_year_sort)

        logger.info(f"Latest quarter: {latest}")
        logger.info(f"Previous quarter: {prev}")
        logger.info(f"Same quarter last year: {prev_year}")

        return latest, prev, prev_year

    def _quarter_sort(self, quarter_label: str) -> Optional[int]:
        """Convert a quarter label like '2024Q1' back to its sort integer."""
        match = self.df[self.df["Quarter"] == quarter_label]["Quarter_Sort"]
        return int(match.iloc[0]) if len(match) > 0 else None

    def _growth(self, current: pd.Series, base: pd.Series) -> pd.Series:
        """Calculate percentage growth, returning NaN where base is zero."""
        return ((current - base) / base.replace(0, np.nan) * 100).round(2)

    def build_country_overview(self) -> list:
        """Pivot: countries × quarters with QoQ and YoY growth."""
        pivot = self.df.pivot_table(
            values="Units",
            index="Country",
            columns="Quarter",
            aggfunc="sum",
            fill_value=0,
        )
        lq, pq, pyq = self.latest_quarter, self.prev_quarter, self.prev_year_quarter

        if lq in pivot.columns and pq in pivot.columns:
            pivot["QoQ_Growth_%"] = self._growth(pivot[lq], pivot[pq])

        if lq in pivot.columns and pyq in pivot.columns:
            pivot["YoY_Growth_%"] = self._growth(pivot[lq], pivot[pyq])

        pivot["Total_All_Quarters"] = pivot.drop(
            columns=["QoQ_Growth_%", "YoY_Growth_%"], errors="ignore"
        ).sum(axis=1)

        result = pivot.reset_index().to_dict(orient="records")
        logger.info(f"Country overview: {len(result)} countries")
        return result

    def build_brand_analysis(self) -> list:
        """Brand units, market share, QoQ and YoY growth per country."""
        lq, pq, pyq = self.latest_quarter, self.prev_quarter, self.prev_year_quarter

        def agg(data, label):
            return (data.groupby(["Country", "Brand"])["Units"].sum().reset_index().rename(columns={"Units": f"Units_{label}"}))

        df = (
            agg(self.latest_data, lq)
            .merge(agg(self.prev_data, pq), on=["Country", "Brand"], how="outer")
            .merge(agg(self.prev_year_data, pyq), on=["Country", "Brand"], how="outer")
            .fillna(0)
        )

        df["QoQ_Growth_%"] = np.where(
            df[f"Units_{pq}"] > 0,
            self._growth(df[f"Units_{lq}"], df[f"Units_{pq}"]),
            np.nan,
        )
        df["YoY_Growth_%"] = np.where(
            df[f"Units_{pyq}"] > 0,
            self._growth(df[f"Units_{lq}"], df[f"Units_{pyq}"]),
            np.nan,
        )

        country_totals = df.groupby("Country")[f"Units_{lq}"].transform("sum")
        df["Market_Share_%"] = (
            (df[f"Units_{lq}"] / country_totals.replace(0, np.nan) * 100).round(2)
        )
        df["Rank"] = (
            df.groupby("Country")[f"Units_{lq}"]
            .rank(ascending=False, method="min")
            .astype(int)
        )

        result = df.to_dict(orient="records")
        logger.info(f"Brand analysis: {len(result)} brand-country combinations")
        return result

    def build_country_comparison(self) -> list:
        """Summary per country: totals, top 5 brands, avg per quarter."""
        result = []
        lq_sort = self._quarter_sort(self.latest_quarter)

        for country in GCC_COUNTRIES:
            country_data = self.df[self.df["Country"] == country]
            if country_data.empty:
                continue

            total_units = country_data["Units"].sum()
            latest_units = country_data[
                country_data["Quarter_Sort"] == lq_sort
            ]["Units"].sum()
            top_brands = (
                self.latest_data[self.latest_data["Country"] == country]
                .groupby("Brand")["Units"]
                .sum()
                .nlargest(5)
                .to_dict()
            )
            num_quarters = country_data["Quarter"].nunique()

            result.append({
                "Country": country,
                "Total_Units_All_Time": int(total_units),
                f"Units_{self.latest_quarter}": int(latest_units),
                "Num_Brands": country_data["Brand"].nunique(),
                "Top_5_Brands": top_brands,
                "Avg_Units_Per_Quarter": int(total_units / num_quarters) if num_quarters else 0,
            })

        logger.info(f"Country comparison: {len(result)} countries")
        return result

    def build_quarterly_trends(self) -> list:
        """GCC total units per quarter with QoQ and YoY growth."""
        trends = (
            self.df.groupby(["Year", "Q_Num", "Quarter"])["Units"]
            .sum()
            .reset_index()
            .sort_values(["Year", "Q_Num"])
        )
        trends["QoQ_Growth_%"] = trends["Units"].pct_change() * 100
        trends["Units_LY"] = trends.groupby("Q_Num")["Units"].shift(1)
        trends["YoY_Growth_%"] = self._growth(trends["Units"], trends["Units_LY"])

        result = trends.to_dict(orient="records")
        logger.info(f"Quarterly trends: {len(result)} quarters")
        return result

    def build_brand_rankings(self) -> list:
        """Overall brand rankings across all GCC, all time."""
        rankings = (
            self.df.groupby("Brand")
            .agg(
                Total_Units=("Units", "sum"),
                Countries_Present=("Country", "nunique"),
                Avg_Quarterly_Units=("Units", "mean"),
            )
            .reset_index()
        )
        rankings["Rank"] = (
            rankings["Total_Units"].rank(ascending=False, method="min").astype(int)
        )
        rankings = rankings.sort_values("Total_Units", ascending=False)

        result = rankings.to_dict(orient="records")
        logger.info(f"Brand rankings: {len(result)} brands")
        return result

    def build_category_analysis(self) -> Optional[list]:
        """Units by product category per country per quarter. None if no category column."""
        if "Product Category" not in self.df.columns:
            return None

        pivot = self.df.pivot_table(
            values="Units",
            index=["Country", "Product Category"],
            columns="Quarter",
            aggfunc="sum",
            fill_value=0,
        ).reset_index()

        result = pivot.to_dict(orient="records")
        logger.info(f"Category analysis: {self.df['Product Category'].nunique()} categories")
        return result

    def build_all(self) -> dict:
        """Run all aggregations and return complete dashboard dict."""
        logger.info("Building all aggregations...")
        dashboard = {
            "country_overview":    self.build_country_overview(),
            "brand_analysis":      self.build_brand_analysis(),
            "country_comparison":  self.build_country_comparison(),
            "quarterly_trends":    self.build_quarterly_trends(),
            "brand_rankings":      self.build_brand_rankings(),
        }
        category = self.build_category_analysis()
        if category is not None:
            dashboard["category_analysis"] = category

        return dashboard


class DashboardExporter:
    """
    Saves dashboard data to JSON, and Excel.
    """

    def __init__(self, dashboard: dict, df_gcc: pd.DataFrame, output_dir: str = "."):
        self.dashboard = dashboard
        self.df_gcc = df_gcc
        self.output_dir = output_dir
        os.makedirs(output_dir, exist_ok=True)

    def _path(self, filename: str) -> str:
        return os.path.join(self.output_dir, filename)

    def save_json(self) -> str:
        """Save dashboard dict as JSON."""
        path = self._path("gcc_dashboard.json")
        try:
            with open(path, "w") as f:
                json.dump(self.dashboard, f, indent=2, default=str)
            logger.info(f"Saved JSON: {path}")
            return path
        except Exception as e:
            raise ExportError(f"Failed to save JSON: {e}") from e

    def save_excel(self) -> str:
        """Save all aggregations as separate sheets in one Excel file."""
        path = self._path("gcc_dashboard.xlsx")
        try:
            with pd.ExcelWriter(path, engine="openpyxl") as writer:
                self.df_gcc.to_excel(writer, sheet_name="Raw Data (GCC)", index=False)

                sheets = {
                    "Country Overview":   "country_overview",
                    "Brand Analysis":     "brand_analysis",
                    "Country Comparison": "country_comparison",
                    "Quarterly Trends":   "quarterly_trends",
                    "Brand Rankings":     "brand_rankings",
                    "Category Analysis":  "category_analysis",
                }
                for sheet_name, key in sheets.items():
                    if key in self.dashboard:
                        pd.DataFrame(self.dashboard[key]).to_excel(
                            writer, sheet_name=sheet_name, index=False
                        )

            logger.info(f"Saved Excel: {path}")
            return path
        except Exception as e:
            raise ExportError(f"Failed to save Excel: {e}") from e

    def export_all(self) -> None:
        """Save all three output formats."""
        self.save_json()
        self.save_excel()


class GCCDashboardPipeline:
    """
    Orchestrates the full ETL pipeline:
    Load → Clean → Aggregate → Export → Summary
    """

    def __init__(
        self,
        url: str = FRD_FILE_URL,
        output_dir: str = ".",
        auth_type: str = "none",
        **auth_params,
    ):
        self.url = url
        self.output_dir = output_dir
        self.auth_type = auth_type
        self.auth_params = auth_params

    def _print_summary(
        self, df_gcc: pd.DataFrame, builder: AggregationBuilder
    ) -> None:
        """Print final run summary."""
        lq = builder.latest_quarter
        logger.info("=" * 50)
        logger.info("PIPELINE COMPLETE")
        logger.info("=" * 50)
        logger.info(f"Period:    {df_gcc['Quarter'].min()} → {df_gcc['Quarter'].max()}")
        logger.info(f"Countries: {df_gcc['Country'].nunique()}")
        logger.info(f"Brands:    {df_gcc['Brand'].nunique()}")
        logger.info(f"Units:     {df_gcc['Units'].sum():,}")

        logger.info(f"\nTop 5 Countries ({lq}):")
        top_countries = (
            builder.latest_data.groupby("Country")["Units"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
        )
        for i, (country, units) in enumerate(top_countries.items(), 1):
            logger.info(f"  {i}. {country}: {units:,}")

        logger.info(f"\nTop 5 Brands ({lq}):")
        top_brands = (
            builder.latest_data.groupby("Brand")["Units"]
            .sum()
            .sort_values(ascending=False)
            .head(5)
        )
        for i, (brand, units) in enumerate(top_brands.items(), 1):
            logger.info(f"  {i}. {brand}: {units:,}")

    def run(self) -> None:
        """Execute full pipeline."""
        logger.info("=" * 50)
        logger.info("GCC CONSUMER PULSE — ETL PIPELINE STARTING")
        logger.info("=" * 50)

        loader = DataLoader(self.url, self.auth_type, **self.auth_params)
        raw_df = loader.load()

        cleaner = DataCleaner(raw_df)
        cleaner.clean()
        df_gcc = cleaner.filter_gcc()

        builder = AggregationBuilder(df_gcc)
        dashboard = builder.build_all()

        exporter = DashboardExporter(dashboard, df_gcc, self.output_dir)
        exporter.export_all()

        self._print_summary(df_gcc, builder)


if __name__ == "__main__":
    pipeline = GCCDashboardPipeline(
        url=FRD_FILE_URL,
        output_dir=".",
        auth_type="none",
    )
    pipeline.run()