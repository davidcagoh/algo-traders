# Divergence Portfolio Theory
### A framework for holistic distribution fitting and overfitting mitigation

---

## 1. Core Observation

Elementary functions appeared diverse but are unified by a single primitive (EML operator). Distribution divergence measures appear diverse but are similarly unified: nearly all belong to the **$f$-divergence family** or the **integral probability metric (IPM)** family, with the **Rényi $\alpha$-divergence** serving as the most natural single-parameter unification.

$$D_\alpha(P \| Q) = \frac{1}{\alpha - 1} \ln \int p^\alpha q^{1-\alpha}$$

This is the "EML analogue" for divergences: one formula, one knob $\alpha \in \mathbb{R}$, the entire classical family falls out.

---

## 2. The $\alpha$-Sensitivity Hierarchy

The parameter $\alpha$ controls *which region* of the density ratio $r = p/q$ dominates the divergence.

| $\alpha$ | Divergence | Sensitivity | Behaviour |
|---|---|---|---|
| $\alpha \to -\infty$ | — | Extreme tail | Numerically unstable |
| $\alpha = -1$ | — | Tail-seeking | Underexplored; robust to head |
| $\alpha \to 0$ | Reverse KL | Mode-seeking | Ignores tails; prone to collapse |
| $\alpha = 1/2$ | Hellinger | Bulk / middle | Symmetric; well-behaved |
| $\alpha \to 1$ | KL (forward) | Mass-covering | Penalises missing mass |
| $\alpha = 2$ | $\chi^2$ | Head / overfit | Penalises where $p \gg q$ |
| $\alpha \gg 1$ | — | Extreme head | Amplifies dominant modes |

**Key tension:** tail sensitivity and finite-sample estimability are in direct conflict — heavier tail weighting inflates estimator variance.

---

## 3. Complementarity Principle

No single $\alpha$ gives a holistic fit:

- **Reverse KL** ($\alpha \to 0$): mode-seeking; fitted distribution collapses onto dominant modes, ignoring data in low-density regions → *underfits tails, overfits modes*
- **Forward KL** ($\alpha \to 1$): mass-covering; spreads probability to avoid missing data mass → *may oversmooth*
- **$\chi^2$** ($\alpha = 2$): penalises where fitted distribution exceeds data → *sensitive to head, blind to tails*

A **portfolio** of complementary $\alpha$ values simultaneously:
1. Prevents mode collapse (include $\alpha > 1$)
2. Prevents tail neglect (include $\alpha < 1/2$)
3. Ensures bulk fidelity (include $\alpha \approx 1/2$)

### Proposed minimal portfolio

$$\mathcal{L} = \sum_{k} \lambda_k \, D_{\alpha_k}(P \| Q), \qquad \alpha \in \{-1,\ 0,\ \tfrac{1}{2},\ 1,\ 2\}$$

where $\lambda_k \geq 0$, $\sum_k \lambda_k = 1$ are mixture weights, either fixed by prior knowledge or **learned jointly** with the distribution parameters.

---

## 4. Connection to Existing Frameworks

| Framework | Relation to divergence portfolio |
|---|---|
| **Normalising flows** | Forward + reverse KL already used to avoid mode collapse |
| **$\beta$-divergence / Bregman** | Explicit tail vs. bulk tradeoff in NMF and robust estimation |
| **Composite likelihood** | Fitting multiple marginals ≈ complementary sensitivity regions |
| **Distributionally robust optimisation (DRO)** | Minimise worst-case loss over an $f$-divergence ball; multiple balls ≈ portfolio |
| **MMD with mixed kernels** | Kernel choice implicitly controls tail sensitivity; most practical current handle |
| **Wasserstein-$p$** | Large $p$ → tail-sensitive, but high sample complexity |

---

## 5. The Tail Gap

A **named, well-behaved, explicitly tail-sensitive divergence** does not yet exist in standard form. Closest candidates:

- Rényi $\alpha > 2$: formally correct but numerically explosive
- MMD with heavy-tailed kernel (e.g. rational quadratic): currently the cleanest practical proxy
- Wasserstein-$p$ for large $p$: tail-sensitive but requires optimal transport, expensive

**Open direction:** construct a divergence $D_\tau$ that is:
- Explicitly parameterised by tail-weight $\tau$
- Finitely estimable from samples (bounded variance)
- Reduces to a classical member at $\tau = 0$

This would complete the portfolio's coverage of the density ratio support.

---

## 6. Overfitting Mitigation via Divergence Portfolio

Classical overfitting arises when the fitted distribution $Q$ memorises the empirical measure $\hat{P}$ rather than the true $P$. A single divergence $D_f(P \| Q)$ creates a single "surface" in distribution space; the model finds shortcuts to minimise it without holistic fidelity.

**Portfolio mechanism:**

- Different $\alpha$ values create *non-collinear* loss surfaces in distribution space
- A model must simultaneously satisfy constraints at multiple sensitivity regions
- This is geometrically analogous to **$L^1 + L^2$ regularisation** (elastic net): no single direction minimises both losses, so the solution is forced toward a more faithful region

**Formal connection to regularisation:**

$$\mathcal{L}_\text{portfolio} = \sum_k \lambda_k D_{\alpha_k}(\hat{P} \| Q) + \Omega(Q)$$

where $\Omega(Q)$ is a structural prior (e.g. smoothness). The divergence portfolio *replaces or augments* $\Omega$ with data-driven multi-scale constraints.

---

## 7. Learnable Weights and the EML Connection

If the $\lambda_k$ are themselves learned (e.g. via softmax logits), the framework becomes:

$$\lambda_k = \text{softmax}(\theta)_k, \qquad \theta \in \mathbb{R}^K$$

This is a **meta-learning** problem: which divergence weighting best reflects the true data geometry? Notably, each $D_{\alpha_k}$ is itself an elementary function of the density ratio — meaning the full portfolio objective is an elementary function, and in principle expressible as an EML tree. This connects the symbolic regression angle of the EML paper directly to the optimisation objective.

---

## 8. Open Questions

1. **Does a tail-complete divergence exist** with bounded sample complexity? What is the minimax rate?
2. **Can $\lambda_k$ be learned stably** without the portfolio collapsing onto a single $\alpha$? (Analogous to attention head collapse in transformers.)
3. **Is there a continuous family** $D_{\alpha, \tau}(P \| Q)$ parameterised jointly by sensitivity region ($\alpha$) and tail weight ($\tau$)?
4. **Geometric interpretation:** do the $\alpha$-divergence level sets in the space of distributions form a coordinate system analogous to the $(\alpha, e)$-flat duality in information geometry?
5. **EML analogue for divergences:** is there a single binary operation $\mathcal{D}$ on pairs of distributions such that composing $\mathcal{D}$ generates all $f$-divergences from a fixed seed?

---

## 9. Summary

| Concept | EML (functions) | Divergence portfolio (distributions) |
|---|---|---|
| Primitive | $\text{eml}(x,y) = e^x - \ln y$ | $D_\alpha(P\|Q)$ with varying $\alpha$ |
| Generates | All elementary functions | All classical divergences |
| Operation | Tree composition | Parameter variation + mixture |
| Universality | Proved constructively | Established via Rényi family |
| Overfitting analogue | — | Single divergence = single loss surface; portfolio = elastic net |
| Open frontier | Unary Sheffer / no-constant variant | Tail-sensitive, estimable divergence |

---

*Personal research notes — draft. Last updated April 2026.*
