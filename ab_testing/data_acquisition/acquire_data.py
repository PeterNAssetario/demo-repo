from pathlib import Path

import pandas as pd
from ab_testing.constants import client_name
from ab_testing.data_acquisition.sql_queries.queries_all_clients import (
    query_bingo_aloha,
    query_homw,
    query_idle_mafia,
    query_knighthood,
    query_spongebob,
    query_terra_genesis,
    query_ultimex,
)
from ml_lib.feature_store import configure_offline_feature_store
from ml_lib.feature_store.offline.client import FeatureStoreOfflineClient

configure_offline_feature_store(workgroup="development", catalog_name="production")

queries_dict = {
    "bingo_aloha": query_bingo_aloha,
    "homw": query_homw,
    "idle_mafia": query_idle_mafia,
    "knighthood": query_knighthood,
    "spongebob": query_spongebob,
    "terra_genesis": query_terra_genesis,
    "ultimex": query_ultimex,
}


class AcquireData:
    def __init__(self, client: str, fname: str, data_dir_str: str = "raw_data"):
        self.client = client
        self.fname = fname
        self.data_dir_path = Path(data_dir_str)

        if not self.data_dir_path.exists():
            self.data_dir_path.mkdir(parents=True, exist_ok=True)

    def acquire_data(self) -> pd.DataFrame:

        data = self._read_if_exists()

        if data.empty:
            if client_name in queries_dict.items():
                data = FeatureStoreOfflineClient.run_athena_query_pandas(queries_dict[client_name])
            else:
                raise ValueError(f"Client name {client_name} not found.")

        data.to_parquet(self.data_dir_path / self.fname)

        return data

    def _read_if_exists(self) -> pd.DataFrame:

        if (self.data_dir_path / self.fname).exists():
            df = pd.read_parquet(self.data_dir_path / self.fname)
        else:
            df = pd.DataFrame()

        return df
