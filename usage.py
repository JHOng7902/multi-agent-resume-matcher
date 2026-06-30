import os
from copy import deepcopy


# Default prices are USD per 1M tokens from the DeepSeek API pricing page.
DEFAULT_PRICING_PER_1M = {
    "deepseek-v4-flash": {
        "input_cache_hit": 0.0028,
        "input_cache_miss": 0.14,
        "output": 0.28,
    },
    "deepseek-v4-pro": {
        "input_cache_hit": 0.003625,
        "input_cache_miss": 0.435,
        "output": 0.87,
    },
}


def extract_token_usage(response) -> dict:
    api_usage = getattr(response, "usage", None)
    input_tokens = _as_int(_get_usage_value(api_usage, "prompt_tokens"))
    output_tokens = _as_int(_get_usage_value(api_usage, "completion_tokens"))
    total_tokens = _as_int(_get_usage_value(api_usage, "total_tokens")) or input_tokens + output_tokens

    details = _get_usage_value(api_usage, "prompt_tokens_details")
    cached_tokens = _as_int(_get_usage_value(details, "cached_tokens"))
    cache_miss_tokens = max(input_tokens - cached_tokens, 0)

    return {
        "input_tokens": input_tokens,
        "output_tokens": output_tokens,
        "total_tokens": total_tokens,
        "cache_hit_input_tokens": cached_tokens,
        "cache_miss_input_tokens": cache_miss_tokens,
    }


def estimate_agent_cost(model: str, usage: dict) -> float:
    pricing = get_model_pricing(model)
    cache_hit_cost = usage.get("cache_hit_input_tokens", 0) / 1_000_000 * pricing["input_cache_hit"]
    cache_miss_cost = usage.get("cache_miss_input_tokens", 0) / 1_000_000 * pricing["input_cache_miss"]
    output_cost = usage.get("output_tokens", 0) / 1_000_000 * pricing["output"]
    return cache_hit_cost + cache_miss_cost + output_cost


def build_agent_usage(agent: str, model: str, response) -> dict:
    token_usage = extract_token_usage(response)
    estimated_cost = estimate_agent_cost(model, token_usage)
    return {
        "agent": agent,
        "model": model,
        **token_usage,
        "estimated_cost_usd": estimated_cost,
    }


def summarize_usage(agent_usage: list[dict]) -> dict:
    if not agent_usage:
        return {
            "model": "N/A",
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_tokens": 0,
            "cache_hit_input_tokens": 0,
            "cache_miss_input_tokens": 0,
            "estimated_cost_usd": 0.0,
        }

    return {
        "model": agent_usage[0]["model"],
        "total_input_tokens": sum(item["input_tokens"] for item in agent_usage),
        "total_output_tokens": sum(item["output_tokens"] for item in agent_usage),
        "total_tokens": sum(item["total_tokens"] for item in agent_usage),
        "cache_hit_input_tokens": sum(item["cache_hit_input_tokens"] for item in agent_usage),
        "cache_miss_input_tokens": sum(item["cache_miss_input_tokens"] for item in agent_usage),
        "estimated_cost_usd": sum(item["estimated_cost_usd"] for item in agent_usage),
    }


def get_model_pricing(model: str) -> dict:
    pricing = _pricing_with_env_overrides()
    if model in pricing:
        return pricing[model]
    if "pro" in model.lower() or "reasoner" in model.lower():
        return pricing["deepseek-v4-pro"]
    return pricing["deepseek-v4-flash"]


def format_usd(amount: float) -> str:
    if amount < 0.01:
        return f"${amount:.4f}"
    return f"${amount:.2f}"


def _pricing_with_env_overrides() -> dict:
    pricing = deepcopy(DEFAULT_PRICING_PER_1M)
    for model in list(pricing.keys()):
        env_prefix = model.upper().replace("-", "_")
        pricing[model]["input_cache_hit"] = _env_float(
            f"{env_prefix}_INPUT_CACHE_HIT_PER_1M",
            pricing[model]["input_cache_hit"],
        )
        pricing[model]["input_cache_miss"] = _env_float(
            f"{env_prefix}_INPUT_CACHE_MISS_PER_1M",
            pricing[model]["input_cache_miss"],
        )
        pricing[model]["output"] = _env_float(
            f"{env_prefix}_OUTPUT_PER_1M",
            pricing[model]["output"],
        )
    return pricing


def _env_float(name: str, default: float) -> float:
    raw_value = os.getenv(name)
    if not raw_value:
        return default
    try:
        return float(raw_value)
    except ValueError:
        return default


def _get_usage_value(source, name: str):
    if source is None:
        return 0
    if isinstance(source, dict):
        return source.get(name, 0)
    return getattr(source, name, 0)


def _as_int(value) -> int:
    try:
        return int(value or 0)
    except (TypeError, ValueError):
        return 0
