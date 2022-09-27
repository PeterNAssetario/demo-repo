import streamlit as st
import pandas as pd
import numpy as np
import scipy.stats
from scipy.stats import norm
import altair as alt


#import matplotlib as plt
#import seaborn as sns
import arviz as az
from pathlib import Path
#%matplotlib inline

from ab_testing.constants import client_name, target_col
from ab_testing.distribution_fit.fit_distribution import FitDistribution
from ab_testing.predictions.produce_predictions import ProducePredictions

st.set_page_config(
    page_title="A/B Testing App", page_icon="📊", initial_sidebar_state="expanded"
)

def conversion_rate(conversions, visitors):
    return (conversions / visitors) * 100

def lift(cra, crb):
    return ((crb - cra) / cra) * 100

def std_err(cr, visitors):
    return np.sqrt((cr / 100 * (1 - cr / 100)) / visitors)

def std_err_diff(sea, seb):
    return np.sqrt(sea ** 2 + seb ** 2)

def z_score(cra, crb, error):
    return ((crb - cra) / error) / 100


def p_value(z, hypothesis):
    if hypothesis == "One-sided" and z < 0:
        return 1 - norm().sf(z)
    elif hypothesis == "One-sided" and z >= 0:
        return norm().sf(z) / 2
    else:
        return norm().sf(z)


def significance(alpha, p):
    return "YES" if p < alpha else "NO"


def plot_chart(df):
    chart = (
        alt.Chart(df)
        .mark_bar(color="#61b33b")
        .encode(
            x=alt.X("Group:O", axis=alt.Axis(labelAngle=0)),
            y=alt.Y("Conversion:Q", title="Conversion rate (%)"),
            opacity="Group:O",
        )
        .properties(width=500, height=500)
    )
    chart_text = chart.mark_text(
        align="center", baseline="middle", dy=-10, color="black"
    ).encode(text=alt.Text("Conversion:Q", format=",.3g"))
    return st.altair_chart((chart + chart_text).interactive())

def style_negative(v, props=""):
    return props if v < 0 else None

def style_p_value(v, props=""):
    return np.where(v < st.session_state.alpha, "color:green;", props)

def calculate_significance(
    conversions_a, conversions_b, visitors_a, visitors_b, hypothesis, alpha
):
    st.session_state.cra = conversion_rate(int(conversions_a), int(visitors_a))
    st.session_state.crb = conversion_rate(int(conversions_b), int(visitors_b))
    st.session_state.uplift = lift(st.session_state.cra, st.session_state.crb)
    st.session_state.sea = std_err(st.session_state.cra, float(visitors_a))
    st.session_state.seb = std_err(st.session_state.crb, float(visitors_b))
    st.session_state.sed = std_err_diff(st.session_state.sea, st.session_state.seb)
    st.session_state.z = z_score(
        st.session_state.cra, st.session_state.crb, st.session_state.sed
    )
    st.session_state.p = p_value(st.session_state.z, st.session_state.hypothesis)
    st.session_state.significant = significance(
        st.session_state.alpha, st.session_state.p
    )

st.write(
    """
# 📊 A/B Testing
Upload your experiment results to see the significance of your A/B test.
"""
)

uploaded_file = st.file_uploader("Upload Parquet", type=".p")

use_example_file = st.checkbox(
    "Use example file", False, help="Use in-built example file to demo the app"
)

ab_default = None
result_default = None

# If CSV is not uploaded and checkbox is filled, use values from the example file
# and pass them down to the next if block
if use_example_file:
    uploaded_file = "bingo_aloha_data.p"
    ab_default = ["test_group"]
    result_default = ["total_wins_spend"]

