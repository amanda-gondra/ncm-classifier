// Published results shown on the page without calling the API, so a visitor sees them even
// while the free API instance is asleep. Every number comes from a versioned report of the
// repository, and project-facts.test.ts fails if any of them stops matching its source:
//   reports/baseline_v1.json                  model in production (baseline_v1)
//   reports/comparison/comparison.json        baseline x BERTimbau, same protocol
//   reports/comparison/inference_benchmark.json  CPU cost of each model
//   src/ncm_classifier/data/positions.json    positions in scope

export const PUBLISHED_TEST = {
  name: "test_v1",
  rows: 146,
  top1: 0.9452,
  top3: 0.9932,
  acceptedTop1: 0.9846,
  reviewRate: 0.1096,
} as const;

export const SECOND_TEST = {
  name: "test_v2",
  rows: 74,
  top1: 0.9459,
} as const;

export const POSITIONS_IN_SCOPE = 37;

export const TRAINING_ROWS = {
  official: 359,
  real: 242, // marketplace (241) + public reference (1)
  synthetic: 299,
} as const;

// Same model trained without the synthetic rows (reports/baseline_v1_no_synthetic.json).
export const WITHOUT_SYNTHETIC_TOP1 = 0.8082;

export const MODEL_COMPARISON = {
  pooledRows: 220,
  top1: { baseline: 0.9455, bertimbau: 0.9455 },
  medianLatencyMs: { baseline: 1.33, bertimbau: 63.1 },
  diskMb: { baseline: 7.3, bertimbau: 436.5 },
} as const;
