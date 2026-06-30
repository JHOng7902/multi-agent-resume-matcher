from types import SimpleNamespace

from usage import (
    DEFAULT_PRICING_PER_1M,
    estimate_agent_cost,
    extract_token_usage,
    summarize_usage,
)


def test_extract_token_usage_reads_standard_usage_fields():
    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=1200,
            completion_tokens=300,
            total_tokens=1500,
        )
    )

    assert extract_token_usage(response) == {
        "input_tokens": 1200,
        "output_tokens": 300,
        "total_tokens": 1500,
        "cache_hit_input_tokens": 0,
        "cache_miss_input_tokens": 1200,
    }


def test_extract_token_usage_reads_cached_prompt_tokens_when_available():
    response = SimpleNamespace(
        usage=SimpleNamespace(
            prompt_tokens=1000,
            completion_tokens=250,
            total_tokens=1250,
            prompt_tokens_details=SimpleNamespace(cached_tokens=400),
        )
    )

    usage = extract_token_usage(response)

    assert usage["cache_hit_input_tokens"] == 400
    assert usage["cache_miss_input_tokens"] == 600


def test_estimate_agent_cost_uses_deepseek_v4_flash_rates():
    cost = estimate_agent_cost(
        model="deepseek-v4-flash",
        usage={
            "input_tokens": 1000,
            "output_tokens": 500,
            "total_tokens": 1500,
            "cache_hit_input_tokens": 0,
            "cache_miss_input_tokens": 1000,
        },
    )

    expected = (1000 / 1_000_000 * DEFAULT_PRICING_PER_1M["deepseek-v4-flash"]["input_cache_miss"]) + (
        500 / 1_000_000 * DEFAULT_PRICING_PER_1M["deepseek-v4-flash"]["output"]
    )
    assert cost == expected


def test_summarize_usage_totals_agents_and_costs():
    agent_usage = [
        {
            "agent": "Resume Analyzer",
            "model": "deepseek-v4-flash",
            "input_tokens": 1000,
            "output_tokens": 200,
            "total_tokens": 1200,
            "cache_hit_input_tokens": 0,
            "cache_miss_input_tokens": 1000,
            "estimated_cost_usd": 0.001,
        },
        {
            "agent": "Final Report",
            "model": "deepseek-v4-flash",
            "input_tokens": 2000,
            "output_tokens": 400,
            "total_tokens": 2400,
            "cache_hit_input_tokens": 100,
            "cache_miss_input_tokens": 1900,
            "estimated_cost_usd": 0.002,
        },
    ]

    summary = summarize_usage(agent_usage)

    assert summary["total_input_tokens"] == 3000
    assert summary["total_output_tokens"] == 600
    assert summary["total_tokens"] == 3600
    assert summary["estimated_cost_usd"] == 0.003
    assert summary["model"] == "deepseek-v4-flash"
