import json
import sqlite3
import pandas as pd
from typing import List, Dict, Any, Optional

class DataExporter:
    """Exports scraped lead dataset into CSV, Excel, JSON, and SQLite formats."""

    @staticmethod
    def to_dataframe(leads: List[Dict[str, Any]]) -> pd.DataFrame:
        if not leads:
            return pd.DataFrame()
        return pd.DataFrame(leads)

    @staticmethod
    def to_csv(leads: List[Dict[str, Any]], filepath: str) -> str:
        df = DataExporter.to_dataframe(leads)
        df.to_csv(filepath, index=False, encoding='utf-8-sig')
        return filepath

    @staticmethod
    def to_excel(leads: List[Dict[str, Any]], filepath: str) -> str:
        df = DataExporter.to_dataframe(leads)
        df.to_excel(filepath, index=False, engine='openpyxl')
        return filepath

    @staticmethod
    def to_json(leads: List[Dict[str, Any]], filepath: str) -> str:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(leads, f, indent=2, ensure_ascii=False)
        return filepath

    @staticmethod
    def to_sqlite(leads: List[Dict[str, Any]], db_filepath: str, table_name: str = "leads") -> str:
        df = DataExporter.to_dataframe(leads)
        conn = sqlite3.connect(db_filepath)
        df.to_sql(table_name, conn, if_exists='replace', index=False)
        conn.close()
        return db_filepath
