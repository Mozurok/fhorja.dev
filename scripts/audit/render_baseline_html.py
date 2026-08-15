#!/usr/bin/env python3
"""render_baseline_html.py -- render the baseline audit JSON as one self-contained page.

Python stdlib only. The JSON produced by scripts/audit/baseline_audit.py is the
artifact of record; this script is a view of it and adds no facts of its own.

The page embeds the JSON inline and builds every table and the reference graph
from it in vanilla JavaScript. No external requests, no CDN, no network fonts,
no library.

Usage:
  python3 scripts/audit/render_baseline_html.py --json docs/audit/X.json \
      --out docs/audit/X.html
"""

import argparse
import html
import json
import os
import sys

RENDER_VERSION = "1.0.0"


# --------------------------------------------------------------------------
# View spec: one entry per check. Every "path" is resolved inside the check
# object at render time; a missing path renders a stated reason, never an error.
# --------------------------------------------------------------------------

def col(key, label, kind="text"):
    return {"key": key, "label": label, "kind": kind}


VIEW = [
    {
        "id": "check_01_counts",
        "title": "1. Counts",
        "lead": ("Command count as reported by each surface, then every "
                 "<!-- count:KIND --> marker in the tree."),
        "blocks": [
            {"type": "table", "path": "command_count_sources",
             "label": "Command count by source",
             "columns": [col("source", "Source"), col("value", "Value", "num"),
                         col("location", "Location"), col("note", "Note")]},
            {"type": "kv", "path": "count_markers_compared",
             "label": "Count markers compared against disk"},
            {"type": "kv", "path": "count_markers_out_of_scan_set",
             "label": "Count markers outside the lint scan-set"},
            {"type": "table", "path": "count_marker_walk_exclusions",
             "label": "Directories excluded from the marker walk",
             "columns": [col("path", "Path"), col("reason", "Reason")]},
            {"type": "table", "path": "count_markers", "label": "Count markers",
             "columns": [col("file", "File"), col("line", "Line", "num"),
                         col("kind", "Kind"), col("declared", "Declared", "num"),
                         col("disk", "On disk", "num"),
                         col("compared", "Compared", "bool"),
                         col("reason", "Reason")]},
        ],
    },
    {
        "id": "check_02_registry_integrity",
        "title": "2. Registry integrity",
        "lead": ("Every command against the four registries lint enforces, plus "
                 "cluster membership in both directions."),
        "blocks": [
            {"type": "kvmap", "path": "registries", "label": "Entries per registry",
             "key_label": "Registry", "value_label": "Entries"},
            {"type": "table", "path": "commands_missing_from_a_registry",
             "label": "Commands missing from a registry",
             "columns": [col("command", "Command"),
                         col("missing_from", "Missing from")]},
            {"type": "table", "path": "orphan_registry_entries",
             "label": "Registry entries with no command file",
             "columns": [col("registry", "Registry"), col("entry", "Entry")]},
            {"type": "list", "path": "commands_in_no_cluster",
             "label": "Commands in no cluster"},
            {"type": "list", "path": "clusters_with_no_members",
             "label": "Clusters with no members"},
            {"type": "table", "path": "cluster_membership_counts",
             "label": "Cluster membership",
             "columns": [col("cluster", "Cluster"), col("members", "Members", "num")]},
            {"type": "note", "path": "taxonomy_note"},
            {"type": "list", "path": "spec_clusters_with_no_matching_category_value",
             "label": "Spec clusters with no matching frontmatter category value"},
            {"type": "list", "path": "category_values_with_no_matching_spec_cluster",
             "label": "Frontmatter category values with no matching spec cluster"},
            {"type": "table", "path": "spec_cluster_by_frontmatter_category",
             "label": "Spec cluster by frontmatter category",
             "columns": [col("spec_cluster", "Spec cluster"),
                         col("frontmatter_category", "Frontmatter category"),
                         col("commands", "Commands", "num")]},
            {"type": "table",
             "path": "frontmatter_category_vs_spec_cluster_disagreements",
             "label": "Per-command disagreements where both taxonomies overlap",
             "columns": [col("command", "Command"),
                         col("frontmatter_category", "Frontmatter category"),
                         col("spec_cluster", "Spec cluster")]},
        ],
    },
    {
        "id": "check_03_shared_block_drift",
        "title": "3. Shared block drift",
        "lead": "Each inlined copy compared against commands/_shared/.",
        "blocks": [
            {"type": "note", "path": "method"},
            {"type": "kv", "path": "markers_total", "label": "Shared markers found"},
            {"type": "kv", "path": "blocks_on_disk", "label": "Canonical blocks on disk"},
            {"type": "table", "path": "files_with_drifted_copy",
             "label": "Files whose copy differs from source",
             "columns": [col("file", "File"), col("line", "Line", "num"),
                         col("block", "Block"),
                         col("observed_chars", "Copy chars", "num"),
                         col("canonical_chars", "Canonical chars", "num")]},
            {"type": "table", "path": "files_referencing_a_missing_block",
             "label": "Files referencing a block that no longer exists",
             "columns": [col("file", "File"), col("line", "Line", "num"),
                         col("block", "Block")]},
            {"type": "list", "path": "shared_blocks_with_no_consumer",
             "label": "Shared blocks with no consumer"},
            {"type": "table", "path": "usage_per_block", "label": "Markers per block",
             "columns": [col("block", "Block"), col("markers", "Markers", "num")]},
        ],
    },
    {
        "id": "check_04_cross_reference_integrity",
        "title": "4. Cross-reference integrity",
        "lead": "Path-shaped references from command files and shared blocks.",
        "blocks": [
            {"type": "note", "path": "classification_rule"},
            {"type": "kv", "path": "path_references_resolved", "label": "References resolved"},
            {"type": "table", "path": "path_references_broken",
             "label": "References whose target does not exist",
             "columns": [col("file", "File"), col("line", "Line", "num"),
                         col("ref", "Reference")]},
            {"type": "table", "path": "path_references_outside_the_tree_by_prefix",
             "label": "References pointing outside this tree, by prefix",
             "columns": [col("prefix", "Prefix"), col("references", "References", "num")]},
            {"type": "table", "path": "path_references_outside_the_tree",
             "label": "References pointing outside this tree",
             "columns": [col("file", "File"), col("line", "Line", "num"),
                         col("ref", "Reference")]},
            {"type": "list", "path": "templates_referenced_by_no_command",
             "label": "templates/ files no command references"},
            {"type": "list", "path": "wos_topics_referenced_by_no_command",
             "label": "wos/ topics no command references"},
            {"type": "list", "path": "scripts_referenced_by_no_command",
             "label": "scripts/ files no command references"},
            {"type": "table", "path": "most_referenced_targets",
             "label": "Most referenced targets",
             "columns": [col("target", "Target"), col("references", "References", "num")]},
        ],
    },
    {
        "id": "check_05_adr_coverage",
        "title": "5. ADR coverage",
        "lead": "Files against the index, numbering, and command citations.",
        "blocks": [
            {"type": "kv", "path": "adr_files", "label": "ADR files"},
            {"type": "kv", "path": "index_rows", "label": "Index rows"},
            {"type": "kv", "path": "highest_number", "label": "Highest number"},
            {"type": "list", "path": "numbering_gaps", "label": "Numbering gaps"},
            {"type": "table", "path": "duplicate_numbers", "label": "Duplicate numbers",
             "columns": [col("number", "Number"), col("files", "Files")]},
            {"type": "list", "path": "files_missing_an_index_row",
             "label": "ADR files with no index row"},
            {"type": "list", "path": "index_rows_without_a_file",
             "label": "Index rows with no file"},
            {"type": "table", "path": "superseded_adrs", "label": "Superseded ADRs",
             "columns": [col("adr", "ADR"), col("status", "Status")]},
            {"type": "table", "path": "superseded_adrs_still_cited_by_a_command",
             "label": "Superseded ADRs still cited from a command",
             "columns": [col("adr", "ADR"), col("status", "Status"),
                         col("citations", "Citing commands")]},
            {"type": "list", "path": "adrs_cited_by_a_command_with_no_file",
             "label": "ADRs cited by a command with no file on disk"},
            {"type": "table", "path": "citation_counts",
             "label": "Most cited ADRs",
             "columns": [col("adr", "ADR"), col("commands", "Citing commands", "num")]},
        ],
    },
    {
        "id": "check_06_eval_coverage",
        "title": "6. Eval coverage",
        "lead": "Per command and per cluster, from two independent signals.",
        "blocks": [
            {"type": "note", "path": "method"},
            {"type": "kv", "path": "scenarios_total", "label": "Scenarios on disk"},
            {"type": "kvmap", "path": "totals", "label": "Totals",
             "key_label": "Metric", "value_label": "Value"},
            {"type": "table", "path": "per_cluster", "label": "Coverage per cluster",
             "columns": [col("cluster", "Cluster"), col("commands", "Commands", "num"),
                         col("tagged_covered", "Tagged", "num"),
                         col("tagged_percent", "Tagged pct", "num"),
                         col("mentioned_covered", "Mentioned", "num"),
                         col("mentioned_percent", "Mentioned pct", "num")]},
            {"type": "list", "path": "clusters_with_zero_tagged_coverage",
             "label": "Clusters with zero tagged coverage"},
            {"type": "list", "path": "clusters_with_zero_mention_coverage",
             "label": "Clusters with zero mention coverage"},
            {"type": "list", "path": "commands_with_zero_coverage",
             "label": "Commands with zero coverage"},
            {"type": "table", "path": "per_command", "label": "Coverage per command",
             "columns": [col("command", "Command"), col("cluster", "Cluster"),
                         col("tagged_count", "Tagged", "num"),
                         col("mentioned_count", "Mentioned", "num"),
                         col("tagged_scenarios", "Tagged scenarios")]},
        ],
    },
    {
        "id": "check_07_skills_conformance",
        "title": "7. Skills spec conformance",
        "lead": "Built Agent Skills under .claude/skills/.",
        "blocks": [
            {"type": "kvmap", "path": "limits", "label": "Limits applied",
             "key_label": "Limit", "value_label": "Value"},
            {"type": "kv", "path": "skills_total", "label": "Skills built"},
            {"type": "list", "path": "over_body_limit", "label": "Over the body-line limit"},
            {"type": "list", "path": "over_description_limit",
             "label": "Over the description-character limit"},
            {"type": "list", "path": "missing_a_required_field",
             "label": "Missing a required frontmatter field"},
            {"type": "list", "path": "commands_without_a_built_skill",
             "label": "Commands with no built skill"},
            {"type": "table", "path": "per_skill", "label": "Per skill",
             "columns": [col("skill", "Skill"), col("body_lines", "Body lines", "num"),
                         col("description_chars", "Description chars", "num"),
                         col("missing_required_fields", "Missing fields"),
                         col("name_matches_directory", "Name matches dir", "bool"),
                         col("has_canonical_command", "Has command", "bool")]},
        ],
    },
    {
        "id": "check_08_token_footprint",
        "title": "8. Token footprint",
        "lead": "Approximate token count per command file, and per install profile.",
        "blocks": [
            {"type": "note", "path": "method"},
            {"type": "note", "path": "budget_statement_note"},
            {"type": "kv", "path": "per_profile_budget_stated",
             "label": "Per-profile budget stated in wos/context-budget.md"},
            {"type": "profiles", "path": "profile_totals", "label": "Totals per profile"},
            {"type": "table", "path": "ten_largest", "label": "Ten largest command files",
             "columns": [col("command", "Command"), col("cluster", "Cluster"),
                         col("approx_tokens", "Approx tokens", "num"),
                         col("chars", "Chars", "num"), col("profiles", "Profiles")]},
            {"type": "table", "path": "numeric_budget_statements_found",
             "label": "Numeric token statements found in wos/context-budget.md",
             "columns": [col("line", "Line", "num"), col("text", "Text")]},
            {"type": "table", "path": "per_command", "label": "Per command",
             "columns": [col("command", "Command"), col("cluster", "Cluster"),
                         col("approx_tokens", "Approx tokens", "num"),
                         col("chars", "Chars", "num"), col("shape", "Shape"),
                         col("profiles", "Profiles")]},
        ],
    },
    {
        "id": "check_09_claim_consistency",
        "title": "9. Claim consistency",
        "lead": "Prose claims in the user-facing surfaces against disk.",
        "blocks": [
            {"type": "list", "path": "surfaces_scanned", "label": "Surfaces scanned"},
            {"type": "list", "path": "surfaces_absent", "label": "Surfaces absent"},
            {"type": "kvmap", "path": "on_disk_reference_values",
             "label": "On-disk reference values", "key_label": "Value",
             "value_label": "Count"},
            {"type": "table", "path": "numeric_claims", "label": "Numeric claims",
             "columns": [col("kind", "Kind"), col("surface", "Surface"),
                         col("line", "Line", "num"), col("claimed", "Claimed", "num"),
                         col("on_disk", "On disk", "num"),
                         col("matches", "Matches", "bool"), col("basis", "Basis"),
                         col("text", "Text")]},
            {"type": "table", "path": "license_declarations", "label": "License declarations",
             "columns": [col("source", "Source"), col("value", "Value"),
                         col("note", "Note")]},
            {"type": "table", "path": "license_mismatches", "label": "License mismatches",
             "columns": [col("source", "Source"), col("value", "Value")]},
            {"type": "note", "path": "harness_note"},
            {"type": "harness", "path": "harness_names_per_surface",
             "label": "Harness names per surface"},
            {"type": "kvmap", "path": "harness_on_disk_evidence",
             "label": "In-repo integration files", "key_label": "Path",
             "value_label": "Exists"},
        ],
    },
    {
        "id": "check_10_staleness",
        "title": "10. Staleness",
        "lead": "Last commit date per command file.",
        "blocks": [
            {"type": "note", "path": "method"},
            {"type": "kvmap", "path": "launch_commit", "label": "Launch commit",
             "key_label": "Field", "value_label": "Value"},
            {"type": "table", "path": "ten_least_recently_touched",
             "label": "Ten least recently touched",
             "columns": [col("command", "Command"), col("cluster", "Cluster"),
                         col("last_commit_date", "Last commit")]},
            {"type": "table", "path": "untouched_since_before_launch",
             "label": "Untouched since before the launch commit",
             "columns": [col("command", "Command"), col("cluster", "Cluster"),
                         col("last_commit_date", "Last commit")]},
            {"type": "list", "path": "commands_with_no_commit_record",
             "label": "Commands with no commit record"},
            {"type": "table", "path": "per_command", "label": "Per command",
             "columns": [col("command", "Command"), col("cluster", "Cluster"),
                         col("last_commit_date", "Last commit"), col("path", "Path")]},
        ],
    },
    {
        "id": "check_11_reference_graph",
        "title": "11. Reference graph",
        "lead": "Directed command-to-command reference graph.",
        "blocks": [
            {"type": "note", "path": "method"},
            {"type": "kv", "path": "edge_count", "label": "Edges (per kind)"},
            {"type": "kv", "path": "distinct_pair_count", "label": "Distinct source-target pairs"},
            {"type": "kv", "path": "distinct_pair_count_excl_shared",
             "label": "Distinct pairs excluding shared-block text"},
            {"type": "graph", "path": "nodes", "label": "Graph"},
            {"type": "table", "path": "edge_kinds", "label": "Edges by kind",
             "columns": [col("kind", "Kind"), col("edges", "Edges", "num")]},
            {"type": "table", "path": "ten_highest_fan_in", "label": "Ten highest fan-in",
             "columns": [col("id", "Command"), col("cluster", "Cluster"),
                         col("fan_in_distinct", "Fan-in", "num"),
                         col("fan_in_edges", "Fan-in edges", "num")]},
            {"type": "table", "path": "ten_highest_fan_out", "label": "Ten highest fan-out",
             "columns": [col("id", "Command"), col("cluster", "Cluster"),
                         col("fan_out_distinct", "Fan-out", "num"),
                         col("fan_out_edges", "Fan-out edges", "num")]},
            {"type": "table", "path": "ten_highest_fan_in_excl_shared",
             "label": "Ten highest fan-in, excluding shared-block text",
             "columns": [col("id", "Command"), col("cluster", "Cluster"),
                         col("fan_in_distinct_excl_shared", "Fan-in", "num")]},
            {"type": "table", "path": "ten_highest_fan_out_excl_shared",
             "label": "Ten highest fan-out, excluding shared-block text",
             "columns": [col("id", "Command"), col("cluster", "Cluster"),
                         col("fan_out_distinct_excl_shared", "Fan-out", "num")]},
            {"type": "table", "path": "nodes", "label": "All nodes",
             "columns": [col("id", "Command"), col("cluster", "Cluster"),
                         col("approx_tokens", "Approx tokens", "num"),
                         col("fan_in_distinct", "Fan-in", "num"),
                         col("fan_out_distinct", "Fan-out", "num"),
                         col("fan_in_distinct_excl_shared", "Fan-in excl shared", "num"),
                         col("fan_out_distinct_excl_shared", "Fan-out excl shared", "num"),
                         col("shape", "Shape")]},
            {"type": "table", "path": "edges", "label": "All edges",
             "columns": [col("source", "Source"), col("target", "Target"),
                         col("kind", "Kind"), col("line", "Line", "num")]},
        ],
    },
    {
        "id": "check_12_reachability",
        "title": "12. Reachability",
        "lead": "Breadth-first walk from the commands named in wos/entry-points.md.",
        "blocks": [
            {"type": "kv", "path": "seed_source", "label": "Seed source"},
            {"type": "kv", "path": "seed_count", "label": "Seeds"},
            {"type": "kv", "path": "reachable_count", "label": "Reachable"},
            {"type": "kv", "path": "unreachable_count", "label": "Unreachable"},
            {"type": "note", "path": "excl_shared_note"},
            {"type": "kv", "path": "reachable_count_excl_shared",
             "label": "Reachable excluding shared-block edges"},
            {"type": "kv", "path": "unreachable_count_excl_shared",
             "label": "Unreachable excluding shared-block edges"},
            {"type": "list", "path": "seeds", "label": "Seed commands"},
            {"type": "table", "path": "unreachable", "label": "Unreachable commands",
             "columns": [col("command", "Command"), col("cluster", "Cluster")]},
            {"type": "table", "path": "unreachable_excl_shared",
             "label": "Unreachable when shared-block edges are excluded",
             "columns": [col("command", "Command"), col("cluster", "Cluster")]},
            {"type": "table", "path": "depth_histogram", "label": "Depth histogram",
             "columns": [col("depth", "Depth", "num"), col("commands", "Commands", "num")]},
            {"type": "table", "path": "per_command_depth", "label": "Per command",
             "columns": [col("command", "Command"), col("cluster", "Cluster"),
                         col("reachable", "Reachable", "bool"),
                         col("depth", "Depth", "num"),
                         col("reachable_excl_shared", "Reachable excl shared", "bool"),
                         col("depth_excl_shared", "Depth excl shared", "num")]},
        ],
    },
    {
        "id": "check_13_cluster_coupling",
        "title": "13. Cluster coupling",
        "lead": "Intra-cluster and cross-cluster edges, and the cluster matrix.",
        "blocks": [
            {"type": "note", "path": "method"},
            {"type": "table", "path": "per_cluster", "label": "Per cluster",
             "columns": [col("cluster", "Cluster"), col("members", "Members", "num"),
                         col("intra_cluster_edges", "Intra", "num"),
                         col("cross_cluster_edges", "Cross", "num"),
                         col("intra_cluster_edges_excl_shared", "Intra excl shared", "num"),
                         col("cross_cluster_edges_excl_shared", "Cross excl shared", "num")]},
            {"type": "matrix", "path": "matrix", "label": "Cluster-to-cluster edge counts"},
            {"type": "table", "path": "matrix", "label": "Matrix as rows",
             "columns": [col("from", "From"), col("to", "To"), col("edges", "Edges", "num")]},
        ],
    },
    {
        "id": "check_14_churn",
        "title": "14. Churn",
        "lead": "Commits and lines changed per command file.",
        "blocks": [
            {"type": "kvmap", "path": "launch_commit", "label": "Launch commit",
             "key_label": "Field", "value_label": "Value"},
            {"type": "note", "path": "since_launch_reason"},
            {"type": "table", "path": "ten_highest_commit_count",
             "label": "Ten highest commit count",
             "columns": [col("command", "Command"),
                         col("commits_all_time", "Commits", "num"),
                         col("lines_changed_all_time", "Lines changed", "num"),
                         col("commits_since_launch", "Commits since launch", "num"),
                         col("lines_changed_since_launch", "Lines since launch", "num")]},
            {"type": "table", "path": "ten_lowest_commit_count",
             "label": "Ten lowest commit count",
             "columns": [col("command", "Command"),
                         col("commits_all_time", "Commits", "num"),
                         col("lines_changed_all_time", "Lines changed", "num")]},
            {"type": "table", "path": "ten_highest_lines_changed",
             "label": "Ten highest lines changed",
             "columns": [col("command", "Command"),
                         col("lines_changed_all_time", "Lines changed", "num"),
                         col("commits_all_time", "Commits", "num")]},
            {"type": "table", "path": "ten_lowest_lines_changed",
             "label": "Ten lowest lines changed",
             "columns": [col("command", "Command"),
                         col("lines_changed_all_time", "Lines changed", "num"),
                         col("commits_all_time", "Commits", "num")]},
            {"type": "table", "path": "per_command", "label": "Per command",
             "columns": [col("command", "Command"), col("cluster", "Cluster"),
                         col("commits_all_time", "Commits", "num"),
                         col("added_all_time", "Added", "num"),
                         col("deleted_all_time", "Deleted", "num"),
                         col("lines_changed_all_time", "Lines changed", "num"),
                         col("commits_since_launch", "Commits since launch", "num"),
                         col("lines_changed_since_launch", "Lines since launch", "num")]},
        ],
    },
    {
        "id": "check_15_cochange_coupling",
        "title": "15. Co-change coupling",
        "lead": "Command file pairs appearing in the same commit three or more times.",
        "blocks": [
            {"type": "kv", "path": "threshold", "label": "Threshold"},
            {"type": "kv", "path": "pairs_total_observed", "label": "Pairs observed at least once"},
            {"type": "kv", "path": "pairs_at_or_above_threshold", "label": "Pairs at or above threshold"},
            {"type": "kv", "path": "commits_touching_commands", "label": "Commits touching commands/"},
            {"type": "table", "path": "commit_size_histogram",
             "label": "Command files touched per commit",
             "columns": [col("command_files_in_commit", "Command files", "num"),
                         col("commits", "Commits", "num")]},
            {"type": "table", "path": "pairs", "label": "Pairs",
             "columns": [col("a", "A"), col("b", "B"),
                         col("commits_together", "Commits together", "num"),
                         col("same_cluster", "Same cluster", "bool"),
                         col("cluster_a", "Cluster A"), col("cluster_b", "Cluster B")]},
        ],
    },
    {
        "id": "check_16_section_vocabulary",
        "title": "16. Section vocabulary",
        "lead": "Heading frequency across command files.",
        "blocks": [
            {"type": "kv", "path": "commands_scanned", "label": "Commands scanned"},
            {"type": "kv", "path": "distinct_headings", "label": "Distinct headings"},
            {"type": "table", "path": "majority_headings",
             "label": "Headings used by more than half of commands",
             "columns": [col("heading", "Heading"),
                         col("commands_with", "Commands with", "num"),
                         col("percent", "Percent", "num"),
                         col("missing_count", "Missing", "num"),
                         col("commands_missing", "Commands missing")]},
            {"type": "table", "path": "frequency", "label": "Heading frequency",
             "columns": [col("heading", "Heading"), col("commands", "Commands", "num"),
                         col("percent", "Percent", "num")]},
            {"type": "table", "path": "per_command_heading_count",
             "label": "Headings per command",
             "columns": [col("command", "Command"), col("headings", "Headings", "num")]},
        ],
    },
    {
        "id": "check_17_external_surface",
        "title": "17. External surface inventory",
        "lead": "Commands whose own text names a fetch, network, or third-party ingest mechanism.",
        "blocks": [
            {"type": "note", "path": "note"},
            {"type": "kv", "path": "commands_with_an_external_surface",
             "label": "Commands with an external surface"},
            {"type": "kv", "path": "commands_scanned", "label": "Commands scanned"},
            {"type": "list", "path": "patterns_scanned", "label": "Patterns scanned"},
            {"type": "external", "path": "per_command", "label": "Per command"},
            {"type": "table", "path": "shared_blocks_naming_a_mechanism",
             "label": "Shared blocks naming a mechanism",
             "columns": [col("shared_block", "Shared block"),
                         col("mechanism_labels", "Mechanisms")]},
        ],
    },
    {
        "id": "check_18_near_duplicate_text",
        "title": "18. Near-duplicate text",
        "lead": "Paragraph blocks compared by word shingles and Jaccard similarity.",
        "blocks": [
            {"type": "kvmap", "path": "parameters", "label": "Parameters",
             "key_label": "Parameter", "value_label": "Value"},
            {"type": "kv", "path": "paragraphs_compared", "label": "Paragraphs compared"},
            {"type": "kv", "path": "pairs_above_threshold", "label": "Pairs above threshold"},
            {"type": "table", "path": "pairs", "label": "Pairs above threshold",
             "columns": [col("score", "Score", "num"),
                         col("a_file", "File A"), col("a_lines", "Lines A"),
                         col("b_file", "File B"), col("b_lines", "Lines B"),
                         col("a_excerpt", "Excerpt")]},
        ],
    },
]


