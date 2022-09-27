from pathlib import Path

import numpy as np
import pandas as pd
import scipy.stats
from ab_testing.constants import DISTRIBUTIONS


class FitDistribution:
    def __init__(self, fname: str, data_dir_str: str = "processed_data"):
        self.data_dir_path = Path(data_dir_str)
        self.fname = fname

        data_dir_path = Path(data_dir_str)
        if not data_dir_path.exists():
            data_dir_path.mkdir(parents=True, exist_ok=True)

    def fit(self, data: pd.DataFrame, target: str) -> str:

        df = pd.DataFrame(columns=["distribution", "AIC", "BIC"])

        dists = []
        aic = []
        bic = []

        for com_dist in DISTRIBUTIONS:
            dist = eval("scipy.stats." + com_dist)
            params = dist.fit(data[target].values)
            # pdf_fitted = dist.pdf(data[target].values, *params)

            logLik = np.sum(dist.logpdf(data["total_wins_spend"].values, *params))
            k = len(params[:])
            n = len(data["total_wins_spend"].values)
            dists.append(com_dist)
            aic.append(2 * k - 2 * logLik)
            bic.append(k * np.log(n) - 2 * logLik)

        df["distribution"] = dists
        df["AIC"] = aic
        df["BIC"] = bic
        df.sort_values(by="AIC", inplace=True)
        df.reset_index(drop=True, inplace=True)

        df.to_parquet(self.data_dir_path / self.fname)

        return df["distribution"].head(1).values[0]
