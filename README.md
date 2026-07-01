# PM2.5 and Pediatric Asthma in the Philippines

Satellite-Derived PM2.5 Exposure and Pediatric Asthma Prevalence Across Philippine Regions, 2013–2022: A Subnational Ecological Panel Analysis

Hertzan D. Alquizola II — Lee County High School, Leesburg, GA
Independent research targeting Regeneron Science Talent Search + peer-reviewed publication


## What this study does

This project examines whether annual changes in satellite-derived PM2.5 concentrations are associated with pediatric asthma prevalence across 17 Philippine administrative regions from 2013 to 2022.

The short answer: a very strong cross-sectional correlation (Pearson r = +0.887) between PM2.5 and asthma prevalence turns out to be almost entirely a between-region artifact — polluted regions are also more urbanized and have more diagnostic capacity. Once two-way fixed effects remove that structural confounding, no robust within-region association remains. The 1.5% within-region variance in GBD-modeled asthma prevalence explains why. This is the paper's main finding: a methodological lesson about ecological epidemiology, not a failure to find an effect.


## Data sources

ACAG V6.GL.02.04 (satpm.org) — Annual satellite PM2.5 in µg/m³, 2013–2022 — data/raw/acag/Annual-selected/

GBD 2023 Results Tool (IHME) — Pediatric asthma prevalence, ages 5–14, subnational Philippines — data/raw/gbd/

GADM level-1 shapefiles — Philippine region boundaries for area-weighting — data/raw/shapefiles/


## How to reproduce the analysis

Install dependencies:

pip install pandas numpy matplotlib seaborn scipy statsmodels linearmodels jupyter geopandas xarray shapely netCDF4

Then run the four scripts in order:

python aggregate_gbd_provinces.py
python process_acag_pm25.py
python run_analysis.py
python generate_figures.py

Outputs land in data/processed/ and outputs/


## Key results

n = 170 region-year observations (17 regions x 10 years)
PM2.5: mean 14.72 +/- 3.52 µg/m³; 34.1% of region-years exceeded WHO guideline of 15 µg/m³
Pooled Pearson r = +0.887 (p < 0.0001) — strong but driven by between-region confounding
Variance decomposition: 98.5% of asthma prevalence variation is between-region structural; only 1.5% is within-region temporal
Two-way fixed effects β = −2.554 (SE = 0.825, p = 0.002, within-R² = 0.080) — no robust within-region signal
First differences r = +0.199 (p = 0.014) — weak positive, consistent with null


## Repository structure

pm10-asthma-davao/
├── data/
│   ├── raw/
│   │   ├── acag/
│   │   ├── gbd/
│   │   └── shapefiles/
│   └── processed/
│       ├── panel_merged.csv
│       ├── asthma_regional_panel.csv
│       └── pm25_regional_panel.csv
├── outputs/
│   ├── figures/
│   └── tables/
├── notebooks/
├── aggregate_gbd_provinces.py
├── process_acag_pm25.py
├── run_analysis.py
├── generate_figures.py
├── variance_check.py
└── requirements.txt


## Citations

ACAG data: Shen S, Li C, van Donkelaar A, et al. Enhancing Global Estimation of Fine Particulate Matter Concentrations by Including Geophysical a Priori Information in Deep Learning. ACS ES&T Air. 2024. DOI: 10.1021/acsestair.3c00054

GBD data: Global Burden of Disease Collaborative Network. GBD 2023 Results. Seattle: IHME, 2024. https://vizhub.healthdata.org/gbd-results/


## Note on repo history

Earlier folders (data/raw/cchain, data/raw/emb) and notebooks reflect abandoned earlier phases — a Davao-only PM10 study using CCHAIN surveillance data and a national 10-point time series. Both were superseded by the current regional panel. They are kept for transparency but are not part of the current analysis.
