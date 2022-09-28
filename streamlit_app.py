import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats
from scipy.stats import norm
import altair as alt

import matplotlib as plt
import seaborn as sns
import arviz as az
from pathlib import Path

from ab_testing.constants import client_name, target_col
from ab_testing.distribution_fit.fit_distribution import FitDistribution
from ab_testing.predictions.produce_predictions import ProducePredictions

st.set_page_config(
    page_title="AB Testing", page_icon="📊", initial_sidebar_state="expanded", layout="wide"
)

st.write(
    """
# 📊 A/B Testing
Upload your experiment results to see the performance of your A/B test.
"""
)

uploaded_file = st.file_uploader("Upload Parquet File", type=".p")

use_example_file = st.checkbox(
    "Use example file", False, help="Use in-built example file to demo the app"
)

ab_default = None
result_default = None

# If Parquet is not uploaded and checkbox is filled, use values from the example file
# and pass them down to the next if block
if use_example_file:
    uploaded_file = "bingo_aloha_data.p"
    ab_default = ["test_group"]
    result_default = ["total_wins_spend"]

if uploaded_file:
    df = pd.read_parquet(uploaded_file)
    
    st.markdown("### Data Preview")
    st.dataframe(df.head())

    st.markdown("### Select Columns for Analysis")
    with st.form(key="my_form"):
        ab = st.multiselect(
            "A/B column",
            options=df.columns,
            help="Select which column refers to your A/B testing labels.",
            default=ab_default,
        )
        result = st.multiselect(
            "Result column",
            options=df.columns,
            help="Select which column shows the result of the test.",
            default=result_default,
        )

        if ab:
            control = df[ab[0]].unique()[0]
            treatment = df[ab[0]].unique()[1]
            decide = st.radio(
                f"Is *{treatment}* Group B?",
                options=["Yes", "No"],
                help="Select yes if this is group B (or the treatment group) from your test.",
            )
            if decide == "No":
                control, treatment = treatment, control

        with st.expander("Adjust test parameters"):
            st.markdown("### Parameters")
            st.slider(
                "Posterior Creadibility (HDI)",
                min_value=0.80,
                max_value=0.99,
                value=0.90,
                step=0.01,
                key="hdi",
                help=" Values of θ that have at least some minimal level of posterior credibility, such that the total probability of all such θ values is HDI% ",
            )
            # Add bullet points of data distribution options with optimal distribution in bold...

        submit_button = st.form_submit_button(label="Submit")

    if not ab or not result:
        st.warning("Please select both an **A/B column** and a **Result column**.")
        st.stop()

    # to find if example file was used -> type(uploaded_file) == str <- is only true for example file
    name = (
        "bingo_aloha_data.p" if isinstance(uploaded_file, str) else uploaded_file.name
    )
    st.write("")
    st.write("## AB Test Performance For:\n", name)
    st.write("")
    
    # Create test results:
    initial_data = df
    result = ProducePredictions()
    results_conversion = result.produce_results_conversion(initial_data)
    results_revenue = result.produce_results_revenue('lognorm', initial_data)
    # change here once manual selection works
    results_posterior_sample = result._produce_results_lognorm_dist_carry_value(initial_data)
    
    # Set up metrics:
    post_sample_A      = results_posterior_sample[1]
    post_sample_B      = results_posterior_sample[0]
    post_sample_uplift = (post_sample_B - post_sample_A) / post_sample_A
    hdi_A              = az.hdi(post_sample_A, hdi_prob=st.session_state.hdi)
    hdi_B              = az.hdi(post_sample_B, hdi_prob=st.session_state.hdi)
    hdi_diff           = az.hdi(post_sample_uplift, hdi_prob=st.session_state.hdi)
    
    # Draw up tables:
    st.write("")
    row1_space1, row1_col1, row1_space2, row1_col2, row1_space3 = st.columns(
        (0.1, 1, 0.1, 1, 0.1)
    )
    with row1_col1:
        st.metric(
            "Delta ARPUs",
            value = "%.4f€" % (results_revenue[0]['avg_values'] - results_revenue[1]['avg_values']),
        )
    with row1_col2:
        st.metric(
            "Delta Conversion",
            value = "%.2f%%" % ((results_conversion[0]['positive_rate'] - results_conversion[1]['positive_rate']) * 100),
        )
    
    st.write("")
    plt.use("agg")
    _lock = plt.backends.backend_agg.RendererAgg.lock
    sns.set_style("darkgrid")
    
    # Set up plots:
    row2_space1, row2_col1, row2_space2, row2_col2, row2_space3 = st.columns(
        (0.1, 1, 0.1, 1, 0.1)
    )
    
    with row2_col1, _lock:
        st.subheader("Distribution of posterior ARPU A & B")
        fig = plt.figure.Figure()
        ax = fig.add_subplot(111)
        fig_temp = sns.kdeplot(post_sample_A, color="blue", ax = ax)
        fig_temp = sns.kdeplot(post_sample_B, color="red", ax = ax)
        l1 = fig_temp.lines[0]
        l2 = fig_temp.lines[1]
        x1 = l1.get_xydata()[:,0]
        x2 = l2.get_xydata()[:,0]
        y1 = l1.get_xydata()[:,1]
        y2 = l2.get_xydata()[:,1]
        x1_new = x1[[all(tup) for tup in zip(list(x1 >= hdi_A[0]), list(x1 <= hdi_A[1]))]]
        x2_new = x2[[all(tup) for tup in zip(list(x2 >= hdi_B[0]), list(x2 <= hdi_B[1]))]]
        y1_new = y1[[all(tup) for tup in zip(list(x1 >= hdi_A[0]), list(x1 <= hdi_A[1]))]]
        y2_new = y2[[all(tup) for tup in zip(list(x2 >= hdi_B[0]), list(x2 <= hdi_B[1]))]]
        #plt.pyplot.fill_between(x1_new, y1_new, color="blue", alpha=0.3)
        #plt.pyplot.fill_between(x2_new, y2_new, color="red", alpha=0.3)
        ax.fill_between(x1_new, y1_new, color="blue", alpha=0.3)
        ax.fill_between(x2_new, y2_new, color="red", alpha=0.3)
        plt.pyplot.legend(labels=['Control','Personalised'])
        st.pyplot(fig)
