# Multicriteria Decision Analysis for Solar PV and Battery Sizing 

## Overview of AHP  
The Analytic Hierarchy Process (AHP) is a structured MCDM method introduced by T. L. Saaty.  It organizes a decision into a hierarchy (goal, criteria, subcriteria, alternatives) and uses pairwise comparisons to derive relative weights.  In practice, decision-makers compare elements (criteria or alternatives) two at a time using Saaty’s 1–9 scale (1 = equal importance, 3 = moderate importance, …, 9 = extreme importance).  These comparisons form a positive reciprocal matrix A (i.e., a<sub>ji</sub>=1/a<sub>ij</sub>).  The principal eigenvector of A (the normalized eigenvector for the largest eigenvalue λ<sub>max</sub>) gives the priority weights.  For example, for three criteria C1, C2, C3 the pairwise matrix might be:  

|    | C1   | C2   | C3   |
|----|:----:|:----:|:----:|
| C1 | 1    | 3    | 5    |
| C2 | 1/3  | 1    | 2    |
| C3 | 1/5  | 1/2  | 1    |

Row-normalizing and averaging gives weights (w1≈0.65, w2≈0.23, w3≈0.12), which sum to 1.  This means C1 is judged most important.  One can compute these weights exactly by solving A·w = λ<sub>max</sub>·w (or approximately by normalizing columns and averaging rows).  

However, human judgments may be inconsistent (e.g. if C1>C2 and C2>C3 but C3>C1 is implied).  AHP measures consistency: the **Consistency Index** CI = (λ<sub>max</sub> – n)/(n–1) (where n is matrix size), and the **Consistency Ratio** CR = CI/RI, where RI is the “Random Index” (the average CI of random matrices of size n).  Saaty recommends CR≤0.10 as acceptable.  Typical RI values are RI(3)=0.58, RI(4)=0.90, RI(5)=1.12, ..., RI(10)=1.49.  For instance, in the above 3×3 example λ<sub>max</sub>≈3.003, giving CI≈0.00165 and CR≈0.003 (very consistent).  In formula form: 

```math
CI \;=\; \frac{\lambda_{\max} - n}{n-1}, 
\quad
CR \;=\; \frac{CI}{RI_n}\quad (\text{acceptable if }CR\le0.10).
``` 

A step‐by‐step AHP procedure is: 
- **Define hierarchy:** Goal at top, then criteria (and subcriteria), then alternatives.  
- **Pairwise comparisons:** For each node, compare its children in pairs using the 1–9 scale, filling a reciprocal matrix A.  
- **Compute weights:** Find the normalized principal eigenvector of A (or normalize columns & average rows).  These weights measure relative importance.  
- **Check consistency:** Compute CI and CR.  If CR>0.10, review and adjust inconsistent judgments.  
- **Aggregate:** Multiply each criterion’s priority by its parent weight and sum down to compute each alternative’s overall score (global priority).  

The key point is that AHP quantifies subjective judgments through structured comparisons.  

## Worked AHP Example  
To illustrate, suppose we have three alternatives A,B,C to cover energy demand, and we use three criteria: *Cost*, *Reliability*, and *Environmental Benefit*.  We build pairwise matrices for criteria and for alternatives under each criterion.  For simplicity, consider only the criteria level: imagine decision-makers judge that Reliability is strongly more important than Cost (say 5:1), and Cost is slightly more important than Environmental Benefit (3:1), and Reliability is very strongly more important than Environmental Benefit (7:1).  The criteria comparison matrix (rows vs columns) might be:  

|              | Cost (C1) | Reliability (C2) | Env. (C3) |
|--------------|:---------:|:----------------:|:---------:|
| **Cost (C1)**        |   1    |     1/5         |    3     |
| **Reliability (C2)** |   5    |     1           |    7     |
| **Env. (C3)**        |   1/3  |     1/7         |    1     |

Column-normalize and average rows:  
- Sum columns: (1+5+1/3)=6.333, (1/5+1+1/7)≈1.342, (3+7+1)=11.  
- Normalize: for example, Cost row becomes (1/6.333, 0.2/1.342, 3/11) ≈ (0.158, 0.149, 0.273).  
- Row averages (priority): Cost≈(0.158+0.149+0.273)/3≈0.193; Reliability≈(5/6.333 + 1/1.342 + 7/11)/3; Env≈(0.053+0.106+0.091)/3.  

