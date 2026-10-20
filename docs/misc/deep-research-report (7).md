# Weather Data and Hot-Year Scenario for Batac, Philippines

### NASA POWER Data  
NASA’s POWER (Prediction Of Worldwide Energy Resources) project provides long-term weather and solar data on a global grid.  For Batac (18.06°N, 120.56°E), useful variables include 2‑m air temperature (T2M) with daily mean, min (T2M_MIN), and max (T2M_MAX) values; 2‑m relative humidity (RH2M); 10‑m wind speed (WS10M); surface solar irradiance (all-sky SW down, ALLSKY_SFC_SW_DWN, and clear-sky SW down, CLRSKY_SFC_SW_DWN); and precipitation (PRECTOTCORR, a bias-corrected daily total in mm). These are all available from NASA POWER.  (All values are metric by default: °C for temperature, % for RH, m/s for wind, W/m² for irradiance, mm for precipitation.)  The data come from NASA reanalysis products: MERRA‑2 for meteorology (0.5°×0.625° grid) and CERES for radiation (1° grid).  (Precipitation uses IMERG satellite data at ~0.1°.)  NASA POWER is like a **virtual weather station network**: it fuses satellites and models to give consistent data worldwide. 

- **Temporal coverage:** Daily data span Jan 1981 to present (updated to near real time).  Hourly data are available from 2001 onward.  (Hourly data default to Local Solar Time unless UTC is requested.)  For simulations of building energy, hourly data capture load peaks better than daily, but NASA’s hourly record is shorter.  
- **Access:** Users can download data via the POWER Data Access Viewer (a web map) or via the REST API.  For example, using Python’s `requests` library one can query the daily point API:  

```python
import requests, pandas as pd

lat, lon = 18.06, 120.56  
# Define time range and parameters
start, end = "20150101", "20151231"  
params = ",".join(["T2M","T2M_MIN","T2M_MAX","RH2M","WS10M",
                    "PRECTOTCORR","ALLSKY_SFC_SW_DWN","CLRSKY_SFC_SW_DWN"])
url = (
    f"https://power.larc.nasa.gov/api/temporal/daily/point?"
    f"parameters={params}&community=RE&latitude={lat}&longitude={lon}"
    f"&start={start}&end={end}&format=JSON"
)
r = requests.get(url)
data = r.json()
df = pd.DataFrame(data['properties']['parameter'])
df.index = pd.to_datetime(df.index, format='%Y%m%d')
```  

- **Units and quirks:** NASA POWER uses metric units and encodes missing values with –999.  You must replace or drop these when processing.  Also, because POWER is a reanalysis (not a direct surface measurement), it can differ from local station data: for example, satellite-derived precipitation may underestimate heavy rains [Speculation], and solar irradiance from CERES may have small biases.  (Always inspect and, if possible, compare with local data.)  

### Other Free Weather/Solar Data Sources  
To cross-check or complement NASA POWER, several global or regional sources are available:

- **Open-Meteo (ERA5 reanalysis):** Open-Meteo provides free weather APIs (no key required).  For historical data it uses **ERA5 reanalysis** (ECMWF) at 0.25° (~28 km) grid and ERA5-Land at 0.1° (~9 km).  Data go back to 1940 (ERA5) or 1950 (ERA5-Land) and include hourly or daily temperature, humidity, precipitation, wind, and even solar radiation variables (GHI, DNI, DHI).  One simply constructs a URL (HTTP GET) with latitude/longitude and variable names.  A strength is the long record and no missing values (ERA5 is gap-free).  The free tier allows ~10,000 calls/day.  In the tropics, ERA5 data are generally comparable to NASA MERRA‑2 (differences <1 °C typical [Inference]), but local verification is wise.  

- **Copernicus ERA5/ERA5-Land (via CDS):** The official route is through the Copernicus Climate Data Store (CDS).  ERA5 single-level reanalysis (hourly, 0.25°, global, from 1950) and ERA5-Land (hourly or daily, 0.1°, land areas) can be downloaded using the `cdsapi` Python client after registering on the CDS.  Data are available since 1950 and include many variables (temperature, humidity, etc.).  The spatial resolution (31 km for ERA5, 9 km for ERA5-Land) is higher than NASA POWER’s.  Copernicus data tend to align well with NASA POWER for broad trends.  One limitation: CDS downloads can be slower and require account setup.  

