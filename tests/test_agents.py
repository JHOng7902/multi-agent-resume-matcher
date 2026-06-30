from agents import create_deepseek_client, run_agent, run_multi_agent_workflow


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

    def create(self, model, messages, temperature):
        self.calls.append(
            {
                "model": model,
                "messages": messages,
                "temperature": temperature,
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
    assert "Resume with Python" in client.chat.completions.calls[0]["messages"][1]["content"]
    assert "job_analysis" in client.chat.completions.calls[2]["messages"][1]["content"]
    assert "interview_preparation" in client.chat.completions.calls[6]["messages"][1]["content"]


def test_create_deepseek_client_uses_deepseek_base_url():
    client = create_deepseek_client("test-key")

    assert str(client.base_url).rstrip("/") == "https://api.deepseek.com"
