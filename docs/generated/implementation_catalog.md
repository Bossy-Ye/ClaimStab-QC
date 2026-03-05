# Implementation Catalog

This page is auto-generated from tracked repository files.

## Summary

- Tracked files: `246`
- Python files: `137`
- Markdown files: `36`
- YAML files: `14`
- JSON files: `31`

## Core Abstractions

- `Claim` evaluators: ranking/decision/distribution in `claimstab/claims/*`.
- `Perturbation` space and sampling policies in `claimstab/perturbations/*`.
- `InferencePolicy` implementations in `claimstab/inference/policies.py`.
- `TraceRecord` / `TraceIndex` / `ExecutionEvent` for auditability in `claimstab/core/*`.
- `TaskPlugin` extension contract in `claimstab/tasks/base.py`.
- `Runner` execution path in `claimstab/runners/*`.
- `ClaimAtlas` publish/validate/compare flow in `claimstab/atlas/*`.

## CLI Surface

- Subcommands: `init-external-task`, `run`, `report`, `validate-spec`, `examples`, `export-definitions`, `publish-result`, `validate-atlas`, `export-dataset-registry`, `atlas-compare`.
- Entrypoint: `claimstab` via `project.scripts` in `pyproject.toml`.

## Artifact Contract

- Core run outputs: `scores.csv`, `claim_stability.json`, `rq_summary.json`, `stability_report.html`.
- Reproducibility artifacts: `trace.jsonl`, `events.jsonl`, `cache.sqlite`.
- Paper package root: `output/paper_artifact/`.
- Curated presentation roots: `output/presentation/`, `output/presentation_large/`.

## Extension Points

- Task plugins: implement `TaskPlugin` (`instances`, `build`).
- Inference policies: implement estimate/decision policy interface.
- Perturbation operators: implement `PerturbationOperator.apply`.
- Backends/runners: integrate new execution engine in runner layer.

## Root Files

- `.gitignore`
- `CHANGELOG.md`
- `CITATION.cff`
- `CODE_OF_CONDUCT.md`
- `CONTRIBUTING.md`
- `GOVERNANCE.md`
- `LICENSE`
- `Makefile`
- `README.md`
- `SECURITY.md`
- `mkdocs.yml`
- `pyproject.toml`

## .github

- `.github/ISSUE_TEMPLATE/bug_report.yml`
- `.github/ISSUE_TEMPLATE/config.yml`
- `.github/ISSUE_TEMPLATE/feature_request.yml`
- `.github/PULL_REQUEST_TEMPLATE/dataset_submission.md`
- `.github/pull_request_template.md`
- `.github/workflows/ci.yml`
- `.github/workflows/docs.yml`

## Atlas Files

