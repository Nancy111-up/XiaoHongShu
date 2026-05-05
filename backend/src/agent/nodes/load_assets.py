"""load_assets 节点 —— 加载全部 4 份品牌资产到 state 上下文

从 write_node 中拆出为独立节点，供后续 generate_copy / generate_visuals / finalize 使用
"""

from __future__ import annotations

from src.agent.state import AgentState
from src.services.asset_loader import load_asset


async def load_assets_node(state: AgentState) -> dict:
    return {
        "brand_context": load_asset("brand_voice.md"),
        "product_context": load_asset("product_info.md"),
        "best_practices": load_asset("best_practices.md"),
        "negative_prompts": load_asset("negative_prompts.md"),
        "current_step": "load_assets_complete",
    }
