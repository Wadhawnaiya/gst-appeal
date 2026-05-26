#!/usr/bin/env bash
set -u -o pipefail

ROOT="/home/wadhawaniya/gst-appeal"
SKILL_DIR="$ROOT/.agents/skills/gst-appeal-drafting"
CASE_REPO="$ROOT/caselaws-cli"
OUT_DIR="$ROOT/demo/output"
FACTS_FILE="$ROOT/demo/first-run-facts.md"
ISSUE="natural justice non-speaking order section 74"
JURISDICTION="Gujarat"

mkdir -p "$OUT_DIR"

CASE_PY="$CASE_REPO/.venv/bin/python"
NOTEBOOKLM_BIN="$CASE_REPO/.venv/bin/notebooklm"

if [[ ! -x "$CASE_PY" ]]; then
  echo "ERROR: caselaws-cli venv python not found at $CASE_PY"
  echo "Run: python3 $SKILL_DIR/scripts/install_dependencies.py --only caselaws"
  exit 1
fi

export CASELAWS_REPO="$CASE_REPO"
export CASELAWS_CLI="$CASE_PY -m cli_anything.caselaws.main"
if [[ -x "$NOTEBOOKLM_BIN" ]]; then
  export NOTEBOOKLM_CLI="$NOTEBOOKLM_BIN"
fi

caselaws() {
  "$CASE_PY" -m cli_anything.caselaws.main "$@"
}

section() {
  printf '\n\n========== %s ==========' "$1"
  printf '\n'
}

section "1. Tool paths"
echo "Project root:       $ROOT"
echo "Skill dir:          $SKILL_DIR"
echo "caselaws python:    $CASE_PY"
echo "notebooklm binary:  ${NOTEBOOKLM_BIN:-not found}"
echo "Notebook ID env:    ${NOTEBOOKLM_NOTEBOOK:-<not set>}"

section "2. Environment check"
python3 "$SKILL_DIR/scripts/check_environment.py" --json > "$OUT_DIR/environment-check.json"
python3 -m json.tool "$OUT_DIR/environment-check.json" | sed -n '1,120p'

section "3. Broad case-law search"
if caselaws search "GST $ISSUE $JURISDICTION High Court" --json --limit 3 > "$OUT_DIR/caselaws-search.json"; then
  python3 -m json.tool "$OUT_DIR/caselaws-search.json" | sed -n '1,120p'
else
  echo "Case-law search failed. Raw output saved at $OUT_DIR/caselaws-search.json"
fi

section "4. Research packet generation"
NOTEBOOK_ARGS=()
if [[ -n "${NOTEBOOKLM_NOTEBOOK:-}" ]]; then
  NOTEBOOK_ARGS=(--notebook "$NOTEBOOKLM_NOTEBOOK")
fi

if python3 "$SKILL_DIR/scripts/gst_appeal_research.py" \
  --issue "$ISSUE" \
  --facts-file "$FACTS_FILE" \
  --jurisdiction "$JURISDICTION" \
  "${NOTEBOOK_ARGS[@]}" \
  --case-limit 2 \
  --timeout 30 \
  --output "$OUT_DIR/research-packet.md"; then
  echo "Research packet written to: $OUT_DIR/research-packet.md"
else
  echo "Research packet command returned non-zero; inspect: $OUT_DIR/research-packet.md"
fi

section "5. Research packet preview"
sed -n '1,180p' "$OUT_DIR/research-packet.md"

section "6. NotebookLM next step"
if [[ -z "${NOTEBOOKLM_NOTEBOOK:-}" ]]; then
  cat <<EOF
NOTEBOOKLM_NOTEBOOK is not set. To enable your GST law knowledge-bank:

  $NOTEBOOKLM_BIN login
  export NOTEBOOKLM_NOTEBOOK="<your-gst-law-notebook-id>"
  bash demo/first-run.sh
EOF
else
  echo "NotebookLM notebook configured as: $NOTEBOOKLM_NOTEBOOK"
  echo "If auth failed above, run: $NOTEBOOKLM_BIN login"
fi

section "Done"
echo "Generated files:"
echo "- $OUT_DIR/environment-check.json"
echo "- $OUT_DIR/caselaws-search.json"
echo "- $OUT_DIR/research-packet.md"