- `atlas/README.md`
- `atlas/index.json`
- `atlas/submissions/.gitkeep`
- `atlas/submissions/bv_calibration_fullfactorial_v1/claim_stability.json`
- `atlas/submissions/bv_calibration_fullfactorial_v1/metadata.json`
- `atlas/submissions/bv_calibration_fullfactorial_v1/rq_summary.json`
- `atlas/submissions/bv_calibration_fullfactorial_v1/scores.csv`
- `atlas/submissions/bv_calibration_fullfactorial_v1/stability_report.html`
- `atlas/submissions/bv_core_decision_multispace_v1/claim_stability.json`
- `atlas/submissions/bv_core_decision_multispace_v1/metadata.json`
- `atlas/submissions/bv_core_decision_multispace_v1/rq_summary.json`
- `atlas/submissions/bv_core_decision_multispace_v1/scores.csv`
- `atlas/submissions/bv_core_decision_multispace_v1/stability_report.html`
- `atlas/submissions/bv_demo_working_example/claim_stability.json`
- `atlas/submissions/bv_demo_working_example/metadata.json`
- `atlas/submissions/bv_demo_working_example/rq_summary.json`
- `atlas/submissions/bv_demo_working_example/scores.csv`
- `atlas/submissions/bv_demo_working_example/stability_report.html`
- `atlas/submissions/ghz_structural_compilation_v1/claim_stability.json`
- `atlas/submissions/ghz_structural_compilation_v1/metadata.json`
- `atlas/submissions/ghz_structural_compilation_v1/rq_summary.json`
- `atlas/submissions/ghz_structural_compilation_v1/scores.csv`
- `atlas/submissions/ghz_structural_compilation_v1/stability_report.html`
- `atlas/submissions/maxcut_adaptive_sampling_only_ci_w03_v1/claim_stability.json`
- `atlas/submissions/maxcut_adaptive_sampling_only_ci_w03_v1/metadata.json`
- `atlas/submissions/maxcut_adaptive_sampling_only_ci_w03_v1/rq_summary.json`
- `atlas/submissions/maxcut_adaptive_sampling_only_ci_w03_v1/scores.csv`
- `atlas/submissions/maxcut_calibration_fullfactorial_v1/claim_stability.json`
- `atlas/submissions/maxcut_calibration_fullfactorial_v1/metadata.json`
- `atlas/submissions/maxcut_calibration_fullfactorial_v1/rq_summary.json`
- `atlas/submissions/maxcut_calibration_fullfactorial_v1/scores.csv`
- `atlas/submissions/maxcut_calibration_fullfactorial_v1/stability_report.html`
- `atlas/submissions/maxcut_core_multispace_randomk_v1/claim_stability.json`
- `atlas/submissions/maxcut_core_multispace_randomk_v1/metadata.json`
- `atlas/submissions/maxcut_core_multispace_randomk_v1/rq_summary.json`
- `atlas/submissions/maxcut_core_multispace_randomk_v1/scores.csv`
- `atlas/submissions/maxcut_core_multispace_randomk_v1/stability_report.html`
- `atlas/submissions/outside_user_portfolio_v1/claim_stability.json`
- `atlas/submissions/outside_user_portfolio_v1/metadata.json`
- `atlas/submissions/outside_user_portfolio_v1/rq_summary.json`
- `atlas/submissions/outside_user_portfolio_v1/scores.csv`
- `atlas/submissions/outside_user_portfolio_v1/stability_report.html`
- `atlas/submissions/sample_problem_plugin_demo_v1/claim_stability.json`
- `atlas/submissions/sample_problem_plugin_demo_v1/metadata.json`
- `atlas/submissions/sample_problem_plugin_demo_v1/rq_summary.json`
- `atlas/submissions/sample_problem_plugin_demo_v1/scores.csv`
- `atlas/submissions/sample_problem_plugin_demo_v1/stability_report.html`

## Docs Files

- `docs/ARCHITECTURE.md`
- `docs/EXPERIMENT_PLAYBOOK.md`
- `docs/artifact.md`
- `docs/assets/extra.css`
- `docs/assets/interactive.js`
- `docs/assets/pipeline.svg`
- `docs/assets/results_snapshot.svg`
- `docs/atlas.md`
- `docs/cite.md`
- `docs/concepts/claims.md`
- `docs/concepts/extending.md`
- `docs/concepts/formal_definitions.md`
- `docs/concepts/perturbations.md`
- `docs/concepts/threats_to_validity.md`
- `docs/custom_task_quickstart.md`
- `docs/dataset_registry.md`
- `docs/examples.md`
- `docs/generated/.gitkeep`
- `docs/generated/README.md`
- `docs/generated/implementation_catalog.md`
- `docs/index.md`
- `docs/output_map.md`
- `docs/playground.md`
- `docs/quickstart.md`
- `docs/reproduce.md`
- `docs/reproduction_contract.md`
- `docs/results/device_aware.md`
- `docs/results/figures.md`
- `docs/results/interactive_report.md`
- `docs/results/main_results.md`
- `docs/results/structural_benchmark.md`
- `docs/trace_cache_replay.md`

## Examples Files

- `examples/atlas_bv_workflow.py`
- `examples/claim_stability_demo.py`
- `examples/community_contrib_demo/portfolio_task.py`
- `examples/community_contrib_demo/spec_portfolio.yml`
- `examples/custom_task_demo/spec_toy.yml`
- `examples/custom_task_demo/toy_task.py`
- `examples/exp_comprehensive_calibration.py`
- `examples/exp_comprehensive_large.py`
- `examples/exp_structural_compilation.py`
- `examples/multidevice_demo.py`
- `examples/specs/claim_spec.yaml`
- `examples/specs/perturbation_spec.yaml`

## Specs Files

- `specs/atlas_bv_demo.yml`
- `specs/paper_device.yml`
- `specs/paper_main.yml`
- `specs/paper_structural.yml`

## Data Files

- `data/suites/standard.json`

## ClaimStab Python Modules

### `claimstab/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/analysis/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/analysis/rq.py`
- Classes: _none_
- Top-level functions: _as_float, _as_int, _decision_counts, _build_rq5_conditional_robustness, _build_rq6_stratified_stability, _build_rq7_effect_diagnostics, _weighted_std, _emit_rq2_debug, _build_rq2_drivers, build_rq_summary