#     fig_temp = sns.kdeplot(post_sample_A, color="blue")
#     fig_temp = sns.kdeplot(post_sample_B, color="red")
#     l1 = fig_temp.lines[0]
#     l2 = fig_temp.lines[1]
#     x1 = l1.get_xydata()[:,0]
#     x2 = l2.get_xydata()[:,0]
#     y1 = l1.get_xydata()[:,1]
#     y2 = l2.get_xydata()[:,1]
#     x1_new = x1[[all(tup) for tup in zip(list(x1 >= hdi_A[0]), list(x1 <= hdi_A[1]))]]
#     x2_new = x2[[all(tup) for tup in zip(list(x2 >= hdi_B[0]), list(x2 <= hdi_B[1]))]]
#     y1_new = y1[[all(tup) for tup in zip(list(x1 >= hdi_A[0]), list(x1 <= hdi_A[1]))]]
#     y2_new = y2[[all(tup) for tup in zip(list(x2 >= hdi_B[0]), list(x2 <= hdi_B[1]))]]
#     plt.pyplot.fill_between(x1_new, y1_new, color="blue", alpha=0.3)
#     plt.pyplot.fill_between(x2_new, y2_new, color="red", alpha=0.3)
#     plt.pyplot.title('Distribution of ARPU A & B')
#     plt.pyplot.legend(labels=['Control','Personalised'])
#     st.pyplot(fig1)

    with row2_col2, _lock:
        st.subheader("Apporximate Distribution of Uplifts")
        fig2 = plt.figure.Figure()
        ax2 = fig2.add_subplot(111)
        fig_temp2 = sns.kdeplot(post_sample_uplift, color="purple", ax = ax2)
        l = fig_temp2.lines[0]
        x = l.get_xydata()[:,0]
        y = l.get_xydata()[:,1]
        x_new = x[[all(tup) for tup in zip(list(x >= hdi_diff[0]), list(x <= hdi_diff[1]))]]
        y_new = y[[all(tup) for tup in zip(list(x >= hdi_diff[0]), list(x <= hdi_diff[1]))]]
        ax2.xaxis.set_major_formatter(plt.ticker.PercentFormatter())
        #plt.pyplot.fill_between(x_new, y_new, color="purple", alpha=0.3)
        ax2.fill_between(x_new, y_new, color="purple", alpha=0.3)
        st.pyplot(fig2)
    
