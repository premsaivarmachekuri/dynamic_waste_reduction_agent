"""
app.py — Production Flask application for the Dynamic Waste Reduction Engine.

Architecture:
  - Flask app factory pattern
  - Blueprint-based API routes (api/routes.py)
  - Legacy routes for frontend compatibility
  - Health endpoint for Cloud Run

Environment:
  - DEMO_MODE=false: reads from BigQuery, uses Vertex AI RAG
  - DEMO_MODE=true:  reads from mock JSON, uses local RAG document search
"""
import json
import os
import sys
import time
import uuid
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))
os.environ.setdefault("DEMO_MODE", "true")

from dotenv import load_dotenv
load_dotenv(override=True)

from flask import Flask, render_template, request, jsonify

from api.routes import api_bp
from services.inventory_service import get_store_list
from services.decision_service import (
    run_analysis,
    load_transfers,
    create_transfer,
    update_transfer_status,
    get_transfer_impact,
)
from tools.inventory_tools import get_inventory_status
from tools.weather_tools import get_weather_forecast

# ── App factory ───────────────────────────────────────────────────────────────

def create_app() -> Flask:
    app = Flask(__name__, template_folder="templates")
    app.config["JSON_SORT_KEYS"] = False

    # Register v1 API blueprint
    app.register_blueprint(api_bp)

    # ── Core page routes ──────────────────────────────────────────────────────

    @app.route("/")
    def index():
        stores = get_store_list()
        return render_template(
            "index.html",
            stores=stores,
            today_date=date.today().strftime("%A %d %B %Y"),
        )

    # ── Health check (Cloud Run) ──────────────────────────────────────────────

    @app.route("/health")
    def health():
        return jsonify({
            "status":  "healthy",
            "version": "2.0.0",
            "date":    date.today().isoformat(),
        })

    # ── Legacy API routes (frontend compatibility) ────────────────────────────

    @app.route("/api/store_data")
    def store_data():
        store_id = request.args.get("store_id", "ST001")
        inv      = get_inventory_status(store_id)
        weather  = get_weather_forecast(store_id)
        return jsonify({"inventory": inv, "weather": weather})

    @app.route("/api/run_analysis", methods=["POST"])
    def run_analysis_legacy():
        body     = request.json or {}
        store_id = body.get("store_id", "ST001")
        try:
            result = run_analysis(store_id)
            return jsonify(result)
        except Exception as e:
            app.logger.error(f"Analysis error: {e}")
            return jsonify({"error": str(e)}), 500

    @app.route("/api/decisions")
    def get_decisions():
        log_path = ROOT / "data" / "decisions_log.json"
        if log_path.exists():
            with open(log_path) as f:
                try:
                    return jsonify(json.load(f))
                except Exception:
                    return jsonify([])
        return jsonify([])

    @app.route("/api/transfers")
    def get_transfers():
        store_id = request.args.get("store_id", "ST001")
        all_t    = load_transfers()
        return jsonify({
            "outgoing": [t for t in all_t if t["from_store_id"] == store_id],
            "incoming": [t for t in all_t if t["to_store_id"]   == store_id],
        })

    @app.route("/api/initiate_transfer", methods=["POST"])
    def initiate_transfer():
        body = request.json or {}
        try:
            transfer = create_transfer(body)
            return jsonify({"status": "SUCCESS", "transfer": transfer})
        except ValueError as e:
            return jsonify({"error": str(e)}), 400

    @app.route("/api/accept_transfer", methods=["POST"])
    def accept_transfer():
        body        = request.json or {}
        transfer_id = body.get("transfer_id")
        new_status  = body.get("status", "ACCEPTED")
        if not transfer_id:
            return jsonify({"error": "transfer_id required"}), 400
        try:
            transfer = update_transfer_status(transfer_id, new_status)
            return jsonify({"status": "SUCCESS", "transfer": transfer})
        except ValueError as e:
            return jsonify({"error": str(e)}), 404

    @app.route("/api/transfer_impact")
    def transfer_impact():
        store_id = request.args.get("store_id")
        return jsonify(get_transfer_impact(store_id))

    return app


# ── Entry point ───────────────────────────────────────────────────────────────

app = create_app()

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    debug = os.environ.get("FLASK_DEBUG", "false").lower() == "true"
    app.run(host="0.0.0.0", port=port, debug=debug)