### `claimstab/analysis/tests/test_rq.py`
- Classes:
  - `TestRQDrivers` (methods: test_rq2_driver_score_uses_value_contrast, test_rq5_conditional_robustness_collects_examples, test_rq6_stratified_stability_collects_and_ranks_examples, test_rq7_effect_diagnostics_collects_main_and_interactions)
- Top-level functions: _none_

### `claimstab/analysis/tests/test_rq2_attribution.py`
- Classes:
  - `TestRQ2Attribution` (methods: test_std_driver_score_highlights_shots_dependency)
- Top-level functions: _none_

### `claimstab/atlas/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/atlas/catalog.py`
- Classes:
  - `SubmissionSnapshot` (methods: -)
- Top-level functions: _load_json, _normalize_list, _format_claim, _github_blob_url, _snapshot_from_entry, build_dataset_registry_markdown

### `claimstab/atlas/compare.py`
- Classes: _none_
- Top-level functions: _resolve_claim_json, _load_payload, _as_float, _row_key, _rows_by_key, compare_claim_outputs

### `claimstab/atlas/registry.py`
- Classes:
  - `AtlasValidationResult` (methods: -)
- Top-level functions: _load_json, _slug, _infer_claim_types, _extract_claim_summaries, _extract_sampling_summary, _default_submission_id, _load_index, publish_result, validate_atlas

### `claimstab/atlas/tests/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/atlas/tests/test_catalog.py`
- Classes:
  - `TestAtlasCatalog` (methods: test_build_dataset_registry_markdown)
- Top-level functions: _none_

### `claimstab/atlas/tests/test_compare.py`
- Classes:
  - `TestAtlasCompare` (methods: _write_payload, test_compare_detects_decision_and_naive_changes, test_compare_accepts_run_directories)
- Top-level functions: _none_

### `claimstab/atlas/tests/test_registry.py`
- Classes:
  - `TestAtlasRegistry` (methods: _write_min_run, test_publish_and_validate, test_publish_requires_claim_json)
- Top-level functions: _none_

### `claimstab/baselines/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/baselines/naive.py`
- Classes:
  - `NaiveComparison` (methods: to_dict)
- Top-level functions: compare_naive_vs_claimstab, evaluate_naive_baseline

### `claimstab/baselines/tests/test_naive.py`
- Classes:
  - `TestNaiveBaseline` (methods: test_compare_overclaim, test_compare_underclaim, test_evaluate_returns_baseline_config)
- Top-level functions: _none_

### `claimstab/cache/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/cache/store.py`
- Classes:
  - `CacheStore` (methods: __init__, close, get, put)
- Top-level functions: _none_

### `claimstab/claims/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/claims/decision.py`
- Classes:
  - `TieBreak` (methods: -)
  - `DecisionClaimResult` (methods: -)
- Top-level functions: top_k_labels, decision_in_top_k, evaluate_decision_claim

### `claimstab/claims/diagnostics.py`
- Classes: _none_
- Top-level functions: _parse_ranking_claim, _parse_baseline_key, _key_to_config, _claim_margin, _matches_constraints, conditional_rank_flip_summary, single_knob_lockdown_recommendation, aggregate_lockdown_recommendations, _shots_bucket, _observed_condition_cell, _cell_key, _cell_stats_from_counts, _hamming_one_diff, _build_minimal_lockdown_set, build_conditional_robustness_summary, compute_effect_diagnostics, compute_stability_vs_shots, minimum_shots_for_stable, rank_flip_root_cause_by_dimension

### `claimstab/claims/distribution.py`
- Classes:
  - `DistributionClaimResult` (methods: -)
- Top-level functions: normalize_counts, _union_support, tvd_distance, _kl_divergence, js_distance, get_distance_fn, evaluate_distribution_claim

### `claimstab/claims/evaluation.py`
- Classes: _none_
- Top-level functions: perturbation_key, collect_paired_scores

### `claimstab/claims/ranking.py`
- Classes:
  - `HigherIsBetter` (methods: -)
  - `Relation` (methods: -)
  - `RankingClaim` (methods: holds, relation)
  - `RankFlip` (methods: flipped)
  - `RankFlipSummary` (methods: flip_rate)
- Top-level functions: compute_rank_flip_summary

### `claimstab/claims/stability.py`
- Classes: _none_
- Top-level functions: evaluate_binomial_with_policy, estimate_clustered_stability

### `claimstab/claims/tests/test_clustered_stability.py`
- Classes:
  - `TestClusteredStability` (methods: test_clustered_bootstrap_summary)
- Top-level functions: _rows

### `claimstab/claims/tests/test_decision.py`
- Classes:
  - `TestDecision` (methods: test_top_k_labels_lexicographic_tie_break, test_decision_in_top_k, test_evaluate_decision_claim_returns_conservative_status)