- **Global Solar Atlas (World Bank):** This web tool gives solar resource maps and typical year solar irradiance.  Data come from Solargis at ≈1 km resolution (derived from satellite and surface data).  You can query a specific location for average GHI or download a typical meteorological year (TMY) file.  It’s free to use via the website (account may be needed for downloads).  The Global Solar Atlas is a helpful check on NASA POWER’s ALLSKY_SFC_SW_DWN.  (It generally agrees within ~5% at large scale [Inference].)  

- **PVGIS (EU JRC):** The Photovoltaic Geographical Information System offers solar and weather time series (including hourly irradiance and temperature) worldwide.  It historically uses coarse global datasets (∼40 km) but now also provides higher-res products (e.g., from CAMS or ERA5).  Users can input coordinates on the PVGIS site or use its REST interface to obtain typical-year data.  It’s a common tool for PV system yield, and its solar inputs (GHI, DNI, etc.) can be compared with NASA POWER radiation.  (Differences are usually small but can vary by location.)  

- **PAGASA Observations:** The Philippine weather service (PAGASA) maintains raw meteorological records from local stations.  Public access is limited, but summaries (e.g. annual climate bulletins) show observed trends.  PAGASA has also released high-resolution gridded climate data for the Philippines (ClimGridPh project).  This ClimGrid dataset offers daily rainfall and temperature (min/mean/max) on a fine grid for the recent 30-year baseline.  For our purposes, PAGASA bulletins or the new CliMap portal allow verifying NASA POWER against actual Philippine data.  (Using PAGASA station data directly often requires special requests.)  

### Climate Context (Northern Luzon)  
Historically, northern Luzon (including Ilocos Norte) has warmed in line with the Philippines-wide trend.  PAGASA reports that the national average annual temperature rose by about 0.6 °C over 1991–2020.  Strong El Niño years (e.g. 2015–2016, 2019) produced unusually high heat and dry spells in Luzon (many locations saw record-high monthly averages [Unverified]).  For example, heat index maps by PAGASA show that summer afternoons can reach the “dangerous” category (>40 °C apparent) across lowland Luzon [Speculation].  The hottest days on record in the Philippines have exceeded 40 °C (often in coastal plains); local maxima in Batac may be a few °C lower due to coastal breezes [Unverified].  

PAGASA’s new climate change projections (based on CMIP6) indicate further warming.  By 2050 (mid-century), under moderate to high-emission scenarios (SSP2-4.5 and SSP5-8.5), projected increases in annual mean temperature for Luzon are on the order of 1–2 °C above the 1981–2010 baseline.  By end of century, warming could reach +3–4 °C.  Meanwhile, rainfall changes are less uniform: for northern Luzon, models suggest increased rainfall in the wet season (June–July) but potential decreases in late spring (March–May).  PAGASA’s CliMap v2 tool now provides downloadable monthly climate projections for each Philippine locality for 2021–2050 and beyond.  These projections are based on downscaled CMIP6 ensembles and can be used to justify extreme weather scenarios.  

### Hot-Year Scenario Construction  
Two “hot-year” scenarios are often used: a **+2 °C uniform shift** and a **record-hot year replay**.  The +2 °C scenario means adding 2 °C to all historical temperatures (both mean and extremes) across the year.  This is analogous to a future warming projection (roughly the Paris Agreement target) and is easy to implement in data: simply increase all T2M values by 2.  The downside is that it does not change humidity or rainfall patterns unless those are adjusted separately.  An alternative is to select an actual hottest historical year as the “year of interest.” For example, if 2019 or 2016 was the hottest on record in this region, one could use that year’s daily series as the basis for simulation.  This captures both high temperatures and any associated weather (though using 2016’s rainfall in 2026 might not reflect climate change).  In practice, many analysts do both: run one case with a +2 °C offset and another case using the data from an extreme El Niño year.  

