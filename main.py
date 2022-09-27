import pandas as pd

from ab_testing.constants import client_name, target_col
from ab_testing.data_acquisition.acquire_data import AcquireData
from ab_testing.distribution_fit.fit_distribution import FitDistribution
from ab_testing.predictions.produce_predictions import ProducePredictions

acquire_initial_data = AcquireData(client=client_name, fname=f"{client_name}_data.p")
initial_data = acquire_initial_data.acquire_data()

fit_dist = FitDistribution(fname=f"{client_name}_distribution_fit.p")
best_distribution = fit_dist.fit(initial_data.loc[initial_data[target_col] > 0], target_col)

result = ProducePredictions()
results_conversion = result.produce_results_conversion(initial_data)
results_revenue = result.produce_results_revenue(best_distribution, initial_data)

output_df = pd.DataFrame(columns=["Metric", "Conversion", "Revenue"])
output_df["Metric"] = ["P( P > C)", "E( loss | P > C)", "E( loss | C > P)"]
output_df["Conversion"] = [
    results_conversion[0]["prob_being_best"],
    results_conversion[0]["expected_loss"],
    results_conversion[1]["expected_loss"],
]
output_df["Revenue"] = [results_revenue[0]["prob_being_best"], results_revenue[0]["expected_loss"], results_revenue[1]["expected_loss"]]

print(f"For client {client_name} data follows {best_distribution} distribution.")
print(output_df)