CSS = """
:root {
  color-scheme: light dark;
  --bg: #ffffff;
  --bg-alt: #f4f5f7;
  --bg-raise: #ffffff;
  --fg: #16181d;
  --fg-dim: #5a6070;
  --line: #d8dbe2;
  --line-soft: #e8eaef;
  --accent: #1f5fd0;
  --flag-bg: #fdeeee;
  --flag-fg: #96201f;
  --flag-line: #e5b3b2;
  --ok-fg: #1c6b40;
  --chip: #eceef3;
  --mono: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
}
@media (prefers-color-scheme: dark) {
  :root {
    --bg: #101216;
    --bg-alt: #171a20;
    --bg-raise: #1b1f26;
    --fg: #e6e8ee;
    --fg-dim: #98a0b0;
    --line: #2c313b;
    --line-soft: #23272f;
    --accent: #6ea8fe;
    --flag-bg: #2a1a1b;
    --flag-fg: #ff9b98;
    --flag-line: #5a2f2f;
    --ok-fg: #6fd39b;
    --chip: #232831;
  }
}
* { box-sizing: border-box; }
body {
  margin: 0; background: var(--bg); color: var(--fg);
  font: 15px/1.55 system-ui, -apple-system, "Segoe UI", Roboto, sans-serif;
}
.wrap { max-width: 1400px; margin: 0 auto; padding: 28px 20px 90px; }
h1 { font-size: 22px; margin: 0 0 4px; letter-spacing: -0.01em; }
h2 { font-size: 17px; margin: 0; letter-spacing: -0.01em; }
h3 { font-size: 13px; margin: 22px 0 8px; color: var(--fg-dim);
     text-transform: uppercase; letter-spacing: 0.07em; font-weight: 600; }
p { margin: 6px 0; }
a { color: var(--accent); }
code, .mono { font-family: var(--mono); font-size: 0.92em; }
.sub { color: var(--fg-dim); font-size: 13px; }

.band { display: grid; gap: 10px; grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        margin: 18px 0 10px; }
.stat { background: var(--bg-alt); border: 1px solid var(--line-soft);
        border-radius: 8px; padding: 12px 14px; }
.stat .n { font-size: 26px; font-weight: 650; letter-spacing: -0.02em; }
.stat .l { font-size: 12px; color: var(--fg-dim); text-transform: uppercase;
           letter-spacing: 0.06em; }
.stat.flag { background: var(--flag-bg); border-color: var(--flag-line); }
.stat.flag .n { color: var(--flag-fg); }

.metabar { background: var(--bg-alt); border: 1px solid var(--line-soft);
           border-radius: 8px; padding: 10px 14px; font-size: 12.5px;
           color: var(--fg-dim); display: flex; flex-wrap: wrap; gap: 6px 20px; }
.metabar b { color: var(--fg); font-weight: 600; }

.toolbar { position: sticky; top: 0; z-index: 20; background: var(--bg);
           border-bottom: 1px solid var(--line); padding: 10px 0 10px;
           margin: 18px 0 4px; display: flex; gap: 10px; flex-wrap: wrap;
           align-items: center; }
.toolbar input[type=search] {
  flex: 1 1 260px; min-width: 200px; padding: 8px 11px; border-radius: 7px;
  border: 1px solid var(--line); background: var(--bg-raise); color: var(--fg);
  font: inherit; font-size: 14px;
}
.toolbar button { padding: 7px 12px; border-radius: 7px; border: 1px solid var(--line);
  background: var(--bg-raise); color: var(--fg); font: inherit; font-size: 13px;
  cursor: pointer; }
.toolbar button:hover { border-color: var(--accent); }
.hint { color: var(--fg-dim); font-size: 12px; }

details.check { border: 1px solid var(--line); border-radius: 9px;
  margin: 12px 0; background: var(--bg-raise); overflow: hidden; }
details.check > summary {
  cursor: pointer; padding: 12px 16px; list-style: none; display: flex;
  gap: 12px; align-items: baseline; background: var(--bg-alt);
  border-bottom: 1px solid transparent;
}
details.check[open] > summary { border-bottom-color: var(--line); }
details.check > summary::-webkit-details-marker { display: none; }
summary .caret { color: var(--fg-dim); font-size: 11px; width: 10px; }
details[open] .caret { transform: rotate(90deg); }
.caret { display: inline-block; transition: transform .12s ease; }
.lead { color: var(--fg-dim); font-size: 13px; margin-left: auto; text-align: right;
        max-width: 55%; }
.pill { font-size: 11.5px; padding: 2px 8px; border-radius: 999px;
        background: var(--chip); color: var(--fg-dim); font-weight: 600;
        letter-spacing: 0.02em; }
.pill.flag { background: var(--flag-bg); color: var(--flag-fg); }
.pill.ok { color: var(--ok-fg); }
.body { padding: 4px 16px 18px; }

.tablewrap { overflow-x: auto; border: 1px solid var(--line-soft); border-radius: 7px;
             max-height: 560px; overflow-y: auto; }
table { border-collapse: collapse; width: 100%; font-size: 13px; }
th, td { text-align: left; padding: 6px 10px; border-bottom: 1px solid var(--line-soft);
         vertical-align: top; }
th { position: sticky; top: 0; background: var(--bg-alt); cursor: pointer;
     white-space: nowrap; font-size: 12px; letter-spacing: 0.02em;
     border-bottom: 1px solid var(--line); user-select: none; }
th:hover { color: var(--accent); }
th .arrow { color: var(--fg-dim); font-size: 10px; margin-left: 4px; }
td.num { text-align: right; font-variant-numeric: tabular-nums; font-family: var(--mono); }
tbody tr:hover { background: var(--bg-alt); }
td.path, td.mono { font-family: var(--mono); font-size: 12px; word-break: break-all; }
.empty { color: var(--fg-dim); font-style: italic; padding: 8px 2px; font-size: 13px; }
.note { background: var(--bg-alt); border-left: 3px solid var(--line);
        padding: 8px 12px; border-radius: 0 6px 6px 0; color: var(--fg-dim);
        font-size: 13px; margin: 10px 0; }
ul.plain { margin: 6px 0; padding-left: 20px; font-family: var(--mono); font-size: 12.5px; }
.kv { display: flex; gap: 10px; align-items: baseline; margin: 4px 0; font-size: 13.5px; }
.kv .k { color: var(--fg-dim); }
.kv .v { font-weight: 600; font-family: var(--mono); }
.bar { height: 8px; border-radius: 4px; background: var(--accent); opacity: .85; }
.profgrid { display: grid; gap: 8px; grid-template-columns: 120px 1fr 130px;
            align-items: center; font-size: 13px; }
.badge { display: inline-block; font-family: var(--mono); font-size: 11.5px;
         padding: 1px 6px; border-radius: 5px; background: var(--chip); margin: 1px 3px 1px 0; }
.true { color: var(--ok-fg); font-weight: 600; }
.false { color: var(--flag-fg); font-weight: 600; }

svg.graph { width: 100%; height: 620px; display: block; background: var(--bg-alt);
            border: 1px solid var(--line-soft); border-radius: 7px; }
.legend { display: flex; flex-wrap: wrap; gap: 6px 14px; margin: 8px 0; font-size: 12px;
          color: var(--fg-dim); }
.legend span.sw { display: inline-block; width: 10px; height: 10px; border-radius: 3px;
                  margin-right: 5px; vertical-align: -1px; }
#tip { position: fixed; pointer-events: none; opacity: 0; background: var(--bg-raise);
       border: 1px solid var(--line); border-radius: 7px; padding: 7px 10px;
       font-size: 12px; box-shadow: 0 6px 20px rgba(0,0,0,.22); z-index: 60;
       font-family: var(--mono); }
.mtable td:first-child { white-space: nowrap; font-family: var(--mono); font-size: 12px; }
.matrix td.c { text-align: center; font-variant-numeric: tabular-nums;
               font-family: var(--mono); }
.matrix th.rot { writing-mode: vertical-rl; text-orientation: mixed; height: 130px;
                 vertical-align: bottom; font-weight: 500; }
"""


