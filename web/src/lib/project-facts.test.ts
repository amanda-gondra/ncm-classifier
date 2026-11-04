// @vitest-environment node
// Guards the numbers printed on the page against the repository reports they come from.
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import { describe, expect, it } from "vitest";

import {
  MODEL_COMPARISON,
  POSITIONS_IN_SCOPE,
  PUBLISHED_TEST,
  SECOND_TEST,
  TRAINING_ROWS,
  WITHOUT_SYNTHETIC_TOP1,
} from "@/lib/project-facts";
import { SAMPLE_RESULT } from "@/lib/sample-prediction";

// web/src/lib -> repository root
const ROOT = new URL("../../../", import.meta.url);

function readJson(path: string) {
  return JSON.parse(readFileSync(fileURLToPath(new URL(path, ROOT)), "utf-8"));
}

type Interval = { value: number };
type TestReport = {
  file: string;
  metrics_calibrated_with_rules: { rows: number; top1: Interval; top3: Interval };
};

const baseline = readJson("reports/baseline_v1.json");
const withoutSynthetic = readJson("reports/baseline_v1_no_synthetic.json");
const comparison = readJson("reports/comparison/comparison.json");
const benchmark = readJson("reports/comparison/inference_benchmark.json");
const positions = readJson("src/ncm_classifier/data/positions.json");

function testReport(name: string): TestReport {
  const report = (baseline.tests as TestReport[]).find((test) => test.file === `${name}.csv`);
  if (!report) throw new Error(`${name} is missing from reports/baseline_v1.json`);
  return report;
}

describe("published facts", () => {
  it("match the production model report on test_v1", () => {
    const metrics = testReport(PUBLISHED_TEST.name).metrics_calibrated_with_rules;
    const headline = comparison.headline[PUBLISHED_TEST.name].baseline_v1;

    expect(metrics.rows).toBe(PUBLISHED_TEST.rows);
    expect(metrics.top1.value).toBe(PUBLISHED_TEST.top1);
    expect(metrics.top3.value).toBe(PUBLISHED_TEST.top3);
    expect(headline.accepted_top1.value).toBe(PUBLISHED_TEST.acceptedTop1);
    expect(headline.review_rate.value).toBe(PUBLISHED_TEST.reviewRate);
  });

  it("match the production model report on test_v2", () => {
    const metrics = testReport(SECOND_TEST.name).metrics_calibrated_with_rules;

    expect(metrics.rows).toBe(SECOND_TEST.rows);
    expect(metrics.top1.value).toBe(SECOND_TEST.top1);
  });

  it("match the ablation without synthetic rows", () => {
    const report = (withoutSynthetic.tests as TestReport[]).find(
      (test) => test.file === `${PUBLISHED_TEST.name}.csv`,
    );
    expect(report?.metrics_calibrated_with_rules.top1.value).toBe(WITHOUT_SYNTHETIC_TOP1);
  });

  it("match the scope and the training data", () => {
    const bySource = baseline.train_rows_by_source;

    expect(Object.keys(positions.positions)).toHaveLength(POSITIONS_IN_SCOPE);
    expect(bySource.ncm_official).toBe(TRAINING_ROWS.official);
    expect(bySource.marketplace + bySource.public_reference).toBe(TRAINING_ROWS.real);
    expect(bySource.synthetic).toBe(TRAINING_ROWS.synthetic);
  });

  it("keep the recorded sample consistent with the official catalog", () => {
    for (const suggestion of SAMPLE_RESULT.predictions) {
      expect(suggestion.official_description).toBe(positions.positions[suggestion.ncm].description);
      expect(suggestion.formatted).toBe(positions.positions[suggestion.ncm].formatted);
    }
  });

  it("match the model comparison and the inference benchmark", () => {
    const pooled = comparison.paired.tests_pooled;

    expect(pooled.rows).toBe(MODEL_COMPARISON.pooledRows);
    expect(pooled.top1.model_a).toBe(MODEL_COMPARISON.top1.baseline);
    expect(pooled.top1.model_b).toBe(MODEL_COMPARISON.top1.bertimbau);
    expect(benchmark.models.baseline.single_ms.median).toBe(MODEL_COMPARISON.medianLatencyMs.baseline);
    expect(benchmark.models.bertimbau.single_ms.median).toBe(MODEL_COMPARISON.medianLatencyMs.bertimbau);
    expect(benchmark.models.baseline.disk_mb).toBe(MODEL_COMPARISON.diskMb.baseline);
    expect(benchmark.models.bertimbau.disk_mb).toBe(MODEL_COMPARISON.diskMb.bertimbau);
  });
});