- Top-level functions: _none_

### `claimstab/claims/tests/test_diagnostics.py`
- Classes:
  - `TestDiagnostics` (methods: test_rank_flip_root_cause_by_dimension_counts_flips, test_conditional_summary_and_lockdown_recommendation, test_aggregate_lockdown_recommendations, test_conditional_robustness_summary_extracts_core_frontier_and_lockdown, test_effect_diagnostics_highlights_shots_bucket)
- Top-level functions: _none_

### `claimstab/claims/tests/test_distribution.py`
- Classes:
  - `TestDistribution` (methods: test_normalize_counts, test_tvd_and_js_identical_distributions_are_zero, test_evaluate_distribution_claim_primary_and_sanity)
- Top-level functions: _none_

### `claimstab/claims/tests/test_evaluation.py`
- Classes:
  - `TestEvaluation` (methods: test_collect_paired_scores_keeps_layout_dimension, test_collect_paired_scores_requires_both_methods)
- Top-level functions: _row

### `claimstab/claims/tests/test_inference_policy.py`
- Classes:
  - `_AlwaysInconclusivePolicy` (methods: interval, estimate, decide)
  - `TestInferencePolicy` (methods: test_default_policy_is_wilson, test_custom_policy_is_respected, test_resolve_policy_by_name, test_bayesian_policy_estimate, test_evaluate_with_policy_name)
- Top-level functions: _none_

### `claimstab/claims/tests/test_ranking_relation.py`
- Classes:
  - `TestRankingRelation` (methods: test_relation_three_way_higher_is_better, test_relation_three_way_lower_is_better, test_flip_uses_relation_change, test_larger_delta_can_reduce_near_tie_flips)
- Top-level functions: _none_

### `claimstab/claims/tests/test_stability.py`
- Classes:
  - `TestStability` (methods: test_conservative_decision_stable, test_conservative_decision_inconclusive, test_conservative_decision_unstable, test_ci_width_non_negative)
- Top-level functions: _none_

### `claimstab/claims/tests/test_stability_vs_shots.py`
- Classes:
  - `TestStabilityVsShots` (methods: test_minimum_shots_for_stable_detected, test_decision_uses_ci_low_not_point_estimate, test_single_point_case_returns_none_when_not_stable)
- Top-level functions: _score_pair_rows, _synthetic_rows_for_shot

### `claimstab/cli.py`
- Classes: _none_
- Top-level functions: build_parser, main

### `claimstab/commands/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/commands/_utils.py`
- Classes: _none_
- Top-level functions: run_subprocess

### `claimstab/commands/atlas.py`
- Classes: _none_
- Top-level functions: cmd_publish_result, cmd_validate_atlas, cmd_export_dataset_registry, cmd_atlas_compare

### `claimstab/commands/init_external_task.py`
- Classes: _none_
- Top-level functions: _slugify_name, _camel_from_slug, _module_path_for_python_file, cmd_init_external_task

### `claimstab/commands/misc.py`
- Classes: _none_
- Top-level functions: cmd_examples, cmd_export_definitions

### `claimstab/commands/report.py`
- Classes: _none_
- Top-level functions: cmd_report

### `claimstab/commands/run.py`
- Classes: _none_
- Top-level functions: _csv_or_string, _suite_name, _extract_sampling, _extract_deltas, _extract_claim_pairs, _has_explicit_ranking_claims, _extract_decision, _extract_space, _backend_engine, _infer_pipeline, _build_main_command, _to_csv_token_list, _build_multidevice_command, cmd_run

### `claimstab/commands/validate.py`
- Classes: _none_
- Top-level functions: cmd_validate_spec, cmd_validate_evidence

### `claimstab/core/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/core/events.py`
- Classes:
  - `ExecutionEvent` (methods: build, to_dict, from_dict)
  - `JsonlEventLogger` (methods: __init__, log)
- Top-level functions: _utc_now_iso

### `claimstab/core/trace.py`
- Classes:
  - `TraceRecord` (methods: from_score_row, to_score_row, to_dict, from_dict)
  - `TraceIndex` (methods: add, extend, save_jsonl, load_jsonl)
  - `ArtifactManifest` (methods: -)
- Top-level functions: _none_

### `claimstab/devices/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/devices/ibm_fake.py`
- Classes: _none_
- Top-level functions: _fake_provider_module, load_fake_backend, snapshot_from_backend, fingerprint

### `claimstab/devices/registry.py`
- Classes:
  - `ResolvedDeviceProfile` (methods: -)
