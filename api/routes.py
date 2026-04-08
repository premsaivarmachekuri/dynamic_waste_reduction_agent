"""
routes.py — Structured Flask API route definitions for the Waste Reduction Engine.

All routes are registered on a Blueprint for clean separation from the app factory.
"""
import json
from datetime import date
from flask import Blueprint, request, jsonify, current_app

from services.inventory_service import get_store_dashboard, get_all_stores_summary, get_store_list
from services.decision_service import (
    run_analysis,
    load_transfers,
    create_transfer,
    update_transfer_status,
    get_transfer_impact,
)
from tools.bigquery_tools import get_decisions_summary, get_network_inventory_summary
from tools.pricing_tools import calculate_esg_metrics

api_bp = Blueprint("api", __name__, url_prefix="/api/v1")


# ── Health / Status ────────────────────────────────────────────────────────────

@api_bp.route("/health")
def health():
    """Health check endpoint for Cloud Run."""
    return jsonify({
        "status":  "healthy",
        "version": "2.0.0",
        "date":    date.today().isoformat(),
        "agents":  6,
        "rag":     "vertex-ai",
        "datastore": "bigquery",
    })


@api_bp.route("/status")
def system_status():
    """Detailed system status — checks all external integrations."""
    import os
    status = {
        "api_key_set":  bool(os.getenv("GOOGLE_API_KEY")),
        "gcp_project":  os.getenv("GOOGLE_CLOUD_PROJECT", "tcs-1770741130267"),
        "demo_mode":    os.getenv("DEMO_MODE", "true"),
        "bq_dataset":   os.getenv("BQ_DATASET", "waste_engine"),
        "rag_corpus":   bool(os.getenv("RAG_CORPUS_NAME", "")),
        "region":       os.getenv("GOOGLE_CLOUD_LOCATION", "us-central1"),
    }

    # Test RAG availability
    try:
        from rag.retriever import _check_rag_available
        status["rag_available"] = _check_rag_available()
    except Exception:
        status["rag_available"] = False

    return jsonify(status)


# ── Store Data ─────────────────────────────────────────────────────────────────

@api_bp.route("/stores")
def list_stores():
    """Return the list of all stores with names."""
    return jsonify(get_store_list())


@api_bp.route("/store/<store_id>/dashboard")
def store_dashboard(store_id: str):
    """Full dashboard data for a single store: inventory + weather + risk summary."""
    try:
        data = get_store_dashboard(store_id)
        return jsonify(data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/network/summary")
def network_summary():
    """Network-wide inventory risk summary across all stores."""
    try:
        summaries = get_all_stores_summary()
        network   = get_network_inventory_summary()
        return jsonify({"stores": summaries, "network": network})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Legacy compatibility routes (used by existing frontend) ────────────────────

@api_bp.route("/store_data")
def store_data_legacy():
    """Legacy route — kept for frontend compatibility."""
    store_id = request.args.get("store_id", "ST001")
    data = get_store_dashboard(store_id)
    return jsonify({
        "inventory": data["inventory"],
        "weather":   data["weather"],
    })


# ── AI Analysis ────────────────────────────────────────────────────────────────

@api_bp.route("/run_analysis", methods=["POST"])
def run_analysis_route():
    """
    Run AI waste reduction analysis for a store.

    Body: {"store_id": "ST001"}
    Returns: decisions, savings, ESG metrics, ai_mode
    """
    body     = request.json or {}
    store_id = body.get("store_id", "ST001")
    try:
        result = run_analysis(store_id)
        return jsonify(result)
    except Exception as e:
        current_app.logger.error(f"Analysis error for {store_id}: {e}")
        return jsonify({"error": str(e)}), 500


# ── Decisions ─────────────────────────────────────────────────────────────────

@api_bp.route("/decisions")
def get_decisions():
    """Get decision history. Query params: store_id (optional), days (default 7)."""
    store_id = request.args.get("store_id")
    days     = int(request.args.get("days", 7))
    try:
        summary = get_decisions_summary(store_id, days)
        # Also return raw decisions for the frontend log
        log_path = __import__("pathlib").Path(__file__).parent.parent / "data" / "decisions_log.json"
        raw = []
        if log_path.exists():
            with open(log_path) as f:
                try:
                    raw = json.load(f)
                except Exception:
                    raw = []
        if store_id:
            raw = [d for d in raw if d.get("store_id") == store_id]
        raw = raw[-50:]  # last 50 decisions
        return jsonify({"summary": summary, "decisions": raw})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/esg_metrics")
def esg_metrics():
    """Compute ESG metrics from logged decisions. Query param: store_id, days."""
    store_id = request.args.get("store_id")
    days     = int(request.args.get("days", 30))
    try:
        log_path = __import__("pathlib").Path(__file__).parent.parent / "data" / "decisions_log.json"
        decisions = []
        if log_path.exists():
            with open(log_path) as f:
                try:
                    decisions = json.load(f)
                except Exception:
                    decisions = []
        if store_id:
            decisions = [d for d in decisions if d.get("store_id") == store_id]
        metrics = calculate_esg_metrics(decisions)
        return jsonify(metrics)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ── Transfers ─────────────────────────────────────────────────────────────────

@api_bp.route("/transfers")
def get_transfers():
    """Get transfers for a store. Query param: store_id."""
    store_id = request.args.get("store_id", "ST001")
    all_t    = load_transfers()
    outgoing = [t for t in all_t if t["from_store_id"] == store_id]
    incoming = [t for t in all_t if t["to_store_id"]   == store_id]
    return jsonify({"outgoing": outgoing, "incoming": incoming})


@api_bp.route("/initiate_transfer", methods=["POST"])
def initiate_transfer():
    """Create a new inter-store transfer."""
    body = request.json or {}
    try:
        transfer = create_transfer(body)
        return jsonify({"status": "SUCCESS", "transfer": transfer})
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/accept_transfer", methods=["POST"])
def accept_transfer():
    """Update transfer status (ACCEPTED / REJECTED / COMPLETED)."""
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
    except Exception as e:
        return jsonify({"error": str(e)}), 500


@api_bp.route("/transfer_impact")
def transfer_impact():
    """ESG impact from all active transfers. Query param: store_id (optional)."""
    store_id = request.args.get("store_id")
    return jsonify(get_transfer_impact(store_id))


# ── RAG Query (demo endpoint) ──────────────────────────────────────────────────

@api_bp.route("/rag_query", methods=["POST"])
def rag_query():
    """
    Query the Vertex AI RAG corpus directly.
    Body: {"query": "optimal discount for chicken breast expiring today", "top_k": 5}
    """
    body  = request.json or {}
    query = body.get("query", "")
    top_k = body.get("top_k", 5)
    if not query:
        return jsonify({"error": "query is required"}), 400
    try:
        from rag.retriever import retrieve_context
        context = retrieve_context(query, top_k=top_k)
        return jsonify({"query": query, "context": context, "top_k": top_k})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
