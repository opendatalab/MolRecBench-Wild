#!/bin/bash
set -e

# ============================================================
# Setup script for VLMEvalKit with U-MolRecBench-Wild patches
#
# This script:
#   1. Clones the official VLMEvalKit repository
#   2. Checks out the pinned commit for reproducibility
#   3. Applies our minimal patches (model adapters + dataset)
#   4. Copies inference scripts and prompt templates
#   5. Installs VLMEvalKit in editable mode
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

VLMEVALKIT_REPO="https://github.com/open-compass/VLMEvalKit.git"
VLMEVALKIT_COMMIT="b9ff66c970449a8106c02570102bcfb2fb3df462"
VLMEVALKIT_DIR="${SCRIPT_DIR}/VLMEvalKit"

PATCH_FILE="${SCRIPT_DIR}/patches/vlmevalkit_chem.patch"

echo "============================================"
echo "  U-MolRecBench-Wild: VLMEvalKit Setup"
echo "============================================"

# Step 1: Clone or reset VLMEvalKit
if [ -d "${VLMEVALKIT_DIR}" ]; then
    echo "[1/5] VLMEvalKit directory exists, resetting to pinned commit..."
    cd "${VLMEVALKIT_DIR}"
    git fetch origin
    git checkout "${VLMEVALKIT_COMMIT}" --force
    git clean -fd
else
    echo "[1/5] Cloning official VLMEvalKit..."
    git clone "${VLMEVALKIT_REPO}" "${VLMEVALKIT_DIR}"
    cd "${VLMEVALKIT_DIR}"
    git checkout "${VLMEVALKIT_COMMIT}"
fi

# Step 2: Verify commit
CURRENT_COMMIT=$(git rev-parse HEAD)
if [ "${CURRENT_COMMIT}" != "${VLMEVALKIT_COMMIT}" ]; then
    echo "ERROR: Failed to checkout pinned commit."
    echo "  Expected: ${VLMEVALKIT_COMMIT}"
    echo "  Got:      ${CURRENT_COMMIT}"
    exit 1
fi
echo "[2/5] Pinned to commit: ${VLMEVALKIT_COMMIT}"

# Step 3: Apply patch
if [ ! -f "${PATCH_FILE}" ]; then
    echo "ERROR: Patch file not found: ${PATCH_FILE}"
    exit 1
fi
echo "[3/5] Applying U-MolRecBench-Wild patches..."
git apply "${PATCH_FILE}"
echo "  Patch applied successfully."

# Step 4: Copy inference scripts and prompts
echo "[4/5] Copying inference scripts and prompt templates..."
cp -r "${SCRIPT_DIR}/inference/scripts/chem" "${VLMEVALKIT_DIR}/scripts/chem"
cp -r "${SCRIPT_DIR}/inference/examples/"* "${VLMEVALKIT_DIR}/examples/"
echo "  Scripts and prompts copied."

# Step 5: Install
echo "[5/5] Installing VLMEvalKit..."
cd "${VLMEVALKIT_DIR}"
pip install -e . 2>&1 | tail -5
echo ""
echo "============================================"
echo "  Setup complete!"
echo ""
echo "  VLMEvalKit installed at: ${VLMEVALKIT_DIR}"
echo "  Based on official commit: ${VLMEVALKIT_COMMIT}"
echo "  With U-MolRecBench-Wild patches applied."
echo ""
echo "  Next steps:"
echo "    1. Configure API keys in VLMEvalKit/.env"
echo "    2. Prepare data:  cd VLMEvalKit && python scripts/chem/jsonl_to_tsv.py ..."
echo "    3. Run inference: cd VLMEvalKit && python run.py --data ... --model ..."
echo "============================================"
