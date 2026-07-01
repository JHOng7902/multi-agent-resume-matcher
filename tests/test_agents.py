import pytest

from agents import (
    RETRY_MAX_TOKENS,
    create_deepseek_client,
    run_agent,
    run_agent_with_usage,
    run_multi_agent_workflow,
)


class FakeMessage:
    def __init__(self, content):
        self.content = content


class FakeChoice:
    def __init__(self, content):
        self.message = FakeMessage(content)


class FakeResponse:
    def __init__(self, content):
        self.choices = [FakeChoice(content)]
        self.usage = type(
            "FakeUsage",
            (),
            {
                "prompt_tokens": 100,
                "completion_tokens": 25,
                "total_tokens": 125,
            },
        )()


class FakeCompletions:
    def __init__(self):
        self.calls = []

    def create(self, model, messages, temperature, max_tokens=None):
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens,
            }
        )
        agent_name = messages[0]["content"].splitlines()[0]
        return FakeResponse(f"output for {agent_name}")


class FakeChat:
    def __init__(self):
        self.completions = FakeCompletions()


class FakeClient:
    def __init__(self):
        self.chat = FakeChat()


def test_run_agent_sends_system_and_user_messages_to_client():
    client = FakeClient()

    output = run_agent(
        client=client,
        model="deepseek-v4-flash",
        agent_name="Resume Analyzer Agent",
        system_prompt="You are a Resume Analyzer Agent.",
        user_input="Resume text",
    )

    assert output == "output for You are a Resume Analyzer Agent."
    assert client.chat.completions.calls[0]["model"] == "deepseek-v4-flash"
    assert client.chat.completions.calls[0]["messages"] == [
        {"role": "system", "content": "You are a Resume Analyzer Agent."},
        {"role": "user", "content": "Resume text"},
    ]


def test_run_multi_agent_workflow_returns_all_expected_outputs():
    client = FakeClient()

    result = run_multi_agent_workflow(
        client=client,
        model="deepseek-v4-flash",
        resume_text="Resume with Python, SQL, and testing experience.",
        job_description="Software tester job requiring SQL and JIRA.",
    )

    assert list(result.keys()) == [
        "resume_analysis",
        "job_analysis",
        "skill_matching",
        "gap_analysis",
        "resume_improvement",
        "interview_preparation",
        "final_report",
        "usage",
    ]
    assert list(result["usage"].keys()) == ["agents", "summary"]
    assert len(result["usage"]["agents"]) == 7
    assert result["usage"]["summary"]["total_tokens"] == 875
    assert result["usage"]["summary"]["model"] == "deepseek-v4-flash"
    assert len(client.chat.completions.calls) == 7
    # Stage 1 runs the resume and job analyzers concurrently, so their call
    # order is not guaranteed; assert the resume text reached one of them.
    stage1 = (
        client.chat.completions.calls[0]["messages"][1]["content"]
        + client.chat.completions.calls[1]["messages"][1]["content"]
    )
    assert "Resume with Python" in stage1
    assert "job_analysis" in client.chat.completions.calls[2]["messages"][1]["content"]
    assert "interview_preparation" in client.chat.completions.calls[6]["messages"][1]["content"]


class _ReasoningMessage:
    def __init__(self, content, reasoning_content):
        self.content = content
        self.reasoning_content = reasoning_content


class _ScriptedCompletions:
    """Returns queued responses in order to simulate empty replies / fallbacks."""

    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = []

    def create(self, model, messages, temperature, max_tokens=None):
        self.calls.append({"max_tokens": max_tokens})
        return self._responses.pop(0)


def _client_returning(responses):
    client = FakeClient()
    client.chat.completions = _ScriptedCompletions(responses)
    return client


def _truncated_response(content):
    response = FakeResponse(content)
    response.choices[0].finish_reason = "length"
    return response


def test_run_agent_falls_back_to_reasoning_content_when_content_is_empty():
    response = FakeResponse("")
    response.choices = [type("C", (), {"message": _ReasoningMessage("", "reasoned answer")})()]
    client = _client_returning([response])

    output = run_agent(client, "m", "Agent", "sys", "user")

    assert output == "reasoned answer"
    assert len(client.chat.completions.calls) == 1


def test_run_agent_retries_once_with_more_tokens_on_empty_reply():
    client = _client_returning([FakeResponse(""), FakeResponse("recovered output")])

    content, _ = run_agent_with_usage(client, "m", "Agent", "sys", "user", max_tokens=700)

    assert content == "recovered output"
    assert [c["max_tokens"] for c in client.chat.completions.calls] == [700, RETRY_MAX_TOKENS]


def test_run_agent_retries_when_reply_is_truncated():
    client = _client_returning([_truncated_response("cut off..."), FakeResponse("complete answer")])

    output = run_agent(client, "m", "Agent", "sys", "user", max_tokens=700)

    assert output == "complete answer"
    assert [c["max_tokens"] for c in client.chat.completions.calls] == [700, RETRY_MAX_TOKENS]


def test_run_agent_keeps_truncated_content_if_retry_also_truncates():
    client = _client_returning([_truncated_response("partial one"), _truncated_response("partial two")])

    output = run_agent(client, "m", "Agent", "sys", "user")

    assert output == "partial two"


def test_run_agent_raises_when_still_empty_after_retry():
    client = _client_returning([FakeResponse(""), FakeResponse("")])

    with pytest.raises(RuntimeError, match="empty response"):
        run_agent(client, "m", "Agent", "sys", "user")


def test_create_deepseek_client_uses_deepseek_base_url():
    client = create_deepseek_client("test-key")

    assert str(client.base_url).rstrip("/") == "https://api.deepseek.com"
