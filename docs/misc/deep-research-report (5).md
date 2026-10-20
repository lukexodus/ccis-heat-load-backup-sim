## Monte Carlo Simulation Methodology for Building Energy Models

### Number of replications  
In Monte Carlo simulation, the **number of replications** (independent simulation runs) affects the accuracy of estimated outputs.  Typically, one aims to narrow the confidence interval of the output statistic (e.g. the mean) to a desired half-width.  For example, by the Central Limit Theorem the sample mean $\bar X$ over $n$ runs is roughly normal with standard error $\sigma/\sqrt{n}$, so a 100(1–α)% confidence interval is $$\bar X \pm z_{1-\alpha/2}\,\frac{\sigma}{\sqrt{n}}\,. $$  Solving for a target half-width $\delta$ yields the approximation  
$$n \approx \Bigl(\frac{z_{1-\alpha/2}\,\sigma}{\delta}\Bigr)^2\,. $$  
In practice $\sigma$ is unknown, so one may run a pilot sample to estimate $s$, then compute $n$.  Alternatively, a sequential stopping rule can be used: continue replicating until the half-width of the CI falls below the tolerance.  For instance, using a Gaussian approximation, one can compute the interval on the fly with $s/\sqrt{n}$ and stop when $z\,s/\sqrt{n} \le \delta$.  

Graphical checks such as plotting the running mean vs. replication index are also recommended: when the mean “flattens out” the number of runs is likely sufficient.  Indeed, many practitioners report an arbitrary number of runs (e.g. “10 replicates” or “500 MC runs”) without justification.  Instead, use a principled approach (target error or sequential CI) to choose $n$.  In summary, one can either compute $n$ from $$n=(z\sigma/\delta)^2$$ once an estimate of $\sigma$ is available, or run sequentially and check that the empirical half-width $z s/\sqrt{n}$ is below the threshold.  

**Worked example:** Suppose we want a 95% CI on the annual average loss within ±5%.  If a pilot run (say 30 simulations) estimates $\hat\sigma=10$ (in the same units as the mean) and $z_{0.975}\approx1.96$, then $n\approx(1.96·10/5)^2\approx15.4$, so about 16 runs.  We would run 16 simulations, compute the sample mean and standard deviation, and verify the 95% CI.  (Alternatively, one could simulate runs until the measured CI half-width falls below 5%.)  

### Sampling design (weather and outage scenarios)  
When incorporating **weather uncertainty**, one can either resample from historical years or use a stochastic weather generator.  A simple *bootstrap* approach draws entire years (or days) with replacement from the historical record.  However, this ignores temporal correlation unless handled carefully.  To preserve day-to-day autocorrelation, a **block bootstrap** can be used. In block resampling, the time series is divided into contiguous blocks (e.g. weeks or months), and those blocks are sampled with replacement and concatenated to form new synthetic years.  For example, one might divide a 10-year history into 10 one-year blocks and randomly pick years (with repetition) to build a scenario year; or use shorter overlapping blocks as in the *moving-block bootstrap*.  This ensures that within each block the daily correlations (e.g. warm spells or rainy periods) are retained.  

For *fully synthetic* weather, one could use a parametric or data-driven weather generator. Resampling-based weather generators reorder or combine historical data while preserving statistics.  (For example, openAMUNDSEN and IBMWeatherGen use k-nearest neighbors or direct sampling to stitch historical blocks into new years.) 

When combining weather with **random outages**, a typical approach is hierarchical: first sample or fix a weather year, then superimpose random outage events (e.g. faults) in that year independently.  If outages are assumed independent of weather, one can treat them as a separate Poisson process, adding to the simulation.  If storms cause extra outages, one could correlate outage rates with weather events (e.g. higher rate during typhoons).  In any case, use the same sequence of random numbers (common random numbers) to compare alternative scenarios fairly.

### Input modeling and distribution fitting  
Simulation input models (distributions) are fitted to data using methods like **maximum likelihood (MLE)** or method of moments.  For each variable (e.g. outage interarrival, outage duration, solar radiation, temperature), hypothesize a family of distributions and estimate parameters.  For example, if interarrival times seem memoryless, we may fit an exponential distribution by MLE.  As Law et al. discuss, one can overlay the fitted density on a histogram to judge fit.  As a concrete case, Law’s tutorial illustrates fitting an exponential to interarrival times, finding the MLE of the rate parameter from sample data.  For outages, it is common to model *arrivals* as a Poisson process (hence interarrival times are exponential) and *durations* as lognormal or gamma.  Indeed, restoration durations often have a right-skew: recent studies model outage restoration as lognormal (with heavy tails).  (Large events may exhibit Pareto-like tails, but the lognormal often fits the bulk and moderate extremes.) 

Solar irradiation or clearness index (ratio of actual to clear-sky irradiance) is often bounded (0 to 1), so Beta distributions or truncated normals are used.  Likewise, daily temperature may be approximated by a normal or sinusoids + noise.  After fitting, assess **goodness-of-fit**.  Standard tests include the Kolmogorov–Smirnov (K–S) test for continuous data (which measures the maximum difference between empirical and fitted CDFs) and the chi-square test for binned data.  The K–S test statistic $D_n$ is defined as $\max_x|F_n(x)-\hat F(x)|$.  (Anderson–Darling is a related test that emphasizes tail fit.)  Graphical checks are also useful: probability plots (Q–Q plots) compare quantiles of data vs. a fitted distribution to detect systematic deviations.  