Doing the math yields approximate weights, e.g. Reliability highest (∼0.70), Cost next (∼0.19), Environment last (∼0.11).  One can also compute λ<sub>max</sub>≈3.02, giving CI≈0.011 and CR≈0.019 (very consistent).  These weights indicate how much each criterion matters overall.  Next, similar comparisons among A,B,C under each criterion yield alternative scores which are multiplied by these criterion weights and summed to give final rankings.  This concrete example shows AHP in action, with formulas implemented via eigenvectors or normalization.  

## AHP and MCDM in PV/Battery Decisions  
AHP and related MCDM methods are widely used in renewable energy planning.  Studies often break down criteria into technical, economic, social, and environmental groups.  For solar PV and battery sizing, typical criteria include: *Energy Reliability* (fraction of load met or backup resilience), *Cost* (capital and operating cost), *Payback/Economic* (levelized cost or ROI), *Environmental Impact* (emissions reduction), and *Risk/Technical Maturity*.  For example, Oening et al. (2023) applied AHP to choose battery technology using criteria of **efficiency (energy yield), load management (reliability), technical maturity, cost, environmental impact, and energy quality**.  In that study, experts assigned weights to four top‐level criteria (environmental, technological, regulatory, financial) and then evaluated four battery types (lead-acid variants and LiFePO<sub>4</sub>) to rank them. 

In practice one often finds that *reliability/outage coverage* and *cost* dominate the weights, while *environmental impact* and *risk* get smaller weights.  For example, a fuzzy AHP study of five battery chemistries found that technical maturity and efficiency often outranked pure cost in importance.  Likewise, PV system studies may weight energy yield (specific generation) and payback higher than site-specific factors.  A broad review notes that ESS selection criteria typically fall into *technology*, *economy*, *society*, and *environment* categories.  (Society here can include safety or social acceptance.)  Specific weights vary by study, but all emphasize reliability (energy security) and cost.  For example, **Bulut & Ozcan (2021)** evaluated five battery types (lead-acid, Li-ion, flow, etc.) with fuzzy AHP-TOPSIS under criteria like efficiency, cost, maturity, enviro-impact and found lithium chemistry often favored when giving high weight to energy density.  

In sum, AHP and MCDM have been used to size or select PV+battery systems with criteria including *coverage of demand*, *backup resilience*, *capital and maintenance cost*, *economic payback*, *carbon/emissions benefit*, and *technology risk*.  Studies typically assign weights in the range 0.1–0.4 to each criterion (summing to 1), e.g. reliability 0.3–0.4, cost 0.2–0.3, payback 0.1–0.2, environment 0.1–0.2, risk 0.05–0.1, depending on context.  (These are illustrative; actual weights should be sourced or justified by stakeholders.) 

## Other Decision Methods (Weighted Scoring, TOPSIS, Utility)  
Apart from AHP, other MCDM and decision-analytic methods are available.  A simple alternative is **weighted scoring** (a multi-attribute value model): each alternative is scored (often on a normalized scale) on each criterion, these scores are multiplied by pre-assigned weights, and summed to give a total score.  This is like AHP without the pairwise comparison; it requires choosing weights and scoring scales.  

**TOPSIS** (Technique for Order Preference by Similarity to Ideal Solution) is a popular method when all criteria are quantitative.  It identifies the “ideal” (best) and “nadir” (worst) levels for each criterion across alternatives, then computes each alternative’s distance to these ideal points.  The alternative closest to the ideal and furthest from the nadir ranks best.  TOPSIS can rank PV+storage options when criteria (e.g. LCOE, reliability, payback) are available as numbers.  Some studies combine AHP for weights with TOPSIS for ranking.  

In contrast, **utility theory / classical decision analysis** handles uncertainty explicitly.  Each outcome (e.g. system cost, outage duration) is assigned a utility (satisfaction) function.  Under uncertainty (e.g. from Monte Carlo simulation), one can compute each alternative’s *expected utility* (averaging utilities over probability distribution).  Alternatively, **expected value of perfect information (EVPI)** or *expected regret* approaches can be used: expected regret measures how much worse an alternative is versus the best case under each scenario, averaged over scenarios.  This allows decision-makers to account for risk preferences.  For example, if your simulation yields distributions of annual cost and unmet load for each PV/battery design, you could define a utility u(cost, reliability) and compute expected utility to rank the options under uncertainty.  