#     fig2 = plt.pyplot.figure(figsize=(12, 6))
#     fig_temp = sns.kdeplot(post_sample_uplift, color="purple")
#     l = fig_temp.lines[0]
#     x = l.get_xydata()[:,0]
#     y = l.get_xydata()[:,1]
#     x_new = x[[all(tup) for tup in zip(list(x >= hdi_diff[0]), list(x <= hdi_diff[1]))]]
#     y_new = y[[all(tup) for tup in zip(list(x >= hdi_diff[0]), list(x <= hdi_diff[1]))]]
#     plt.pyplot.fill_between(x_new, y_new, color="purple", alpha=0.3)
#     plt.pyplot.title('Apporximate Distribution of Uplifts')
#     st.pyplot(fig2)

    # Set up end tables:
    row3_space1, row3_col1, row3_space2, row3_col2, row3_space3 = st.columns(
        (0.1, 1, 0.1, 1, 0.1)
    )

    # Table1
    output_df = pd.DataFrame(columns=["Metric", "Conversion", "Revenue"])
    output_df["Metric"] = ["P( P > C)", "E( loss | P > C)", "E( loss | C > P)"]
    output_df["Conversion"] = [
        "%.4f%%" % (results_conversion[0]["prob_being_best"] * 100),
        "%.4f%%" % (results_conversion[0]["expected_loss"] * 100),
        "%.4f%%" % (results_conversion[1]["expected_loss"] * 100),
    ]
    output_df["Revenue"] = [
        "%.4f%%" % (results_revenue[0]["prob_being_best"] * 100),
        "%.4f%%" % (results_revenue[0]["expected_loss"] * 100),
        "%.4f%%" % (results_revenue[1]["expected_loss"] * 100),
    ]
    output_df = output_df.set_index('Metric')
    table1 = row3_col1.write(output_df)

    # Table2
    output_df2 = pd.DataFrame(columns=["Metric", "Control", "Personalised", "Personalised-Control"])
    output_df2["Metric"] = ["sample size", "conversion", "ARPU", "ARPPU", "95% HDI"]
    output_df2["Control"] = [
        "%d" % (results_revenue[1]['totals']),
        "%.2f%%" % (results_conversion[1]['positive_rate'] * 100),
        "%.4f€" % (results_revenue[1]['avg_values']),
        "%.4f€" % (results_revenue[1]['avg_positive_values']),
        "[%.2f€, %.2f€]" % (hdi_A[0], hdi_A[1]),
    ]
    output_df2["Personalised"] = [
        "%d" % (results_revenue[0]['totals']),
        "%.2f%%" % (results_conversion[0]['positive_rate'] * 100),
        "%.4f€" % (results_revenue[0]['avg_values']),
        "%.4f€" % (results_revenue[0]['avg_positive_values']),
        "[%.2f€, %.2f€]" % (hdi_B[0], hdi_B[1]),
    ]
    output_df2["Personalised-Control"] = [
        np.NAN,
        "%.2f%%" % ((results_conversion[0]['positive_rate'] - results_conversion[1]['positive_rate']) * 100),
        "%.4f€" % (results_revenue[0]['avg_values'] - results_revenue[1]['avg_values']),
        "%.4f€" % (results_revenue[0]['avg_positive_values'] - results_revenue[1]['avg_positive_values']),
        "[%.2f€, %.2f€]" % (hdi_diff[0], hdi_diff[1]),
    ]
    output_df2 = output_df2.set_index('Metric')
    table2 = row3_col2.write(output_df2)
