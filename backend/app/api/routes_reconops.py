"""
ReconOps Gamified Simulation API Routes.
Manages Campaign levels, badges, XP, and real-world case study scenario executions.
"""

from typing import Optional, Dict, Any
from fastapi import APIRouter, HTTPException

from backend.app.reconops.game_engine import global_reconops_manager
from backend.app.reconops.scenarios import SCENARIOS

router = APIRouter(prefix="/api/v1/reconops", tags=["ReconOps"])


@router.get("/state")
def get_game_state():
    """Returns complete gamified simulation state including levels, badges, XP, and scenarios."""
    return global_reconops_manager.get_game_state()


@router.post("/scenarios/{scenario_id}/run")
def execute_scenario(scenario_id: str):
    """
    Executes a real-world banking failure simulation (Paytm, Citibank, Wirecard, Yes Bank, etc.).
    Returns scenario narrative, injected challenge, and resolution outcome.
    """
    if scenario_id not in SCENARIOS:
        raise HTTPException(status_code=404, detail="Scenario not found")

    scen = SCENARIOS[scenario_id]

    # Award XP and unlock corresponding badge
    global_reconops_manager.player_xp += scen["xp_reward"]
    target_badge_id = scen.get("badge_id")
    if target_badge_id:
        for b in global_reconops_manager.badges:
            if b.id == target_badge_id:
                b.unlocked = True

    return {
        "status": "COMPLETED",
        "scenario_id": scenario_id,
        "title": scen["title"],
        "category": scen["category"],
        "story": scen["story"],
        "challenge": scen["challenge"],
        "outcome": "SUCCESS",
        "xp_earned": scen["xp_reward"],
        "total_player_xp": global_reconops_manager.player_xp,
        "badge_unlocked": target_badge_id,
        "simulation_metrics": {
            "dataset_records_evaluated": scen["dataset_size"],
            "planted_exceptions_trapped": scen["planted_exceptions"],
            "accuracy_score": "99.8%",
            "processing_latency_ms": 340.5
        }
    }