- Top-level functions: parse_device_profile, parse_noise_model_mode, resolve_device_profile

### `claimstab/devices/spec.py`
- Classes:
  - `DeviceProfile` (methods: -)
- Top-level functions: _none_

### `claimstab/devices/tests/test_registry.py`
- Classes:
  - `TestDeviceRegistry` (methods: test_missing_device_profile_defaults_disabled, test_noise_model_default_none, test_ibm_fake_missing_dependency_raises_clean_error)
- Top-level functions: _none_

### `claimstab/evidence/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/evidence/protocol.py`
- Classes:
  - `EvidenceValidationResult` (methods: -)
- Top-level functions: _stable_hash, _load_schema_v1, _resolve_artifact_path, build_cep_protocol_meta, build_experiment_cep_record, validate_evidence_payload, validate_evidence_file

### `claimstab/figures/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/figures/attribution.py`
- Classes: _none_
- Top-level functions: _select_attribution_metric, plot_top_attribution_bars

### `claimstab/figures/baseline_compare.py`
- Classes: _none_
- Top-level functions: plot_naive_vs_claimstab

### `claimstab/figures/ci_shrink.py`
- Classes: _none_
- Top-level functions: plot_ci_width_vs_budget

### `claimstab/figures/cost_curve.py`
- Classes: _none_
- Top-level functions: _majority_label, plot_stability_vs_shots

### `claimstab/figures/heatmap.py`
- Classes: _none_
- Top-level functions: plot_fliprate_heatmap

### `claimstab/figures/loaders.py`
- Classes: _none_
- Top-level functions: load_claim_json, comparative_dataframe, rq_dataframe, load_scores_csv

### `claimstab/figures/robustness.py`
- Classes: _none_
- Top-level functions: plot_rq5_robustness_map, plot_rq6_decision_counts, plot_rq7_top_main_effects

### `claimstab/figures/style.py`
- Classes: _none_
- Top-level functions: apply_style, save_fig

### `claimstab/inference/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/inference/policies.py`
- Classes:
  - `StabilityDecision` (methods: -)
  - `BinomialEstimate` (methods: -)
  - `InferencePolicy` (methods: interval, estimate, decide)
  - `WilsonInferencePolicy` (methods: interval, estimate, decide)
  - `BayesianBetaPolicy` (methods: __init__, interval, estimate, decide)
- Top-level functions: resolve_inference_policy, wilson_interval, estimate_binomial_rate, estimate_stability_from_outcomes, conservative_stability_decision, ci_width

### `claimstab/io/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/io/runtime_meta.py`
- Classes: _none_
- Top-level functions: _safe_package_version, _safe_git, collect_runtime_metadata

### `claimstab/io/writers.py`
- Classes: _none_
- Top-level functions: write_scores_csv, compute_method_stats, write_summary_json

### `claimstab/methods/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/methods/spec.py`
- Classes:
  - `MethodSpec` (methods: __post_init__)
- Top-level functions: _none_

### `claimstab/perturbations/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/perturbations/operators.py`
- Classes:
  - `PerturbationOperator` (methods: apply)
  - `SeedTranspilerOperator` (methods: apply)
  - `OptimizationLevelOperator` (methods: apply)
  - `LayoutMethodOperator` (methods: apply)
  - `ShotsOperator` (methods: apply)
  - `SeedSimulatorOperator` (methods: apply)
- Top-level functions: base_config_for_space, iter_space_configs_via_operators

### `claimstab/perturbations/sampling.py`
- Classes:
  - `SamplingPolicy` (methods: -)
  - `AdaptiveSamplingResult` (methods: -)
- Top-level functions: normalize_repeats_to_seed_simulator, sample_configs, ensure_config_included, adaptive_sample_configs

### `claimstab/perturbations/space.py`
- Classes:
  - `PerturbationLevel` (methods: -)
  - `CompilationPerturbation` (methods: -)
  - `ExecutionPerturbation` (methods: -)
  - `PerturbationConfig` (methods: -)
  - `PerturbationSpace` (methods: iter_configs, iter_configs_with_operators, size, conf_level_default, day1_default, compilation_only, sampling_only, combined_light)
- Top-level functions: _none_

### `claimstab/perturbations/tests/test_operators.py`
- Classes:
  - `TestPerturbationOperators` (methods: test_single_operator_apply, test_operator_shim_matches_sampling_only_space, test_standalone_iter_space_configs_via_operators)
- Top-level functions: _none_

