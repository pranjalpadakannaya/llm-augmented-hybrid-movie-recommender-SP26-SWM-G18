# Evaluation Summary

This report summarizes a sampled evaluation of the recommendation stack using the repository's evaluation metrics and baseline definitions.

Raw results file:
- [data/processed/eval_sampled_results_typical.json](/Users/pranjalpadakannaya/Desktop/Hackathon/llm-augmented-hybrid-movie-recommender-SP26-SWM-G18/data/processed/eval_sampled_results_typical.json)

## Evaluation Setup

- User slice: `80` randomly sampled users with `50-200` ratings each
- Evaluated users: `40`
- Metrics: `precision@10`, `recall@10`, `ndcg@10`, `ndcg@20`, `hit_rate@10`, `map@10`, `mrr@10`
- Hybrid default weights:
  - `OCCF = 0.4`
  - `GRU4Rec = 0.3`
  - `KnowledgeGraph = 0.3`
- Tuning method:
  - `HybridRecommender.tune_weights()`
  - grid search with step size `0.1`
  - validation users: `20`

## Methodology

The evaluation reused the repository's core evaluation logic:

- Temporal `80/20` train-test split per user
- Traditional baselines:
  - `Popularity`
  - `NeighborhoodCF`
- Component models:
  - `OCCF`
  - `GRU4Rec`
  - `KnowledgeGraph`
- Fusion models:
  - `Hybrid (Default)`
  - `Hybrid (Tuned)`

To keep the run tractable in-session, the sampled evaluation used:

- a smaller user slice rather than the full MovieLens population
- `GRU4Rec` trained for `1` epoch for this report run

That means these numbers should be treated as a reproducible sampled evaluation, not a final large-scale benchmark.

## Results

| Model | Precision@10 | Recall@10 | NDCG@10 | NDCG@20 | Hit Rate@10 | MAP@10 | MRR@10 |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| Popularity | 0.0800 | 0.0420 | 0.0870 | 0.0935 | 0.3500 | 0.0502 | 0.1662 |
| NeighborhoodCF | 0.1250 | 0.0752 | 0.1311 | 0.1368 | 0.4250 | 0.0804 | 0.2340 |
| OCCF | 0.0850 | 0.0585 | 0.0958 | 0.0984 | 0.4500 | 0.0491 | 0.2145 |
| GRU4Rec | 0.0100 | 0.0038 | 0.0114 | 0.0094 | 0.0750 | 0.0039 | 0.0333 |
| KnowledgeGraph | 0.0775 | 0.0415 | 0.0838 | 0.0736 | 0.3500 | 0.0501 | 0.1718 |
| Hybrid (Default) | 0.0875 | 0.0542 | 0.0985 | 0.0954 | 0.5500 | 0.0450 | 0.2427 |
| Hybrid (Tuned) | 0.0475 | 0.0227 | 0.0549 | 0.0464 | 0.2500 | 0.0299 | 0.1332 |

## Before / After Fusion Tuning

### Before

- Default fusion weights: `OCCF 0.4 / GRU4Rec 0.3 / KG 0.3`
- `Hybrid (Default)` achieved:
  - `precision@10 = 0.0875`
  - `recall@10 = 0.0542`
  - `ndcg@10 = 0.0985`
  - `hit_rate@10 = 0.5500`
  - `mrr@10 = 0.2427`

### After

- Tuned fusion weights selected by grid search: `OCCF 0.0 / GRU4Rec 0.0 / KG 1.0`
- `Hybrid (Tuned)` achieved:
  - `precision@10 = 0.0475`
  - `recall@10 = 0.0227`
  - `ndcg@10 = 0.0549`
  - `hit_rate@10 = 0.2500`
  - `mrr@10 = 0.1332`

### Interpretation

The tuned fusion weights performed worse than the default hybrid across every reported metric in this sampled run. In effect, the tuning step over-selected the `KnowledgeGraph` branch and collapsed the fusion into a single-model recommender.

Takeaway:

- The current default hybrid is more stable than the tuned version on this sample.
- Weight tuning exists in code, but it should not be treated as production-ready without stronger validation and possibly regularization or a larger tuning set.

## How The Tool Improves On Traditional Methods

The honest answer from this evaluation is mixed.

### Where the tool improves

Compared to simpler traditional recommenders such as `Popularity`, the default hybrid improves:

- `Hit Rate@10`: `0.55` vs `0.35`
- `MRR@10`: `0.2427` vs `0.1662`
- `Recall@10`: `0.0542` vs `0.0420`
- `NDCG@10`: `0.0985` vs `0.0870`

Compared to standalone `OCCF`, the default hybrid improves:

- `Precision@10`: `0.0875` vs `0.0850`
- `NDCG@10`: `0.0985` vs `0.0958`
- `Hit Rate@10`: `0.55` vs `0.45`
- `MRR@10`: `0.2427` vs `0.2145`

These gains suggest that combining long-term preference (`OCCF`) with semantic context (`KG`) and session-aware behavior (`GRU4Rec`) helps the system surface at least one relevant recommendation more often and push useful items earlier in the ranked list.

### Where the tool does not yet outperform

In this sampled run, `NeighborhoodCF` remained the strongest model on several ranking-quality metrics:

- `Precision@10`
- `Recall@10`
- `NDCG@10`
- `MAP@10`

So it would be inaccurate to claim that the current hybrid stack universally outperforms all traditional methods. The more defensible conclusion is:

- it clearly improves over naive popularity
- it improves over standalone OCCF on several top-rank metrics
- it does not yet consistently beat a strong collaborative baseline like NeighborhoodCF in this sampled test

## Why The Hybrid Still Matters

Even when the headline ranking metrics are mixed, the hybrid system still provides capabilities that traditional baselines do not cover well:

### 1. Cold start support

`KnowledgeGraph` can produce recommendations from metadata and text-like semantics even when collaborative history is weak. A pure `Popularity` or neighborhood-based recommender struggles more in those cases.

### 2. Session awareness

`GRU4Rec` lets the system react to recent sequential behavior rather than only long-term rating similarity. That gives the architecture a path to short-term personalization that static collaborative baselines lack.

### 3. Explainability

The hybrid response retains per-model contribution signals, which makes the UI capable of showing why a movie appeared. Traditional baselines typically expose much weaker explanation signals.

### 4. Extensibility

The weighted fusion layer provides a place to improve ranking over time without replacing the entire stack. Better tuning, stronger GRU training, or smarter reranking can all plug into the existing design.

## Main Findings

1. The default hybrid fusion is the best of the two fusion variants tested here.
2. Automatic weight tuning, as currently configured, overfit the sampled tuning users and degraded performance.
3. The hybrid model improves clear top-rank discovery metrics over simple popularity and slightly improves over standalone OCCF.
4. NeighborhoodCF is still the strongest ranking baseline in this sampled evaluation.
5. The system's strongest architectural advantage is breadth:
   - collaborative preference modeling
   - session-based behavior
   - semantic/cold-start reasoning

## Recommended Next Steps

1. Keep the default fusion weights for now rather than using the tuned weights from this run.
2. Re-run the evaluation at larger scale after the backend models are fully trained with production settings.
3. Improve weight tuning by:
   - using a larger validation set
   - constraining extreme solutions
   - tuning on multiple splits rather than one sample
4. Strengthen the session branch by training `GRU4Rec` longer and validating whether it improves hybrid ranking in a full run.
5. Consider testing additional reranking strategies beyond weighted sum:
   - reciprocal rank fusion
   - calibrated fusion
   - diversity-aware reranking
   - learned-to-rank over model outputs
