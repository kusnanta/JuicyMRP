"""data/loader.py — load and validate sales + BOM from CSV files."""
from __future__ import annotations

import io
from pathlib import Path
from typing import Union

import pandas as pd
from loguru import logger

FileInput = Union[str, Path, io.IOBase]


def _read(src: FileInput) -> pd.DataFrame:
    if isinstance(src, (str, Path)):
        return pd.read_csv(src)
    return pd.read_csv(src)


def load_sales(src: FileInput) -> pd.DataFrame:
    """
    Load historical sales CSV.

    Expected columns: date, product_name, sales_qty
    Returns a clean, sorted DataFrame.
    """
    df = _read(src)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required = {"date", "product_name", "sales_qty"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"Sales CSV kolom tidak lengkap: {missing}\n"
            f"Dibutuhkan: date, product_name, sales_qty\n"
            f"Ditemukan: {list(df.columns)}"
        )

    df["date"] = pd.to_datetime(df["date"], errors="coerce")
    df["sales_qty"] = pd.to_numeric(df["sales_qty"], errors="coerce").fillna(0)
    df["product_name"] = df["product_name"].astype(str).str.strip()

    bad = df["date"].isna().sum()
    if bad:
        logger.warning("Membuang {} baris dengan tanggal tidak valid.", bad)
    df = df.dropna(subset=["date"])
    df = df[df["sales_qty"] >= 0]
    df = df.sort_values(["product_name", "date"]).reset_index(drop=True)

    logger.info(
        "Sales loaded: {} baris, {} produk, {} → {}",
        len(df),
        df["product_name"].nunique(),
        str(df["date"].min().date()),
        str(df["date"].max().date()),
    )
    return df


def load_bom(src: FileInput) -> pd.DataFrame:
    """
    Load BOM/recipe CSV.

    Expected columns: product_name, material, component_qty
    """
    df = _read(src)
    df.columns = [c.strip().lower().replace(" ", "_") for c in df.columns]

    required = {"product_name", "material", "component_qty"}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(
            f"BOM CSV kolom tidak lengkap: {missing}\n"
            f"Dibutuhkan: product_name, material, component_qty\n"
            f"Ditemukan: {list(df.columns)}"
        )

    df["product_name"] = df["product_name"].astype(str).str.strip()
    df["material"] = df["material"].astype(str).str.strip()
    df["component_qty"] = pd.to_numeric(df["component_qty"], errors="coerce").fillna(0)
    df = df[df["component_qty"] > 0].reset_index(drop=True)

    logger.info(
        "BOM loaded: {} entri, {} produk, {} material.",
        len(df),
        df["product_name"].nunique(),
        df["material"].nunique(),
    )
    return df