### `claimstab/perturbations/tests/test_sampling.py`
- Classes:
  - `TestSampling` (methods: test_full_factorial_sampling_returns_all, test_full_factorial_with_operator_shim_matches_default, test_random_k_sampling_respects_k, test_adaptive_mode_uses_max_budget_for_initial_pool, test_ensure_config_included_adds_missing_baseline, test_adaptive_sample_configs_stops_on_target_width)
- Top-level functions: _small_space

### `claimstab/perturbations/tests/test_space.py`
- Classes:
  - `TestSpace` (methods: test_baseline_space_constructs_and_has_expected_size)
- Top-level functions: _none_

### `claimstab/pipelines/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/pipelines/common.py`
- Classes: _none_
- Top-level functions: parse_csv_tokens, parse_deltas, parse_claim_pairs, try_load_spec, canonical_suite_name, canonical_space_name, make_space, build_baseline_config, config_key, key_sort_value, config_from_key, baseline_from_keys, build_evidence_ref, make_event_logger, _key_from_row, load_rows_from_trace_by_space, load_rows_from_trace_by_batch, write_rows_csv

### `claimstab/results/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/results/report_builder.py`
- Classes: _none_
- Top-level functions: build_report_html

### `claimstab/results/report_helpers.py`
- Classes: _none_
- Top-level functions: as_float, numeric_sort_key, report_plot_rc, decision_badge, decision_count, shots_warning, shots_diagnostic_text, executive_summary, legacy_to_experiment, relative_ref

### `claimstab/results/report_plots.py`
- Classes: _none_
- Top-level functions: plot_delta_curve, plot_shots_curve, plot_factor_attribution

### `claimstab/results/report_renderers.py`
- Classes: _none_
- Top-level functions: render_delta_table, render_comparative_table, render_device_summary_table, render_top_unstable, render_dimension_breakdown, render_lockdown_recommendations, render_conditional_robustness, render_stratified_stability, render_effect_diagnostics, render_shots_curve_table, render_auxiliary_claims, render_naive_summary, render_rq_summary, render_evidence_chain

### `claimstab/results/report_sections.py`
- Classes: _none_
- Top-level functions: available_sections_text, parse_sections_arg, is_section_enabled

### `claimstab/runners/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/runners/matrix_runner.py`
- Classes:
  - `ScoreRow` (methods: -)
  - `MatrixRunner` (methods: __init__, _circuit_digest, _config_dict, _fingerprint, run)
- Top-level functions: _none_

### `claimstab/runners/qiskit_aer.py`
- Classes:
  - `AerRunConfig` (methods: -)
  - `AerRunResult` (methods: -)
  - `QiskitAerRunner` (methods: __init__, _build_spot_check_noise_model, _transpiled_stats, _transpile_with_profile, run_counts, run_metric)
- Top-level functions: _none_

### `claimstab/runners/tests/test_matrix_runner.py`
- Classes:
  - `_Details` (methods: -)
  - `_Backend` (methods: __init__, run_metric)
  - `_Task` (methods: build)
  - `TestMatrixRunner` (methods: test_runner_uses_provided_sampled_configs, test_runner_supports_structural_metric_name, test_default_objective_path_is_device_neutral, test_cache_hit_skips_backend_execution)
- Top-level functions: _none_

### `claimstab/runners/tests/test_qiskit_aer.py`
- Classes:
  - `TestQiskitAerRunner` (methods: _toy_circuit, test_spot_check_noise_requires_aer_engine, test_aer_requested_without_package_raises, test_spot_check_noise_initializes_when_aer_available, test_default_run_has_no_device_metadata, test_transpile_only_returns_structural_stats, test_noisy_sim_produces_counts_when_available)
- Top-level functions: _none_

### `claimstab/scripts/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/scripts/check_expected.py`
- Classes: _none_
- Top-level functions: parse_args, run_tiny_experiment, check_outputs, main

### `claimstab/scripts/generate_implementation_catalog.py`
- Classes:
  - `ClassInfo` (methods: -)
  - `ModuleInfo` (methods: -)
- Top-level functions: parse_args, _repo_root, _tracked_files, _module_info, _section_files, _render_file_list, _render_module_list, build_catalog_markdown, main

### `claimstab/scripts/generate_stability_report.py`
- Classes: _none_
- Top-level functions: parse_args, main

### `claimstab/scripts/make_paper_figures.py`
- Classes: _none_
- Top-level functions: _collect_naive_rows, _collect_shots_rows, _collect_adaptive_rows, parse_args, main

### `claimstab/scripts/plot_heatmap.py`
- Classes: _none_
- Top-level functions: main