JS = r"""
'use strict';
var DATA = JSON.parse(document.getElementById('audit-data').textContent);
var VIEW = JSON.parse(document.getElementById('view-spec').textContent);

var PALETTE = ['#4c78a8','#f58518','#54a24b','#e45756','#72b7b2','#eeca3b',
               '#b279a2','#ff9da6','#9d755d','#bab0ac','#7f7fbf','#3d9970'];
var clusterColor = {};
function colorFor(c) {
  if (!(c in clusterColor)) {
    var keys = Object.keys(clusterColor).length;
    clusterColor[c] = PALETTE[keys % PALETTE.length];
  }
  return clusterColor[c];
}

function el(tag, cls, text) {
  var n = document.createElement(tag);
  if (cls) n.className = cls;
  if (text !== undefined && text !== null) n.textContent = String(text);
  return n;
}
function fmt(v) {
  if (v === null || v === undefined) return '';
  if (Array.isArray(v)) return v.join(', ');
  if (typeof v === 'object') return JSON.stringify(v);
  return String(v);
}

/* ---------- generic blocks ---------- */

function renderTable(rows, columns) {
  var wrap = el('div', 'tablewrap');
  var t = el('table');
  var thead = el('thead');
  var hr = el('tr');
  columns.forEach(function (c, i) {
    var th = el('th', null, c.label);
    var arrow = el('span', 'arrow', '');
    th.appendChild(arrow);
    th.addEventListener('click', function () { sortBy(t, i, c.kind); });
    hr.appendChild(th);
  });
  thead.appendChild(hr); t.appendChild(thead);
  var tb = el('tbody');
  rows.forEach(function (r) {
    var tr = el('tr');
    columns.forEach(function (c) {
      var v = r ? r[c.key] : null;
      var td = el('td');
      if (c.kind === 'num') { td.className = 'num'; td.textContent = fmt(v); }
      else if (c.kind === 'bool') {
        td.appendChild(el('span', v ? 'true' : 'false', v ? 'yes' : 'no'));
      } else {
        var s = fmt(v);
        if (/^[a-z0-9._\/-]+\.(md|py|sh|json|html|jsonl)$/i.test(s) || /\//.test(s)) {
          td.className = 'path';
        }
        td.textContent = s;
      }
      tr.appendChild(td);
    });
    tr.dataset.hay = columns.map(function (c) { return fmt(r ? r[c.key] : ''); })
                            .join(' ').toLowerCase();
    tb.appendChild(tr);
  });
  t.appendChild(tb);
  wrap.appendChild(t);
  return wrap;
}

function sortBy(table, idx, kind) {
  var tb = table.tBodies[0];
  var rows = Array.prototype.slice.call(tb.rows);
  var th = table.tHead.rows[0].cells[idx];
  var dir = th.dataset.dir === 'asc' ? 'desc' : 'asc';
  Array.prototype.forEach.call(table.tHead.rows[0].cells, function (c) {
    c.dataset.dir = ''; c.querySelector('.arrow').textContent = '';
  });
  th.dataset.dir = dir;
  th.querySelector('.arrow').textContent = dir === 'asc' ? '▲' : '▼';
  rows.sort(function (a, b) {
    var x = a.cells[idx].textContent, y = b.cells[idx].textContent;
    var r;
    if (kind === 'num') {
      var nx = parseFloat(x), ny = parseFloat(y);
      if (isNaN(nx) && isNaN(ny)) r = 0;
      else if (isNaN(nx)) r = 1;
      else if (isNaN(ny)) r = -1;
      else r = nx - ny;
    } else { r = x.localeCompare(y); }
    return dir === 'asc' ? r : -r;
  });
  rows.forEach(function (r) { tb.appendChild(r); });
}

function blockTitle(label) {
  return label ? el('h3', null, label) : null;
}

function renderBlock(check, spec) {
  var frag = document.createDocumentFragment();
  var has = check && Object.prototype.hasOwnProperty.call(check, spec.path);
  var val = has ? check[spec.path] : undefined;
  var t = blockTitle(spec.label);

  if (!has) {
    if (spec.type === 'note') return frag;
    if (t) frag.appendChild(t);
    frag.appendChild(el('div', 'empty',
      'Key "' + spec.path + '" is not present in this report.'));
    return frag;
  }
  if (val === null || val === undefined ||
      (Array.isArray(val) && val.length === 0) ||
      (typeof val === 'object' && !Array.isArray(val) && Object.keys(val).length === 0)) {
    if (spec.type === 'note') return frag;
    if (t) frag.appendChild(t);
    frag.appendChild(el('div', 'empty', 'None.'));
    return frag;
  }

  switch (spec.type) {
    case 'note':
      frag.appendChild(el('div', 'note', fmt(val)));
      return frag;
    case 'kv': {
      var d = el('div', 'kv');
      d.appendChild(el('span', 'k', spec.label + ':'));
      d.appendChild(el('span', 'v', fmt(val)));
      frag.appendChild(d);
      return frag;
    }
    case 'list': {
      if (t) frag.appendChild(t);
      var ul = el('ul', 'plain');
      (Array.isArray(val) ? val : [val]).forEach(function (x) {
        ul.appendChild(el('li', null, fmt(x)));
      });
      frag.appendChild(ul);
      return frag;
    }
    case 'kvmap': {
      if (t) frag.appendChild(t);
      var rows = Object.keys(val).map(function (k) {
        return { k: k, v: fmt(val[k]) };
      });
      frag.appendChild(renderTable(rows, [
        { key: 'k', label: spec.key_label || 'Key', kind: 'text' },
        { key: 'v', label: spec.value_label || 'Value', kind: 'text' }]));
      return frag;
    }
    case 'table': {
      if (t) frag.appendChild(t);
      frag.appendChild(renderTable(val, spec.columns));
      return frag;
    }
    case 'profiles': {
      if (t) frag.appendChild(t);
      var max = 0;
      Object.keys(val).forEach(function (k) { max = Math.max(max, val[k].approx_tokens); });
      var g = el('div', 'profgrid');
      Object.keys(val).forEach(function (k) {
        g.appendChild(el('div', null, k + ' (' + val[k].commands + ')'));
        var barwrap = el('div');
        var bar = el('div', 'bar');
        bar.style.width = (max ? (100 * val[k].approx_tokens / max) : 0) + '%';
        bar.style.background = colorFor(k);
        barwrap.appendChild(bar);
        g.appendChild(barwrap);
        g.appendChild(el('div', 'mono', val[k].approx_tokens.toLocaleString() + ' tok'));
      });
      frag.appendChild(g);
      return frag;
    }
    case 'harness': {
      if (t) frag.appendChild(t);
      var hrows = [];
      val.forEach(function (r) {
        var names = r.harnesses_named || {};
        var keys = Object.keys(names).sort();
        hrows.push({ surface: r.surface,
                     named: keys.map(function (k) { return k + ' (' + names[k] + ')'; })
                               .join(', ') || 'none' });
      });
      frag.appendChild(renderTable(hrows, [
        { key: 'surface', label: 'Surface', kind: 'text' },
        { key: 'named', label: 'Harness names and mention counts', kind: 'text' }]));
      return frag;
    }
    case 'external': {
      if (t) frag.appendChild(t);
      var erows = val.map(function (r) {
        return {
          command: r.command, cluster: r.cluster,
          tools: (r.declared_network_tools || []).join(', '),
          mechs: (r.mechanisms || []).map(function (m) {
            return m.mechanism + ' x' + m.hits + ' (line ' + m.first_hit.line + ')';
          }).join(' | ')
        };
      });
      frag.appendChild(renderTable(erows, [
        { key: 'command', label: 'Command', kind: 'text' },
        { key: 'cluster', label: 'Cluster', kind: 'text' },
        { key: 'tools', label: 'Declared network tools', kind: 'text' },
        { key: 'mechs', label: 'Mechanism named in the file', kind: 'text' }]));
      return frag;
    }
    case 'matrix': {
      if (t) frag.appendChild(t);
      frag.appendChild(renderMatrix(val));
      return frag;
    }
    case 'graph': {
      if (t) frag.appendChild(t);
      frag.appendChild(renderGraph(check));
      return frag;
    }
  }
  return frag;
}

function renderMatrix(rows) {
  var froms = [], tos = [], map = {};
  rows.forEach(function (r) {
    if (froms.indexOf(r.from) < 0) froms.push(r.from);
    if (tos.indexOf(r.to) < 0) tos.push(r.to);
    map[r.from + "::" + r.to] = r.edges;
  });
  var all = froms.slice();
  tos.forEach(function (t) { if (all.indexOf(t) < 0) all.push(t); });
  all.sort();
  var max = 0;
  rows.forEach(function (r) { max = Math.max(max, r.edges); });

  var wrap = el('div', 'tablewrap');
  var t = el('table', 'matrix');
  var thead = el('thead'), hr = el('tr');
  hr.appendChild(el('th', null, 'from \\ to'));
  all.forEach(function (c) { hr.appendChild(el('th', 'rot', c)); });
  thead.appendChild(hr); t.appendChild(thead);
  var tb = el('tbody');
  all.forEach(function (a) {
    var tr = el('tr');
    tr.appendChild(el('td', 'mono', a));
    all.forEach(function (b) {
      var v = map[a + "::" + b] || 0;
      var td = el('td', 'c', v || '');
      if (v) {
        var alpha = 0.12 + 0.68 * (v / (max || 1));
        td.style.background = 'rgba(79,134,214,' + alpha.toFixed(3) + ')';
      }
      tr.appendChild(td);
    });
    tr.dataset.hay = a.toLowerCase();
    tb.appendChild(tr);
  });
  t.appendChild(tb); wrap.appendChild(t);
  return wrap;
}

/* ---------- reference graph ---------- */

function renderGraph(check) {
  var host = el('div');
  var nodes = (check.nodes || []).map(function (n) { return Object.assign({}, n); });
  var edges = check.edges || [];
  if (!nodes.length) {
    host.appendChild(el('div', 'empty', 'No nodes in this report.'));
    return host;
  }
  var reach = {};
  var rc = DATA.check_12_reachability;
  var haveReach = rc && rc.status === 'ok' && rc.per_command_depth;
  if (haveReach) {
    rc.per_command_depth.forEach(function (r) { reach[r.command] = r.reachable; });
  }

  var clusters = [];
  nodes.forEach(function (n) { if (clusters.indexOf(n.cluster) < 0) clusters.push(n.cluster); });
  clusters.sort();
  clusters.forEach(function (c) { colorFor(c); });

  var legend = el('div', 'legend');
  clusters.forEach(function (c) {
    var s = el('span');
    var sw = el('span', 'sw'); sw.style.background = colorFor(c);
    s.appendChild(sw); s.appendChild(document.createTextNode(c));
    legend.appendChild(s);
  });
  var note = el('span');
  note.textContent = haveReach
    ? 'dashed outline = unreachable from a documented entry point; radius scales with approximate token count'
    : 'reachability data absent from this report; radius scales with approximate token count';
  legend.appendChild(note);
  host.appendChild(legend);

  var W = 1200, H = 620;
  var svg = document.createElementNS('http://www.w3.org/2000/svg', 'svg');
  svg.setAttribute('viewBox', '0 0 ' + W + ' ' + H);
  svg.setAttribute('class', 'graph');
  svg.setAttribute('preserveAspectRatio', 'xMidYMid meet');
  host.appendChild(svg);

  var index = {};
  var seed = 1;
  function rnd() { seed = (seed * 1103515245 + 12345) % 2147483648; return seed / 2147483648; }
  nodes.forEach(function (n, i) {
    index[n.id] = i;
    var ci = clusters.indexOf(n.cluster);
    var ang = (ci / clusters.length) * Math.PI * 2;
    n.x = W / 2 + Math.cos(ang) * 240 + (rnd() - 0.5) * 130;
    n.y = H / 2 + Math.sin(ang) * 210 + (rnd() - 0.5) * 130;
    n.vx = 0; n.vy = 0;
    var t = n.approx_tokens || 0;
    n.r = 3.4 + Math.sqrt(t) / 22;
  });

  var links = [];
  var seen = {};
  edges.forEach(function (e) {
    var k = e.source + "::" + e.target;
    if (seen[k]) return;
    seen[k] = 1;
    if (index[e.source] === undefined || index[e.target] === undefined) return;
    links.push([index[e.source], index[e.target]]);
  });

  for (var it = 0; it < 320; it++) {
    var alpha = 1 - it / 320;
    for (var i = 0; i < nodes.length; i++) {
      for (var j = i + 1; j < nodes.length; j++) {
        var a = nodes[i], b = nodes[j];
        var dx = b.x - a.x, dy = b.y - a.y;
        var d2 = dx * dx + dy * dy || 0.01;
        var d = Math.sqrt(d2);
        var rep = 2400 / d2;
        var ux = dx / d, uy = dy / d;
        a.vx -= ux * rep; a.vy -= uy * rep;
        b.vx += ux * rep; b.vy += uy * rep;
      }
    }
    links.forEach(function (l) {
      var a = nodes[l[0]], b = nodes[l[1]];
      var dx = b.x - a.x, dy = b.y - a.y;
      var d = Math.sqrt(dx * dx + dy * dy) || 0.01;
      var f = (d - 95) * 0.012;
      var ux = dx / d, uy = dy / d;
      a.vx += ux * f; a.vy += uy * f;
      b.vx -= ux * f; b.vy -= uy * f;
    });
    nodes.forEach(function (n) {
      n.vx += (W / 2 - n.x) * 0.0016;
      n.vy += (H / 2 - n.y) * 0.0016;
      n.x += n.vx * alpha; n.y += n.vy * alpha;
      n.vx *= 0.82; n.vy *= 0.82;
      n.x = Math.max(18, Math.min(W - 18, n.x));
      n.y = Math.max(18, Math.min(H - 18, n.y));
    });
  }

  var ns = 'http://www.w3.org/2000/svg';
  var gl = document.createElementNS(ns, 'g');
  gl.setAttribute('stroke', 'currentColor');
  gl.setAttribute('stroke-opacity', '0.13');
  gl.setAttribute('stroke-width', '0.7');
  gl.setAttribute('fill', 'none');
  var dstr = links.map(function (l) {
    var a = nodes[l[0]], b = nodes[l[1]];
    return 'M' + a.x.toFixed(1) + ',' + a.y.toFixed(1) +
           'L' + b.x.toFixed(1) + ',' + b.y.toFixed(1);
  }).join('');
  var p = document.createElementNS(ns, 'path');
  p.setAttribute('d', dstr);
  gl.appendChild(p);
  svg.appendChild(gl);

  var gn = document.createElementNS(ns, 'g');
  var tip = document.getElementById('tip');
  nodes.forEach(function (n) {
    var c = document.createElementNS(ns, 'circle');
    c.setAttribute('cx', n.x.toFixed(1));
    c.setAttribute('cy', n.y.toFixed(1));
    c.setAttribute('r', n.r.toFixed(2));
    c.setAttribute('fill', colorFor(n.cluster));
    var unreachable = haveReach && reach[n.id] === false;
    c.setAttribute('stroke', unreachable ? '#e45756' : 'rgba(0,0,0,0.28)');
    c.setAttribute('stroke-width', unreachable ? '2' : '0.6');
    if (unreachable) c.setAttribute('stroke-dasharray', '2 2');
    c.addEventListener('mousemove', function (ev) {
      tip.style.opacity = 1;
      tip.style.left = (ev.clientX + 14) + 'px';
      tip.style.top = (ev.clientY + 14) + 'px';
      tip.innerHTML = '';
      [n.id, n.cluster,
       'tokens ~' + (n.approx_tokens || 0),
       'fan-in ' + n.fan_in_distinct + ' / fan-out ' + n.fan_out_distinct,
       haveReach ? (unreachable ? 'unreachable' : 'reachable') : 'reachability n/a'
      ].forEach(function (line) { tip.appendChild(el('div', null, line)); });
    });
    c.addEventListener('mouseleave', function () { tip.style.opacity = 0; });
    gn.appendChild(c);
  });
  svg.appendChild(gn);

  var gt = document.createElementNS(ns, 'g');
  nodes.slice().sort(function (a, b) { return b.fan_in_distinct - a.fan_in_distinct; })
       .slice(0, 22).forEach(function (n) {
    var t = document.createElementNS(ns, 'text');
    t.setAttribute('x', (n.x + n.r + 3).toFixed(1));
    t.setAttribute('y', (n.y + 3).toFixed(1));
    t.setAttribute('font-size', '9');
    t.setAttribute('fill', 'currentColor');
    t.setAttribute('fill-opacity', '0.72');
    t.textContent = n.id;
    gt.appendChild(t);
  });
  svg.appendChild(gt);
  return host;
}

/* ---------- page ---------- */

function mismatchCounts() {
  var byNum = {};
  (DATA.mismatches || []).forEach(function (m) {
    var num = (m.check.match(/^(\d+)/) || [])[1];
    if (!num) return;
    byNum[num] = (byNum[num] || 0) + 1;
  });
  return byNum;
}

function renderGates(root) {
  var g = DATA.reused_gates;
  var d = el('details', 'check');
  d.id = 'reused_gates';
  var s = el('summary');
  s.appendChild(el('span', 'caret', '▶'));
  s.appendChild(el('h2', null, '0. Reused repository guards'));
  var body = el('div', 'body');
  if (!g) {
    s.appendChild(el('span', 'pill flag', 'absent'));
    body.appendChild(el('div', 'note',
      'Key "reused_gates" is not present in this report.'));
    d.open = true;
  } else if (g.status !== 'ok') {
    s.appendChild(el('span', 'pill flag', g.status));
    body.appendChild(el('div', 'note',
      'Not run. Reason: ' + (g.reason || 'not stated.')));
    d.open = true;
  } else {
    var bad = (g.gates || []).filter(function (x) {
      return x.status !== 'ok' || x.exit_code !== 0; }).length;
    s.appendChild(el('span', bad ? 'pill flag' : 'pill ok',
      bad ? bad + ' non-zero' : 'all clean'));
    if (bad) d.open = true;
    body.appendChild(el('div', 'note',
      'These guards ship with the repository and are run rather than ' +
      'reimplemented. Checks 1, 2, 3, and 7 below overlap them on purpose, so a ' +
      'disagreement between the two is visible.'));
    var rows = (g.gates || []).map(function (x) {
      return {
        gate: x.gate,
        command: x.command || '',
        exit_code: x.status === 'ok' ? x.exit_code : null,
        status: x.status === 'ok' ? (x.exit_code === 0 ? 'clean' : 'non-zero exit')
                                  : (x.reason || x.status),
        covers: x.covers || '',
        output: (x.summary_lines || []).join(' | ')
      };
    });
    body.appendChild(renderTable(rows, [
      { key: 'gate', label: 'Guard', kind: 'text' },
      { key: 'command', label: 'Command', kind: 'text' },
      { key: 'exit_code', label: 'Exit', kind: 'num' },
      { key: 'status', label: 'Status', kind: 'text' },
      { key: 'covers', label: 'Covers', kind: 'text' },
      { key: 'output', label: 'Output', kind: 'text' }]));
  }
  s.appendChild(el('span', 'lead',
    'The repository guards, run as part of this pass.'));
  d.appendChild(s); d.appendChild(body);
  root.appendChild(d);
}

function build() {
  var counts = mismatchCounts();
  var root = document.getElementById('sections');
  renderGates(root);

  VIEW.forEach(function (v) {
    var check = DATA[v.id];
    var num = (v.id.match(/check_(\d+)/) || [])[1];
    var mm = counts[num] || 0;

    var d = el('details', 'check');
    d.id = v.id;
    var s = el('summary');
    s.appendChild(el('span', 'caret', '▶'));
    s.appendChild(el('h2', null, v.title));
    if (!check) {
      s.appendChild(el('span', 'pill flag', 'absent'));
    } else if (check.status === 'could_not_run') {
      s.appendChild(el('span', 'pill flag', 'could not run'));
    } else if (mm) {
      s.appendChild(el('span', 'pill flag', mm + (mm === 1 ? ' mismatch' : ' mismatches')));
    } else {
      s.appendChild(el('span', 'pill ok', 'no mismatch'));
    }
    if (v.lead) s.appendChild(el('span', 'lead', v.lead));
    d.appendChild(s);

    var body = el('div', 'body');
    if (!check) {
      body.appendChild(el('div', 'note',
        'This check is absent from the report. Reason: the key "' + v.id +
        '" was not written by the audit run that produced this JSON.'));
    } else if (check.status === 'could_not_run') {
      body.appendChild(el('div', 'note',
        'This check could not run. Reason: ' + (check.reason || 'not stated.')));
    } else {
      v.blocks.forEach(function (b) { body.appendChild(renderBlock(check, b)); });
    }
    d.appendChild(body);
    if (mm > 0 || !check || (check && check.status === 'could_not_run')) d.open = true;
    root.appendChild(d);
  });

  /* mismatch table */
  var host = document.getElementById('mismatches');
  var rows = DATA.mismatches || [];
  if (!rows.length) {
    host.appendChild(el('div', 'empty', 'No mismatches recorded.'));
  } else {
    host.appendChild(renderTable(rows, [
      { key: 'check', label: 'Check', kind: 'text' },
      { key: 'expected', label: 'Expected', kind: 'text' },
      { key: 'actual', label: 'Actual', kind: 'text' },
      { key: 'location', label: 'Location', kind: 'text' }]));
  }

  var box = document.getElementById('filter');
  box.addEventListener('input', function () {
    var q = box.value.trim().toLowerCase();
    var hidden = 0, shown = 0;
    document.querySelectorAll('tbody tr').forEach(function (tr) {
      var hay = tr.dataset.hay || tr.textContent.toLowerCase();
      var ok = !q || hay.indexOf(q) >= 0;
      tr.style.display = ok ? '' : 'none';
      if (ok) shown++; else hidden++;
    });
    document.getElementById('filterstat').textContent =
      q ? (shown + ' rows match, ' + hidden + ' hidden') : '';
    if (q) document.querySelectorAll('details.check').forEach(function (d) { d.open = true; });
  });
  document.getElementById('expand').addEventListener('click', function () {
    document.querySelectorAll('details.check').forEach(function (d) { d.open = true; });
  });
  document.getElementById('collapse').addEventListener('click', function () {
    document.querySelectorAll('details.check').forEach(function (d) { d.open = false; });
  });
}

build();
"""


