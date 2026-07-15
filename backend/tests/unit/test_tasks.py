"""Unit tests for Celery async tasks."""

from unittest.mock import AsyncMock, MagicMock, patch

import pytest


class TestExecuteTaskAsync:
    """Test execute_task_async Celery task."""

    def test_execute_task_async_success(self) -> None:
        """Test that the Celery task calls the pipeline and returns result dict."""
        from app.services.execution.tasks import execute_task_async

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {
            "task_id": "test-task-id",
            "status": "completed",
            "experience_id": "exp-001",
            "steps": [],
            "total_duration_ms": 100.0,
            "error": None,
        }

        mock_pipeline = MagicMock()
        mock_pipeline.run = AsyncMock(return_value=mock_result)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.execution.pipeline.ExperiencePipeline", return_value=mock_pipeline) as mock_pipeline_cls, \
             patch("app.core.database.async_session_factory", return_value=mock_session):
            result = execute_task_async(
                intent="Deploy application",
                context={"domain": "devops"},
                constraints={"env": "prod"},
            )

        assert result["task_id"] == "test-task-id"
        assert result["status"] == "completed"
        mock_pipeline.run.assert_awaited_once()

    def test_execute_task_async_with_defaults(self) -> None:
        """Test Celery task with default None parameters."""
        from app.services.execution.tasks import execute_task_async

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"status": "completed"}

        mock_pipeline = MagicMock()
        mock_pipeline.run = AsyncMock(return_value=mock_result)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        with patch("app.services.execution.pipeline.ExperiencePipeline", return_value=mock_pipeline), \
             patch("app.core.database.async_session_factory", return_value=mock_session):
            result = execute_task_async(intent="Simple task")

        assert result["status"] == "completed"
        mock_pipeline.run.assert_awaited_once_with(
            intent="Simple task",
            context=None,
            constraints=None,
            workflow=None,
        )

    def test_execute_task_async_with_workflow(self) -> None:
        """Test Celery task with workflow parameter."""
        from app.services.execution.tasks import execute_task_async

        mock_result = MagicMock()
        mock_result.model_dump.return_value = {"status": "completed", "experience_id": "exp-123"}

        mock_pipeline = MagicMock()
        mock_pipeline.run = AsyncMock(return_value=mock_result)

        mock_session = AsyncMock()
        mock_session.__aenter__ = AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = AsyncMock(return_value=None)

        workflow = [{"name": "step1", "action": "execute"}]

        with patch("app.services.execution.pipeline.ExperiencePipeline", return_value=mock_pipeline), \
             patch("app.core.database.async_session_factory", return_value=mock_session):
            result = execute_task_async(
                intent="Workflow task",
                workflow=workflow,
            )

        assert result["experience_id"] == "exp-123"
        mock_pipeline.run.assert_awaited_once()

    def test_task_is_registered(self) -> None:
        """Test that the task is registered with Celery."""
        from app.services.execution.tasks import execute_task_async

        # The task should have a name attribute
        assert execute_task_async.name == "execute_task_async"