### `claimstab/scripts/reproduce_paper.py`
- Classes: _none_
- Top-level functions: _run, parse_args, _render_reports, main

### `claimstab/spec/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/spec/tests/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/spec/tests/test_validate.py`
- Classes:
  - `TestSpecValidation` (methods: test_defaults_apply_backward_compatibility, test_validate_accepts_minimal_v1, test_validate_rejects_invalid_sampling_mode, test_load_spec_from_yaml, test_validate_allows_external_task_and_custom_suite, test_defaults_map_legacy_repeats_to_seed_simulator)
- Top-level functions: _none_

### `claimstab/spec/validate.py`
- Classes: _none_
- Top-level functions: load_yaml, apply_spec_defaults, _load_schema_v1, _validate_fallback, validate_spec, load_spec

### `claimstab/tasks/__init__.py`
- Classes: _none_
- Top-level functions: _none_

### `claimstab/tasks/base.py`
- Classes:
  - `TaskError` (methods: -)
  - `TaskSpecError` (methods: -)
  - `BuiltWorkflow` (methods: -)
  - `TaskPlugin` (methods: instances, build)
- Top-level functions: _none_

### `claimstab/tasks/bernstein_vazirani.py`
- Classes:
  - `BVInstance` (methods: -)
  - `BernsteinVaziraniTaskPlugin` (methods: __init__, instances, build, _build_bv_oracle, _build_random_baseline)
- Top-level functions: _legacy_default_hidden_strings, _generate_hidden_strings_for_n

### `claimstab/tasks/factory.py`
- Classes:
  - `TaskConfig` (methods: -)
- Top-level functions: _default_methods, parse_task_config, make_task, parse_methods

### `claimstab/tasks/ghz_structural.py`
- Classes:
  - `GHZInstance` (methods: -)
  - `GHZStructuralTaskPlugin` (methods: __init__, instances, build, _build_ghz_linear, _build_ghz_star, _build_random_baseline)
- Top-level functions: _none_

### `claimstab/tasks/graphs.py`
- Classes:
  - `GraphInstance` (methods: -)
- Top-level functions: ring, erdos_renyi, core_suite, standard_suite, large_suite, day1_suite, day2_suite, day2_large_suite

### `claimstab/tasks/instances.py`
- Classes:
  - `ProblemInstance` (methods: -)
- Top-level functions: _none_

### `claimstab/tasks/maxcut.py`
- Classes:
  - `MaxCutTask` (methods: __init__, build, _build_qaoa_circuit, _build_random_baseline, _expectation_metric, _cut_value)
  - `MaxCutTaskPlugin` (methods: __init__, instances, build)
- Top-level functions: _none_

### `claimstab/tasks/registry.py`
- Classes: _none_
- Top-level functions: register_task, get_task_class, load_external_task, registered_tasks, ensure_builtin_tasks_registered

### `claimstab/tasks/suites.py`
- Classes: _none_
- Top-level functions: _default_data_dir, _load_suite_json, load_suite

### `claimstab/tasks/tests/test_bernstein_vazirani.py`
- Classes:
  - `TestBernsteinVaziraniTask` (methods: test_instances_and_build, test_large_suite_has_30_instances, test_small_qubit_range_is_capped_by_unique_capacity)
- Top-level functions: _none_

### `claimstab/tasks/tests/test_factory.py`
- Classes:
  - `TestTaskFactory` (methods: test_parse_methods_default, test_parse_methods_default_bv, test_make_task_builtin_maxcut, test_make_task_external_module_class)
- Top-level functions: _none_

### `claimstab/tasks/tests/test_ghz_structural.py`
- Classes:
  - `TestGHZStructuralTask` (methods: test_instances_cover_qubit_range, test_supported_methods_build, test_factory_builtin_ghz)
- Top-level functions: _none_

### `claimstab/tasks/tests/test_maxcut.py`
- Classes:
  - `TestMaxCutQAOA` (methods: setUp, test_qaoa_binds_all_parameters, test_qaoa_has_measurements, test_qaoa_qubit_count)
  - `TestGraphSuites` (methods: test_large_suite_has_expected_size_and_unique_ids)
- Top-level functions: _none_

### `claimstab/tasks/tests/test_suites.py`
- Classes:
  - `TestSuites` (methods: test_load_standard_suite, test_alias_day2_maps_to_standard)
- Top-level functions: _none_

### `claimstab/templates/claim_skeleton.py`
- Classes:
  - `MyClaim` (methods: holds)
- Top-level functions: evaluate_my_claim

### `claimstab/templates/runner_skeleton.py`
- Classes:
  - `RunResult` (methods: -)
  - `MyRunner` (methods: run_one)
