#!/usr/bin/env bash
set -euo pipefail

# ============================================================
# Setup script for VLMEvalKit with U-MolRecBench-Wild patches
#
# This script:
#   1. Clones the official VLMEvalKit repository
#   2. Checks out the pinned commit for reproducibility
#   3. Applies our minimal patches (model adapters + dataset)
#   4. Installs VLMEvalKit in editable mode
# ============================================================

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "${SCRIPT_DIR}/.." && pwd)"

VLMEVALKIT_REPO="https://github.com/open-compass/VLMEvalKit.git"
VLMEVALKIT_COMMIT="b9ff66c970449a8106c02570102bcfb2fb3df462"
VLMEVALKIT_DIR="${REPO_ROOT}/VLMEvalKit"

PATCH_FILE="${REPO_ROOT}/patches/vlmevalkit_chem.patch"

echo "============================================"
echo "  U-MolRecBench-Wild: VLMEvalKit Setup"
echo "============================================"

# Step 1: Clone VLMEvalKit into a new, managed directory. Never reset or clean
# an existing checkout because it may contain user changes or untracked files.
if [ -e "${VLMEVALKIT_DIR}" ]; then
    echo "ERROR: Refusing to overwrite existing path: ${VLMEVALKIT_DIR}" >&2
    echo "Move or remove it explicitly, then run this script again." >&2
    exit 1
fi

echo "[1/4] Cloning official VLMEvalKit..."
git clone "${VLMEVALKIT_REPO}" "${VLMEVALKIT_DIR}"
cd "${VLMEVALKIT_DIR}"
git checkout --detach "${VLMEVALKIT_COMMIT}"

# Step 2: Verify commit
CURRENT_COMMIT=$(git rev-parse HEAD)
if [ "${CURRENT_COMMIT}" != "${VLMEVALKIT_COMMIT}" ]; then
    echo "ERROR: Failed to checkout pinned commit."
    echo "  Expected: ${VLMEVALKIT_COMMIT}"
    echo "  Got:      ${CURRENT_COMMIT}"
    exit 1
fi
echo "[2/4] Pinned to commit: ${VLMEVALKIT_COMMIT}"

# Step 3: Apply patch
if [ ! -f "${PATCH_FILE}" ]; then
    echo "ERROR: Patch file not found: ${PATCH_FILE}"
    exit 1
fi
echo "[3/4] Applying U-MolRecBench-Wild patches..."
git apply --check "${PATCH_FILE}"
git apply "${PATCH_FILE}"
echo "  Patch applied successfully."

# Step 4: Install
echo "[4/4] Installing VLMEvalKit..."
cd "${VLMEVALKIT_DIR}"
PYTHON_BIN="${PYTHON_BIN:-python3}"
if ! command -v "${PYTHON_BIN}" >/dev/null 2>&1; then
    echo "ERROR: Python interpreter not found: ${PYTHON_BIN}" >&2
    exit 1
fi
"${PYTHON_BIN}" -m pip install -e .
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
echo "    2. Prepare data:  python scripts/download_and_convert_dataset.py --prompt all"
echo "    3. Run inference: cd VLMEvalKit && python run.py --data ... --model ..."
echo "============================================"
