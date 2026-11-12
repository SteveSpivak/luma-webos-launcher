# Lab 07 — Spectral Analysis & Fiedler Cut

> ⚡ **BLUF**: Fiedler $\lambda_2$ algebraic connectivity via Rayleigh-quotient power
> iteration on the graph Laplacian. Identifies the mathematically optimal cut point
> for splitting coupled modules. $\lambda_2 \approx 0$ indicates a near-disconnected
> graph — a clean modular boundary.

+-----------------------------------------------------------------------------+
| FIEDLER SPECTRAL CUT PIPELINE                                               |
+-----------------------------------------------------------------------------+
|                                                                             |
|  [Adjacency matrix A]  -->  [Degree matrix D]                               |
|                                     |                                       |
|                                     v                                       |
|  [Laplacian L = D - A]              |                                       |
|                                     |                                       |
|                                     v                                       |
|  [Power iteration on L]             |                                       |
|                                     |                                       |
|                                     v                                       |
|  [Fiedler vector v₂]                -->  [Sign split: v₂[i] ≥ 0 vs < 0]   |
|                                     |                                       |
|                                     v                                       |
|  [Two modules with min cross-edges]  -->  [RCPT receipt]                   |
|                                                                             |
+-----------------------------------------------------------------------------+

## Math

Graph Laplacian: $L = D - A$ where $D_{ii} = \text{deg}(i)$, $A_{ij} = 1$ if edge exists.

Rayleigh quotient for $\lambda_2$:
$$\lambda_2 = \min_{v \perp \mathbf{1}} \frac{v^T L v}{v^T v}$$

Power iteration converges to the Fiedler vector $v_2$. The sign of each component
of $v_2$ determines which side of the cut a module belongs to.

Cross-edge count for cut $(S, \bar{S})$:
$$\text{cut}(S) = |\{ (u,v) \in E : u \in S, v \in \bar{S} \}|$$

Minimize $\text{cut}(S)$ subject to balance constraint — this is the spectral
relaxation of the NP-hard minimum bisection problem.

## Measured Result

For this repo's dependency graph:
- $\lambda_2 = 0.0$ — graph is already well-separated into components
- No spectral cut needed (no dense cyclic core)
- 14 connected components means modules are already loosely coupled

**Receipt**: `RCPT-CE7D5046A48A`

## When to Act

| $\lambda_2$ | Interpretation | Action |
|-------------|----------------|--------|
| $\approx 0$ | Nearly disconnected | Clean split point exists |
| Small ($>0$) | Weakly connected | Consider modularization |
| Large | Dense core | Refactor needed (high coupling) |
