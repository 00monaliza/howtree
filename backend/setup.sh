set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
WEIGHTS_DIR="$SCRIPT_DIR/weights"

echo "==> Creating backend/weights/ directory..."
mkdir -p "$WEIGHTS_DIR"
echo "    $WEIGHTS_DIR"

echo ""
echo "==> Checking for model weights..."
if [[ -f "$WEIGHTS_DIR/model_best.pth" ]]; then
    echo "    model_best.pth found ($(du -sh "$WEIGHTS_DIR/model_best.pth" | cut -f1))"
else
    echo "    MISSING: model_best.pth"
    echo ""
    echo "    Upload the weights file to the server:"
    echo "      scp /local/path/model_best.pth user@server:$WEIGHTS_DIR/model_best.pth"
    echo ""
    echo "    The inference endpoint (POST /predict) will return HTTP 503 until weights are present."
fi

echo ""
echo "==> Installing Detectron2 (Mask R-CNN backend)..."
echo "    Detectron2 is not on PyPI — installing from source:"
pip install 'git+https://github.com/facebookresearch/detectron2.git' \
    || echo "    WARNING: detectron2 install failed. Install manually per:"
    echo "    https://detectron2.readthedocs.io/tutorials/install.html"

echo ""
echo "==> Done. Start the direct inference server with:"
echo "    cd $SCRIPT_DIR && uvicorn api:app --port 8001 --host 0.0.0.0"
