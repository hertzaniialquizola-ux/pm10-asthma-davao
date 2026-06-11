# PM10 & Pediatric Asthma in Davao City (2013–2022)

**Author:** Hertzan D. Alquizola II  
**Affiliation:** Lee County High School | Independent Student Researcher  
**Status:** In Progress

---

## Research Question

> Does seasonal variation in PM10 concentrations in Davao City, Philippines significantly correlate with asthma prevalence among school-age children (ages 5–12) from 2013–2022, after controlling for socioeconomic factors?

---

## Repository Structure

```
pm10-asthma-davao/
│
├── data/
│   ├── raw/              ← Original downloaded datasets (DO NOT EDIT)
│   │   ├── cchain/       ← Project CCHAIN data files (.csv)
│   │   └── emb/          ← EMB-XI PM10 reports (PDFs + any CSVs)
│   └── processed/        ← Cleaned, merged datasets your code produces
│
├── notebooks/
│   └── 01_analysis.ipynb ← Main Jupyter Notebook (start here)
│
├── outputs/
│   ├── figures/          ← Saved plots (.png)
│   └── tables/           ← Saved result tables (.csv)
│
├── requirements.txt      ← Python packages needed
└── README.md             ← This file
```

---

## Datasets Used

| Dataset | Source | Link |
|---|---|---|
| Project CCHAIN (health + environment + socioeconomic, Davao, 2003–2022) | Humanitarian Data Exchange | https://data.humdata.org/dataset/project-cchain |
| EMB-XI PM10 Annual Reports | EMB Region XI | https://r11.emb.gov.ph/ |
| WHO Philippines Health Indicators | HDX / WHO | https://data.humdata.org/m/dataset/who-data-for-philippines |

---

## Key References (DOIs)

1. Ho et al. (2023) — Pediatric asthma in the Philippines. `doi:10.1016/j.lanwpc.2023.100806`
2. Yang et al. (2024) — Asthma trends, Western Pacific 1990–2045. `doi:10.2196/55327`
3. Gallano et al. (2024) — PM2.5 and child respiratory illness, Philippines. https://ph01.tci-thaijo.org/index.php/aer/article/view/255626
4. Zhang et al. (2021) — PM and pediatric asthma exacerbation. `PMC8312457`
5. Ye et al. (2023) — PM10 and pediatric hospitalization. `PMC9908005`

---

## Setup Instructions

### 1. Clone this repo
```bash
git clone https://github.com/YOUR_USERNAME/pm10-asthma-davao.git
cd pm10-asthma-davao
```

### 2. Install Python dependencies
```bash
pip install -r requirements.txt
```

### 3. Launch Jupyter
```bash
jupyter notebook
```
Then open `notebooks/01_analysis.ipynb`

---

## Analysis Steps (in the notebook)

- [ ] Step 1: Load and explore the CCHAIN dataset
- [ ] Step 2: Filter for Davao City, ages 5–12, asthma variables
- [ ] Step 3: Load and clean PM10 data
- [ ] Step 4: Merge datasets on date + barangay
- [ ] Step 5: Seasonal decomposition of PM10
- [ ] Step 6: Correlation analysis (Pearson + Spearman)
- [ ] Step 7: Multivariate regression with socioeconomic covariates
- [ ] Step 8: WHO threshold comparison
- [ ] Step 9: Export figures and tables for paper

---

## License
This project is for academic research purposes.
