# AB-testing
Assetario repository regarding AB testing setup

How to use the repo:

Check out exploration.ipynb notebook to explore empirical distribution and find out what known theoretical disgtribution fits the data the best based on AIC / BIC, graphical evidence and Kolmogorov-Smirnov test.
MCMC simulation using pymc3 library are performed to compare personal and control group.

Run main.py to get the results for chosen client, Bernoulli distribution for conversions and lognormal distribution for revenues. There are three steps in the pipeline:

A. Data acquisition - implemented for all existing clients.
B. Distribution fit - Bernoulli distribution for the conversions and lognormal distribution for the revenues.
C. Produce predictions - probability for the P being the best with the expected losses in both cases for conversions and revenue.