def esc(s):
    return html.escape(str(s), quote=False)


def build_html(data):
    summary = data.get("summary", {})
    meta = data.get("meta", {})
    cnr = summary.get("checks_could_not_run", [])

    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    view = json.dumps(VIEW, ensure_ascii=False).replace("</", "<\\/")

    stats = [
        ("commands", summary.get("commands_total", "n/a"), False),
        ("mismatches", summary.get("mismatches_total", "n/a"),
         bool(summary.get("mismatches_total"))),
        ("checks run", "%s of %s" % (summary.get("checks_run", "n/a"),
                                     summary.get("checks_total", "n/a")), False),
        ("could not run", len(cnr), bool(cnr)),
    ]
    band = "".join(
        '<div class="stat%s"><div class="n">%s</div><div class="l">%s</div></div>'
        % (" flag" if flag else "", esc(value), esc(label))
        for label, value, flag in stats)

    metabits = [
        ("git sha", (meta.get("git_sha") or "unavailable")[:12]),
        ("branch", meta.get("git_branch") or "unavailable"),
        ("commit time", meta.get("git_commit_time") or "unavailable"),
        ("run", meta.get("run_timestamp") or "unavailable"),
        ("audit", meta.get("audit_version", "?")),
        ("renderer", RENDER_VERSION),
        ("uncommitted paths", meta.get("working_tree_dirty_paths", "?")),
    ]
    metabar = "".join("<span><b>%s</b> %s</span>" % (esc(k), esc(v)) for k, v in metabits)

    cnr_line = ""
    if cnr:
        cnr_line = ('<p class="sub">Checks that could not run: %s</p>'
                    % esc(", ".join(cnr)))

    launch = meta.get("launch_commit") or {}
    launch_line = ""
    if launch.get("sha"):
        launch_line = ('<p class="sub">Launch commit used for the since-launch '
                       'columns: <code>%s</code> (%s), resolved by %s.</p>'
                       % (esc(launch["sha"][:12]), esc(launch.get("date", "")),
                          esc(launch.get("resolved_by", "unstated"))))
    elif launch:
        launch_line = ('<p class="sub">Launch commit unresolved: %s</p>'
                       % esc(launch.get("reason", "no reason recorded")))

    scripts_rows = "".join(
        "<tr><td class=\"path\">%s</td><td class=\"mono\">%s</td><td>%s</td></tr>"
        % (esc(s.get("script", "")), esc(s.get("sha256_16", "")),
           esc(s.get("role", "")))
        for s in meta.get("scripts", []))

    return (
        "<!doctype html>\n"
        "<html lang=\"en\">\n<head>\n"
        "<meta charset=\"utf-8\">\n"
        "<meta name=\"viewport\" content=\"width=device-width, initial-scale=1\">\n"
        "<title>Fhorja baseline audit</title>\n"
        "<style>%s</style>\n</head>\n<body>\n"
        "<div class=\"wrap\">\n"
        "<h1>Fhorja repository baseline</h1>\n"
        "<p class=\"sub\">Read-only structural, graph, history, and convention "
        "baseline. Facts only: no recommendations, no severity ratings. Generated "
        "from the JSON artifact of record by "
        "<code>scripts/audit/render_baseline_html.py</code>.</p>\n"
        "<div class=\"band\">%s</div>\n"
        "<div class=\"metabar\">%s</div>\n"
        "%s%s\n"
        "<div class=\"toolbar\">\n"
        "  <input id=\"filter\" type=\"search\" placeholder=\"Filter every table on "
        "this page\" autocomplete=\"off\">\n"
        "  <button id=\"expand\" type=\"button\">Expand all</button>\n"
        "  <button id=\"collapse\" type=\"button\">Collapse all</button>\n"
        "  <span id=\"filterstat\" class=\"hint\"></span>\n"
        "  <span class=\"hint\">Click a column header to sort.</span>\n"
        "</div>\n"
        "<div id=\"sections\"></div>\n"
        "<h3>Mismatches</h3>\n"
        "<div id=\"mismatches\"></div>\n"
        "<h3>Provenance</h3>\n"
        "<div class=\"tablewrap\"><table><thead><tr><th>Script</th>"
        "<th>sha256 (first 16)</th><th>Role</th></tr></thead><tbody>%s</tbody>"
        "</table></div>\n"
        "<p class=\"sub\">%s</p>\n"
        "</div>\n"
        "<div id=\"tip\"></div>\n"
        "<script id=\"audit-data\" type=\"application/json\">%s</script>\n"
        "<script id=\"view-spec\" type=\"application/json\">%s</script>\n"
        "<script>%s</script>\n"
        "</body>\n</html>\n"
    ) % (CSS, band, metabar, cnr_line, launch_line, scripts_rows,
         esc(meta.get("determinism", "")), payload, view, JS)


def main(argv):
    ap = argparse.ArgumentParser(description="Render the baseline audit JSON as HTML")
    ap.add_argument("--json", required=True, help="path to the audit JSON")
    ap.add_argument("--out", required=True, help="path to write the HTML")
    args = ap.parse_args(argv)

    with open(args.json, "r", encoding="utf-8") as fh:
        data = json.load(fh)

    page = build_html(data)
    for ch, label in (("—", "em-dash"), ("–", "en-dash")):
        if ch in page:
            sys.stderr.write("render_baseline_html: refusing to write: a %s "
                             "reached the page\n" % label)
            return 3

    os.makedirs(os.path.dirname(os.path.abspath(args.out)), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        fh.write(page)
    sys.stderr.write("render_baseline_html: wrote %s (%d bytes)\n"
                     % (args.out, len(page.encode("utf-8"))))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
