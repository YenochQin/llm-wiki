import io
import json
import sys
from pathlib import Path

import httpx
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "tools"))

import api_review


@pytest.fixture
def vault(tmp_path, monkeypatch):
    config = tmp_path / "paths.toml"
    config.write_text(
        f"[wiki]\nroot_dir = {json.dumps(str(tmp_path))}\n", encoding="utf-8"
    )
    root = tmp_path / "wiki"
    for directory in ("claims", "concepts", "papers"):
        (root / directory).mkdir(parents=True)
    monkeypatch.delenv("LLM_WIKI_WIKI_ROOT", raising=False)
    monkeypatch.setenv("LLM_BASE_URL", "https://review.example/v1/")
    monkeypatch.setenv("LLM_MODEL", "chosen-model")
    monkeypatch.setenv("LLM_API_KEY", "dummy-secret")
    return root, ["--paths-config", str(config)]


def install_transport(monkeypatch, handler):
    def post(url, **kwargs):
        with httpx.Client(transport=httpx.MockTransport(handler)) as client:
            return client.post(url, **kwargs)

    monkeypatch.setattr(api_review.httpx, "post", post)


def test_posts_artifact_and_selected_wiki_evidence(vault, monkeypatch, capsys):
    wiki, options = vault
    artifact = "# Claim\nSupporting record [[paper#Results|evidence]].\n`[[code]]`\n[[escape]]\n[[missing]]"
    (wiki / "claims/example.md").write_text(artifact, encoding="utf-8")
    (wiki / "claims/code.md").write_text(
        "Do not select a code example.", encoding="utf-8"
    )
    (wiki / "papers/paper.md").write_text("Recorded result. " * 500, encoding="utf-8")
    (wiki / "concepts/definition.md").write_text(
        "Scope of measurement.", encoding="utf-8"
    )
    outside = wiki.parent / "outside.md"
    outside.write_text("Outside the wiki.", encoding="utf-8")
    (wiki / "papers/escape.md").symlink_to(outside)
    calls = []

    def respond(request):
        calls.append(request)
        return httpx.Response(
            200,
            json={
                "model": "served-model",
                "choices": [{"message": {"content": "Verify the measurement scope."}}],
            },
        )

    install_transport(monkeypatch, respond)
    assert (
        api_review.main(
            [*options, "example", "--context", "definition", "--focus", "scope"]
        )
        == 0
    )
    result = json.loads(capsys.readouterr().out)
    assert len(calls) == 1
    request = calls[0]
    assert request.url == "https://review.example/v1/chat/completions"
    assert request.headers["Authorization"] == "Bearer dummy-secret"
    body = json.loads(request.content)
    assert body["model"] == "chosen-model"
    material = json.loads(body["messages"][1]["content"])
    assert material["review_focus"] == "scope"
    assert material["artifact"] == {"path": "claims/example.md", "text": artifact}
    assert material["wiki_context"] == [
        {
            "path": "concepts/definition.md",
            "text": "Scope of measurement.",
            "truncated": False,
        },
        {
            "path": "papers/paper.md",
            "text": ("Recorded result. " * 500)[:6000],
            "truncated": True,
        },
    ]
    assert result["provider"] == "review.example"
    assert result["model"] == "served-model"
    assert result["review"] == "Verify the measurement scope."
    assert result["unresolved_wikilinks"] == ["escape", "missing"]


def test_preview_from_stdin_has_no_secrets_or_api_call(vault, monkeypatch, capsys):
    wiki, options = vault
    (wiki / "papers/paper.md").write_text("supplied evidence", encoding="utf-8")
    monkeypatch.setattr(sys, "stdin", io.StringIO("pasted draft [[paper]]"))
    monkeypatch.setattr(
        api_review.httpx, "post", lambda *a, **k: pytest.fail("preview made a request")
    )
    assert api_review.main([*options, "-", "--dry-run", "--no-linked-context"]) == 0
    output = capsys.readouterr().out
    result = json.loads(output)
    assert result["status"] == "dry-run"
    assert result["context"] == []
    assert result["artifact"]["path"] == "stdin"
    assert "pasted draft" not in output
    assert "dummy-secret" not in output


def test_ambiguous_context_blocks_submission(vault, monkeypatch, capsys):
    wiki, options = vault
    for path in ("claims/target.md", "papers/shared.md", "concepts/shared.md"):
        (wiki / path).write_text("Text", encoding="utf-8")
    monkeypatch.setattr(
        api_review.httpx, "post", lambda *a, **k: pytest.fail("ambiguous submission")
    )
    assert api_review.main([*options, "target", "--context", "shared"]) == 1
    error = capsys.readouterr().err
    assert "ambiguous wiki page" in error
    assert "papers/shared.md" in error and "concepts/shared.md" in error


def test_redirect_does_not_forward_artifact_or_credentials(vault, monkeypatch, capsys):
    wiki, options = vault
    (wiki / "claims/target.md").write_text("Artifact", encoding="utf-8")
    calls = []

    def redirect(request):
        calls.append(request.url.host)
        return httpx.Response(
            307, headers={"Location": "https://other.example/"}, text="private body"
        )

    install_transport(monkeypatch, redirect)
    assert api_review.main([*options, "target"]) == 1
    assert calls == ["review.example"]
    output = capsys.readouterr()
    assert "HTTP 307" in output.err
    assert "private body" not in output.err and "dummy-secret" not in output.err
    assert not output.out