In practice, one might compare several candidate distributions (e.g. exponential vs. Weibull for interarrival) using both visual and statistical tests.  As Law notes, “none of our fitted distributions will be exactly correct,” so we seek ones accurate enough for modeling purposes.  We also check residuals or use the bootstrap to estimate uncertainty in fit.  

### Random variate generation  
Once input distributions are chosen, random variates can be generated by standard methods.  For example, the *inverse transform* method works by generating a uniform $U\sim[0,1]$ and setting $X=F^{-1}(U)$, where $F$ is the CDF of the target distribution.  The *acceptance-rejection* method is used when $F^{-1}$ is not available in closed form: one samples a candidate from an easy envelope distribution and accepts it with appropriate probability.  

In practice, software libraries handle most common cases.  In Python, one can use `numpy.random` or `scipy.stats`. For instance, `np.random.exponential(scale=θ, size=N)` returns $N$ samples from an Exponential($\theta$) distribution; similarly `np.random.poisson(lam)` for Poisson, `np.random.normal(loc, scale)` for Normal, etc.  To ensure reproducibility, always set a fixed seed (e.g. `np.random.seed(123)`) before sampling.  For comparing scenarios, use **common random numbers**: reuse the same random seed or streams so that corresponding random draws align across scenarios, reducing variance in the difference.  

**Example snippet:** To simulate outage arrivals and durations in one year (e.g. days), one could write:  
```python
import numpy as np
np.random.seed(0)
lam = 10                  # mean outages per year
# Sample number of outages
N_out = np.random.poisson(lam)  
# Generate interarrival days (Exp with mean 1/lam per day)
interarr = np.random.exponential(1/lam, size=N_out) 
# Cumulative arrival times (days into year)
arrivals = np.cumsum(interarr) 
# Generate outage durations (hours)
durations = np.random.lognormal(mean=np.log(2), sigma=0.5, size=N_out)
```  
Here we assume an average of 10 outages/year (Poisson), exponential interarrival (so roughly 36.5/10 days between events), and lognormal durations with median 2 hours.  (Any arrivals beyond 365 days could be dropped.) This illustrates inverse-transform (exponential via `np.random.exponential`) and direct library calls.  

### Output analysis and comparisons  
After running the simulations, output is analyzed statistically.  Compute **confidence intervals** on key performance metrics using the sample statistics (mean $\pm$ margin-of-error as above).  Also report percentiles (e.g. 5th, 50th, 95th) of outputs for risk assessment.  For example, sort the simulated annual loss values and take the 0.05, 0.50, 0.95 quantiles to report P5, P50, P95.  

To compare two scenarios (e.g. with vs. without a design change), use paired comparisons.  If the same random stream is used for both, form differences of outputs across runs and apply a *paired t-test* (if approximately normal) or a *Wilcoxon signed-rank test* (nonparametric) to assess if the mean difference is zero.  Confidence intervals on differences can also be computed via the paired-sample statistics. 

For sensitivity analysis, common methods include one-at-a-time (OAT) and global sampling.  In OAT, vary one input parameter (e.g. outage rate or solar capacity) while holding others fixed, and measure the change in output.  A *tornado chart* can visualize these univariate sensitivities.  A more global approach is *Latin Hypercube Sampling* (LHS): sample many combinations of inputs covering their range (each input is stratified into intervals) and perform regression or variance-based analysis.  LHS ensures all parts of each input distribution are explored efficiently.  

For risk reporting, emphasis is often on tail statistics: the upper percentiles (e.g. 95%) indicate worst-case risk.  Use bootstrap or analytic formulas for confidence intervals on these percentiles if needed.  

### Verification and validation  
Finally, ensure the Monte Carlo model is implemented and behaving correctly.  **Verification** checks the code: for example, verify conservation of energy (solar in, loads out) or known properties (e.g. with zero outages, results match the base model).  Insert extreme-value tests: for instance, if one sets the outage rate to zero or 100%, does the output behave sensibly?  Use reproducible seeds to verify deterministic consistency.  **Validation** compares model outputs to any known benchmarks or expert expectations: e.g. does the average outage impact match historical experience (if available)?  Conduct *face validity* checks (do results change sensibly when inputs change?) and document all assumptions.  A common practice is a checklist of tests, such as unit checks, energy balance, known-case recovery, and peer review.  

By following the above methodology—establishing sufficient replications, carefully designing sampling and input distributions, generating variates correctly, and thoroughly analyzing outputs—one obtains reliable Monte Carlo estimates with quantifiable uncertainty.  Maintain clear documentation of assumptions and parameters (including any that were estimated or assumed) for transparency and reproducibility.

**Sources:** Standard references on simulation (Law & Kelton 2000; Banks et al. 2010) explain confidence intervals and stopping rules. Recent tutorials and papers provide guidance on input modeling and weather resampling.  The block-bootstrap approach for weather data is described in statistical literature.  Outage-duration modeling (lognormal/Pareto) appears in reliability research. All code examples use NumPy/SciPy conventions for random variate generation. 

