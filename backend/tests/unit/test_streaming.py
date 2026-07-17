"""Unit tests for SSE streaming endpoints."""

import json
import uuid
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.api.v1.streaming import (
    experience_event_stream,
    fetch_new_experiences,
    format_sse_event,
)
from app.models.experience import Experience


def _make_experience(**overrides) -> Experience:
    defaults = dict(
        id=uuid.uuid4(),
        context={"domain": "devops", "task_type": "deployment"},
        intent="Deploy FastAPI application",
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return Experience(**defaults)


class _MockSessionFactory:
    """Mock async session factory for testing the event stream."""

    def __init__(self, session):
        self._session = session

    def __call__(self):
        return self

    async def __aenter__(self):
        return self._session

    async def __aexit__(self, *args):
        return False


class TestFormatSseEvent:
    """Test format_sse_event."""

    def test_sse_format_basic(self) -> None:
        exp = _make_experience()
        event = format_sse_event(exp)

        assert event.startswith("data: ")
        assert event.endswith("\n\n")

    def test_sse_format_contains_id_intent_domain(self) -> None:
        exp = _make_experience(
            intent="Test deployment",
            context={"domain": "frontend", "task_type": "test"},
        )
        event = format_sse_event(exp)
        payload = event[len("data: "):].rstrip("\n\n")

        data = json.loads(payload)
        assert data["id"] == str(exp.id)
        assert data["intent"] == "Test deployment"
        assert data["domain"] == "frontend"

    def test_sse_format_empty_context(self) -> None:
        exp = _make_experience(context={})
        event = format_sse_event(exp)
        payload = event[len("data: "):].rstrip("\n\n")

        data = json.loads(payload)
        assert data["domain"] is None

    def test_sse_format_none_context(self) -> None:
        exp = _make_experience()
        exp.context = None
        event = format_sse_event(exp)
        payload = event[len("data: "):].rstrip("\n\n")

        data = json.loads(payload)
        assert data["domain"] is None

    def test_sse_format_valid_json(self) -> None:
        exp = _make_experience()
        event = format_sse_event(exp)
        payload = event[len("data: "):].rstrip("\n\n")

        # Should be valid JSON
        data = json.loads(payload)
        assert isinstance(data, dict)
        assert set(data.keys()) == {"id", "intent", "domain"}


class TestFetchNewExperiences:
    """Test fetch_new_experiences with mocked session."""

    @pytest.mark.asyncio
    async def test_fetch_returns_experiences(self) -> None:
        session = AsyncMock()
        exp = _make_experience()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [exp]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        experiences = await fetch_new_experiences(
            session, since=datetime.now(timezone.utc)
        )

        assert len(experiences) == 1
        assert experiences[0].id == exp.id

    @pytest.mark.asyncio
    async def test_fetch_empty(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        experiences = await fetch_new_experiences(
            session, since=datetime.now(timezone.utc)
        )

        assert experiences == []

    @pytest.mark.asyncio
    async def test_fetch_with_domain_filter(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        await fetch_new_experiences(
            session, since=datetime.now(timezone.utc), domain="devops"
        )

        session.execute.assert_awaited_once()


class TestExperienceEventStream:
    """Test the experience_event_stream generator."""

    @pytest.mark.asyncio
    async def test_stream_yields_new_experiences(self) -> None:
        exp = _make_experience()
        session = MagicMock()
        factory = _MockSessionFactory(session)

        with patch(
            "app.api.v1.streaming.fetch_new_experiences",
            new_callable=AsyncMock,
            return_value=[exp],
        ), patch("app.api.v1.streaming.asyncio.sleep", new_callable=AsyncMock):
            events = []
            async for event in experience_event_stream(
                factory, max_iterations=1
            ):
                events.append(event)

        assert len(events) == 1
        assert events[0].startswith("data: ")

    @pytest.mark.asyncio
    async def test_stream_empty_when_no_new_experiences(self) -> None:
        session = MagicMock()
        factory = _MockSessionFactory(session)

        with patch(
            "app.api.v1.streaming.fetch_new_experiences",
            new_callable=AsyncMock,
            return_value=[],
        ), patch("app.api.v1.streaming.asyncio.sleep", new_callable=AsyncMock):
            events = []
            async for event in experience_event_stream(
                factory, max_iterations=1
            ):
                events.append(event)

        assert events == []

    @pytest.mark.asyncio
    async def test_stream_multiple_iterations(self) -> None:
        exp1 = _make_experience(intent="First")
        exp2 = _make_experience(intent="Second")
        session = MagicMock()
        factory = _MockSessionFactory(session)

        call_count = 0
        experiences_sequence = [[exp1], [], [exp2]]

        async def mock_fetch(*args, **kwargs):
            nonlocal call_count
            result = experiences_sequence[call_count]
            call_count += 1
            return result

        with patch(
            "app.api.v1.streaming.fetch_new_experiences",
            side_effect=mock_fetch,
        ), patch("app.api.v1.streaming.asyncio.sleep", new_callable=AsyncMock):
            events = []
            async for event in experience_event_stream(
                factory, max_iterations=3
            ):
                events.append(event)

        assert len(events) == 2
        assert "First" in events[0]
        assert "Second" in events[1]

    @pytest.mark.asyncio
    async def test_stream_domain_passed_to_fetch(self) -> None:
        session = MagicMock()
        factory = _MockSessionFactory(session)

        with patch(
            "app.api.v1.streaming.fetch_new_experiences",
            new_callable=AsyncMock,
            return_value=[],
        ) as mock_fetch, patch(
            "app.api.v1.streaming.asyncio.sleep", new_callable=AsyncMock
        ):
            async for _ in experience_event_stream(
                factory, domain="devops", max_iterations=1
            ):
                pass

        mock_fetch.assert_awaited_once()
        call_args = mock_fetch.call_args
        # domain is passed as the 3rd positional arg
        domain_arg = call_args.args[2] if len(call_args.args) > 2 else call_args.kwargs.get("domain")
        assert domain_arg == "devops"

    @pytest.mark.asyncio
    async def test_stream_updates_since_timestamp(self) -> None:
        """新经验的 created_at 应更新 since 时间戳."""
        later = datetime.now(timezone.utc) + timedelta(seconds=10)
        exp = _make_experience(created_at=later)
        session = MagicMock()
        factory = _MockSessionFactory(session)

        with patch(
            "app.api.v1.streaming.fetch_new_experiences",
            new_callable=AsyncMock,
            return_value=[exp],
        ) as mock_fetch, patch(
            "app.api.v1.streaming.asyncio.sleep", new_callable=AsyncMock
        ):
            async for _ in experience_event_stream(
                factory, max_iterations=2
            ):
                pass

        # Second call should use the exp's created_at as since
        second_call_args = mock_fetch.call_args_list[1]
        second_since = second_call_args.kwargs.get("since") or second_call_args.args[1]
        assert second_since == later


class TestStreamingEndpoints:
    """Test the SSE endpoints via HTTP client."""

    @pytest.mark.asyncio
    async def test_stream_experiences_headers(self, client) -> None:
        async def _finite_stream(*args, **kwargs):
            yield "data: {\"id\": \"1\", \"intent\": \"test\", \"domain\": \"devops\"}\n\n"

        with patch(
            "app.api.v1.streaming.experience_event_stream", _finite_stream
        ):
            response = await client.get("/api/v1/stream/experiences")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"

    @pytest.mark.asyncio
    async def test_stream_experiences_sse_format(self, client) -> None:
        async def _finite_stream(*args, **kwargs):
            yield "data: {\"id\": \"1\", \"intent\": \"deploy\", \"domain\": \"devops\"}\n\n"

        with patch(
            "app.api.v1.streaming.experience_event_stream", _finite_stream
        ):
            response = await client.get("/api/v1/stream/experiences")

        text = response.text
        assert text.startswith("data: ")
        assert text.endswith("\n\n")

    @pytest.mark.asyncio
    async def test_stream_domain_endpoint_headers(self, client) -> None:
        async def _finite_stream(*args, **kwargs):
            return
            yield  # make it a generator

        with patch(
            "app.api.v1.streaming.experience_event_stream", _finite_stream
        ):
            response = await client.get("/api/v1/stream/domain/devops")

        assert response.status_code == 200
        assert response.headers["content-type"].startswith("text/event-stream")
        assert response.headers["cache-control"] == "no-cache"

    @pytest.mark.asyncio
    async def test_stream_domain_endpoint_passes_domain(self, client) -> None:
        captured_domain = None

        async def _capturing_stream(*args, **kwargs):
            nonlocal captured_domain
            captured_domain = kwargs.get("domain")
            return
            yield  # make it a generator

        with patch(
            "app.api.v1.streaming.experience_event_stream", _capturing_stream
        ):
            await client.get("/api/v1/stream/domain/frontend")

        assert captured_domain == "frontend"

    @pytest.mark.asyncio
    async def test_stream_empty_response(self, client) -> None:
        async def _empty_stream(*args, **kwargs):
            return
            yield  # make it a generator

        with patch(
            "app.api.v1.streaming.experience_event_stream", _empty_stream
        ):
            response = await client.get("/api/v1/stream/experiences")

        assert response.status_code == 200
        assert response.text == ""