In either approach, one must decide how to handle humidity and solar radiation.  A pure +2 °C shift might leave relative humidity lower (since warm air holds more moisture), potentially underestimating heat index; one could instead fix dew point and recalc RH [Inference].  Selecting a historic year automatically carries the correct humidity from that year (and usually a higher heat index during hot spells).  In summary, a **“hot year”** input can be built by either uniformly warming the baseline record or by picking a recent anomalously warm year’s data.  Both methods are used in climate impact studies.  (Care: these treatments are simplified scenarios; they should be labeled as assumptions [Unverified] when reported.)  

### Data Quality and Usage Tips  
- **Missing values:** NASA POWER outputs use a fill value of –999 for missing data.  Check for these in the downloaded data and replace them with `NaN` or interpolate as needed.  Some variables (e.g. solar radiation) may have missing values on certain days if satellite retrievals failed.  When using daily data, ensure that –999 is not left in calculations.  
- **Consistency of time resolution:** Decide if your simulation needs hourly or daily inputs.  NASA POWER’s **hourly** API (from 2001 onward) can provide hour-by-hour profiles (useful for capturing peak cooling loads).  The **daily** API (1981 onwards) provides day-averages and minima/maxima.  If only daily data are available, you may need to disaggregate (e.g. by assuming typical diurnal cycles) or accept a less precise result.  Note also that mixing NASA daily data (UTC) with local clock (LST) can introduce small timing shifts; the default NASA time is local solar time unless you specify UTC.  

- **Simulations:** For energy modeling, use the weather parameter frequency that matches your model.  EnergyPlus or similar simulators often require hourly inputs (e.g. using an EPW weather file). NASA POWER can provide an EPW format directly (SB community, from 2001+) but only at its fixed locations.  Otherwise, download hourly CSV or JSON and convert to the needed format.  Be aware that reanalysis data (like NASA’s or ERA5) represent gridbox averages.  In high-resolution urban settings, local shading, land cover, or microclimate might differ.  

### Summary Table of Weather Parameters  

| Parameter                  | Units       | Source(s)                                  | Spatial Resolution                    | Recommended Use                            |
|----------------------------|-------------|--------------------------------------------|---------------------------------------|--------------------------------------------|
| 2 m Air Temp (mean/min/max)  | °C          | NASA POWER (MERRA-2), ERA5/ERA5-Land, PAGASA | 0.5°×0.625° (NASA POWER); 0.25° (ERA5); 0.1° (ERA5-Land); point (stations) | Building heating/cooling load             |
| 2 m Relative Humidity      | %           | NASA POWER (MERRA-2), ERA5                 | 0.5°×0.625° (NASA POWER); 0.25° (ERA5)                   | Heat index, cooling demand                |
| 10 m Wind Speed            | m/s         | NASA POWER (MERRA-2), ERA5                 | 0.5°×0.625° (NASA POWER); 0.25° (ERA5)                   | Natural ventilation, wind load            |
| Surface Solar Irradiance (All-sky) | W/m²       | NASA POWER (CERES), Global Solar Atlas, PVGIS | 1° (CERES); ~1 km (Solargis)                    | PV generation, solar cooling              |
| Surface Solar Irradiance (Clear-sky) | W/m²       | NASA POWER (CERES)                         | 1° (CERES)                           | Baseline solar resource (no clouds)       |
| Precipitation (corrected)  | mm/day      | NASA POWER (GPM/IMERG), ERA5              | 0.1° (NASA POWER/IMERG); 0.25° (ERA5)                 | Rainfall input (irrigation, cooling)      |

Each source and resolution above is indicative; when building simulations, choose the dataset that best balances accuracy and convenience.  In general, for Batac use the NASA POWER or ERA5 values as the primary weather input (citing those sources as above), and treat PAGASA or local station data as a check.  

**Sources:** Official NASA POWER documentation, Open-Meteo/ERA5 documentation, and PAGASA reports.  (Annotated references above in text.)