In summary, AHP is one of many MCDA tools.  As noted by Dolan et al., “methods discussed include … direct weighting methods, multi-attribute decision analysis, and the analytic hierarchy process (AHP)”.  Weighted scoring is quick but sensitive to how weights are chosen.  TOPSIS is useful when criteria are quantitative and monotonic.  Classical decision analysis (expected utility/regret) is most appropriate when you have probabilistic outcomes from simulation and a clear utility function.  One can link Monte Carlo outputs to decision criteria by computing statistics (mean, probability of meeting load, Value-at-Risk) and using those as inputs to the decision method.  

## Defining and Justifying Weights  
A major critique of MCDM is the subjectivity of weights.  If stakeholder input is unavailable, weights must be justified somehow.  One approach is to use **literature-derived weights**: review similar case studies or standards and adopt those proportions.  Another is to assume an “expert panel” (as if expert opinions are being used) and label the assumption clearly.  For example, Oening et al. took the geometric mean of eight expert scores to set weights.  

Because weights strongly influence outcomes, **sensitivity analysis** is recommended.  This means re-running the decision model with different plausible weight sets (e.g. emphasizing cost vs. reliability) to see if the ranking of alternatives changes.  A robust result holds under a range of weights.  For instance, Oening et al. explicitly constructed alternate scenarios (e.g. “emphasize environmental” or “emphasize cost”) to test how the preferred battery changed.  Any assumed weights should be clearly documented, and one can perform a one-at-a-time sensitivity (vary each weight by ±X%) or Monte Carlo simulation on weights to test stability.  In absence of stakeholders, it is common to report the base-case literature weights and then show sensitivity charts to assure readers that conclusions are not an artifact of arbitrary weighting. 

## Implementation: Python/Excel Example  
AHP is easily implemented in code or spreadsheets.  In **Python** one can use NumPy/Pandas to handle the math.  A simple outline: 

```python
import numpy as np

# Example pairwise matrix for n criteria:
A = np.array([[1,   5,   3],
              [1/5, 1,   1/2],
              [1/3, 2,   1  ]], float)
# Compute priority weights (principal eigenvector):
eigvals, eigvecs = np.linalg.eig(A)
index = np.argmax(eigvals.real)
w = eigvecs[:, index].real
w = w / np.sum(w)  # normalize to sum 1

# Consistency:
n = A.shape[0]
lambda_max = eigvals[index].real
CI = (lambda_max - n) / (n - 1)
RI = {1:0,2:0,3:0.58,4:0.90,5:1.12}[n]
CR = CI/RI
```

This code yields the weights w and consistency ratio CR for any input matrix (assuming RI defined).  One can wrap this in functions, or use Pandas to normalize columns and average rows (an approximate method).  For **spreadsheets**, the AHP steps are:

- Enter the pairwise matrix in cells (with reciprocals).  
- Sum each column.  
- Divide each entry by its column sum to get a normalized matrix.  
- Compute each row’s average of the normalized matrix; this is the priority vector.  
- To check consistency, compute the weighted sum for each row (i.e. dot product of the original matrix row with the weights) and divide by the weight; average these λ<sub>i</sub> to find λ<sub>max</sub>, then compute CI and CR as above.  

For example, if the weights are [w1, w2, w3], one can in Excel multiply row i by [w1,w2,w3], sum, and divide by w_i to get λ_i.  If CR≤0.10, the matrix passes consistency.  

## Presenting Results and Limitations  
Results are often presented as a **ranking table** of alternatives with their total scores.  Bar charts or bullet graphs can show each alternative’s score broken down by criteria contribution.  To illustrate weight sensitivity, a **spider (radar) chart** or tornado chart can show how the top-ranked alternative changes as one criterion’s weight is varied.  A **trade-off scatterplot** (a Pareto plot) can also be useful: e.g. plot system *cost* vs *reliability* for each alternative, highlighting the rank.  

**Limitations:** AHP (like all subjective MCDM) depends on the chosen scale and consistency of judgments.  The 1–9 scale is somewhat arbitrary, and rank reversal (when adding a new alternative changes existing ranks) can occur unless the decision is framed carefully.  The Consistency Ratio check helps ensure judgments are not random, but recent analyses note that CR can have blind spots (“false negatives” of inconsistency) and is sensitive to matrix size.  All conclusions should be framed as conditional on the weight assumptions.  Finally, AHP assumes additive value (no interaction between criteria); if criteria are not independent, more complex methods (e.g. Analytic Network Process) may be needed.  

**Sources:** The above methods and guidelines are described in Saaty’s work and in renewable energy decision analyses.  The implementation logic can be found in many AHP tutorials and technical reports.