if uploaded_file:
    df = pd.read_parquet(uploaded_file)
    
    st.markdown("### Data preview")
    st.dataframe(df.head())

    st.markdown("### Select columns for analysis")
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
            #visitors_a = df[ab[0]].value_counts()[control]
            #visitors_b = df[ab[0]].value_counts()[treatment]


        if result:
            conversions_a = (
                df[[ab[0], result[0]]].groupby(ab[0]).agg("sum")[result[0]][control]
            )
            conversions_b = (
                df[[ab[0], result[0]]].groupby(ab[0]).agg("sum")[result[0]][treatment]
            )

        with st.expander("Adjust test parameters"):
            st.markdown("### Parameters")
            st.slider(
                "Posterior Creadibility (HDI)",
                min_value=0.80,
                max_value=0.99,
                value=0.90,
                step=0.01,
                key="HDI",
                help=" Values of θ that have at least some minimal level of posterior credibility, such that the total probability of all such θ values is HDI% ",
            )

        submit_button = st.form_submit_button(label="Submit")

    if not ab or not result:
        st.warning("Please select both an **A/B column** and a **Result column**.")
        st.stop()

    # type(uploaded_file) == str, means the example file was used
    name = (
        "bingo_aloha_data.p" if isinstance(uploaded_file, str) else uploaded_file.name
    )
    st.write("")
    st.write("## Results for A/B test from ", name)
    st.write("")
    
    # Create test results:
    result = ProducePredictions()
    results_conversion = result.produce_results_conversion(initial_data)
    results_revenue = result.produce_results_revenue('lognorm', initial_data)
    results_posterior_sample = result._produce_results_lognorm_dist_carry_value(initial_data)
    
    # Obtain the metrics to display
    #calculate_significance(
    #    conversions_a,
    #    conversions_b,
    #    visitors_a,
    #    visitors_b,
    #    st.session_state.hypothesis,
    #    st.session_state.alpha,
    #)
    
    # Set up metrics:
    post_sample_A      = results_posterior_sample[1]
    post_sample_B      = results_posterior_sample[0]
    post_sample_uplift = (post_sample_B - post_sample_A) / post_sample_A
    hdi_A              = az.hdi(post_sample_A, hdi_prob=st.session_state.alpha)
    hdi_B              = az.hdi(post_sample_B, hdi_prob=st.session_state.alpha)
    hdi_diff           = az.hdi(diff_post_sample, hdi_prob=st.session_state.alpha)
    
    mcol1, mcol2 = st.columns(2)

    # Use st.metric to diplay difference in conversion rates
    with mcol1:
        st.metric(
            "Delta ARPUs",
            value = "%.4f€" % (results_revenue[0]['avg_values'] - results_revenue[1]['avg_values']),
        )
    # Display whether or not A/B test result is statistically significant
    with mcol2:
        st.metric(
            "Delta Conversion",
            value = "%.2f%%" % ((results_conversion[0]['positive_rate'] - results_conversion[1]['positive_rate']) * 100),
        )
    
    # Create a single-row, two-column DataFrame to use in bar chart
    results_df = pd.DataFrame(
        {
            "Group": ["Control", "Treatment"],
            "Conversion": [st.session_state.cra, st.session_state.crb],
        }
    )
    st.write("")
    st.write("")

    # Plot bar chart of conversion rates
    plot_chart(results_df)

    ncol1, ncol2 = st.columns([2, 1])

    table = pd.DataFrame(
        {
            "Converted": [conversions_a, conversions_b],
            "Total": [visitors_a, visitors_b],
            "% Converted": [st.session_state.cra, st.session_state.crb],
        },
        index=pd.Index(["Control", "Treatment"]),
    )

    # Format "% Converted" column values to 3 decimal places
    table1 = ncol1.write(table.style.format(formatter={("% Converted"): "{:.3g}%"}))

    metrics = pd.DataFrame(
        {
            "p-value": [st.session_state.p],
            "z-score": [st.session_state.z],
            "uplift": [st.session_state.uplift],
        },
        index=pd.Index(["Metrics"]),
    )

    # Color negative values red; color significant p-value green and not significant red
    table2 = ncol1.write(
        metrics.style.format(
            formatter={("p-value", "z-score"): "{:.3g}", ("uplift"): "{:.3g}%"}
        )
        .applymap(style_negative, props="color:red;")
        .apply(style_p_value, props="color:red;", axis=1, subset=["p-value"])
    )