- Top-level functions: _none_

### `claimstab/templates/task_skeleton.py`
- Classes:
  - `MyPayload` (methods: -)
  - `MyTaskPlugin` (methods: __init__, instances, build)
- Top-level functions: _none_

### `claimstab/tests/test_cli.py`
- Classes:
  - `TestCLI` (methods: test_init_external_task_starter, test_examples_subcommand, test_validate_spec_subcommand, test_validate_evidence_subcommand, test_run_dry_run_main, test_run_dry_run_main_with_debug_attribution_flag, test_run_dry_run_main_with_trace_cache_flags, test_run_dry_run_external_task, test_run_dry_run_multidevice_with_trace_flags, test_run_dry_run_bv_decision_only_no_ranking_pairs, test_export_definitions, test_publish_result_and_validate_atlas, test_export_dataset_registry, test_atlas_compare_command)
- Top-level functions: _none_

### `claimstab/tests/test_evidence_protocol.py`
- Classes:
  - `TestEvidenceProtocol` (methods: test_validate_evidence_payload_passes_with_matching_trace, test_validate_evidence_payload_flags_unmatched_query, test_validate_evidence_file_roundtrip)
- Top-level functions: _write_trace, _valid_payload

### `claimstab/tests/test_figures_attribution.py`
- Classes:
  - `TestAttributionFigure` (methods: test_prefers_driver_score_when_available, test_fallback_uses_flip_rate_from_counts)
- Top-level functions: _none_

### `claimstab/tests/test_figures_robustness.py`
- Classes:
  - `TestRobustnessFigures` (methods: test_plot_rq5_robustness_map, test_plot_rq6_decision_counts, test_plot_rq7_top_main_effects)
- Top-level functions: _none_

### `claimstab/tests/test_multidevice_replay.py`
- Classes:
  - `TestMultideviceReplaySmoke` (methods: test_transpile_only_replay_trace)
- Top-level functions: _none_

### `claimstab/tests/test_pipeline_common.py`
- Classes:
  - `TestPipelineCommon` (methods: test_parse_deltas_requires_non_empty, test_parse_claim_pairs_supports_fallback, test_canonical_aliases, test_make_space_combined_light_override, test_baseline_helpers)
- Top-level functions: _none_

### `claimstab/tests/test_report_section_registry.py`
- Classes:
  - `TestReportSectionRegistry` (methods: test_available_sections_text_contains_known_ids, test_parse_sections_arg_empty_returns_none, test_parse_sections_arg_returns_set, test_is_section_enabled)
- Top-level functions: _none_

### `claimstab/tests/test_report_sections.py`
- Classes:
  - `TestReportSections` (methods: _payload, _run_report, test_default_includes_naive_and_delta_sections, test_custom_sections_can_hide_naive)
- Top-level functions: _none_

### `claimstab/tests/test_smoke_demo.py`
- Classes:
  - `TestSmokeDemo` (methods: _run_demo, test_maxcut_ranking_smoke, test_bv_decision_smoke, test_replay_trace_smoke)
- Top-level functions: _none_

### `claimstab/tests/test_trace_cache.py`
- Classes:
  - `TestTraceAndCache` (methods: _row, test_trace_roundtrip, test_trace_index_save_load_jsonl, test_cache_store_put_get)
- Top-level functions: _none_

### `claimstab/utils.py`
- Classes: _none_
- Top-level functions: _viz_rc, _infer_two_methods, _build_diff_matrix, plot_heatmap, plot_scatter

## Example Python Modules

### `examples/atlas_bv_workflow.py`
- Classes: _none_
- Top-level functions: parse_args, _run_command, main

### `examples/claim_stability_demo.py`
- Classes: _none_
- Top-level functions: _none_

### `examples/community_contrib_demo/portfolio_task.py`
- Classes:
  - `PortfolioPayload` (methods: -)
  - `PortfolioAllocationTask` (methods: __init__, instances, build)
- Top-level functions: _make_weights

### `examples/custom_task_demo/toy_task.py`
- Classes:
  - `ToyPayload` (methods: -)
  - `ToyTask` (methods: __init__, instances, build)
- Top-level functions: _none_

### `examples/exp_comprehensive_calibration.py`
- Classes: _none_
- Top-level functions: parse_args, main

### `examples/exp_comprehensive_large.py`
- Classes: _none_
- Top-level functions: parse_args, main

### `examples/exp_structural_compilation.py`
- Classes: _none_
- Top-level functions: parse_args, main

### `examples/multidevice_demo.py`
- Classes: _none_
- Top-level functions: _none_
