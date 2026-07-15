"""Unit tests for ExperienceGraph - 图谱关系管理."""

import uuid
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest

from app.models.experience import ExperienceRelation
from app.schemas.experience import RelationCreate
from app.services.experience.graph import ExperienceGraph


def _make_relation(**overrides) -> ExperienceRelation:
    """Build an ExperienceRelation for testing."""
    defaults = dict(
        id=uuid.uuid4(),
        source_id=uuid.uuid4(),
        target_id=uuid.uuid4(),
        relation_type="reuse",
        weight=1.0,
        metadata_={},
        created_at=datetime.now(timezone.utc),
    )
    defaults.update(overrides)
    return ExperienceRelation(**defaults)


class TestAddRelation:
    """Test add_relation."""

    @pytest.mark.asyncio
    async def test_add_relation_success(self) -> None:
        session = AsyncMock()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        session.refresh = AsyncMock(side_effect=lambda obj: setattr(obj, "id", uuid.uuid4()))

        repo = ExperienceGraph(session)
        data = RelationCreate(
            target_id=target_id,
            relation_type="reuse",
            weight=0.8,
            metadata={"key": "value"},
        )

        result = await repo.add_relation(source_id, data)

        session.add.assert_called_once()
        session.flush.assert_awaited_once()
        session.refresh.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_add_relation_maps_fields(self) -> None:
        session = AsyncMock()
        source_id = uuid.uuid4()
        target_id = uuid.uuid4()

        repo = ExperienceGraph(session)
        data = RelationCreate(
            target_id=target_id,
            relation_type="citation",
            weight=0.5,
            metadata={"source": "test"},
        )

        await repo.add_relation(source_id, data)

        added_obj = session.add.call_args[0][0]
        assert added_obj.source_id == source_id
        assert added_obj.target_id == target_id
        assert added_obj.relation_type == "citation"
        assert added_obj.weight == 0.5
        assert added_obj.metadata_ == {"source": "test"}


class TestGetRelations:
    """Test get_relations."""

    @pytest.mark.asyncio
    async def test_get_outgoing_relations(self) -> None:
        session = AsyncMock()
        exp_id = uuid.uuid4()
        rel = _make_relation(source_id=exp_id)

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [rel]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        graph = ExperienceGraph(session)
        results = await graph.get_relations(exp_id, direction="outgoing")

        assert len(results) == 1
        assert results[0] is rel
        session.execute.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_get_incoming_relations(self) -> None:
        session = AsyncMock()
        exp_id = uuid.uuid4()
        rel = _make_relation(target_id=exp_id)

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [rel]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        graph = ExperienceGraph(session)
        results = await graph.get_relations(exp_id, direction="incoming")

        assert len(results) == 1
        assert results[0] is rel

    @pytest.mark.asyncio
    async def test_get_both_directions(self) -> None:
        session = AsyncMock()
        exp_id = uuid.uuid4()
        rel_out = _make_relation(source_id=exp_id)
        rel_in = _make_relation(target_id=exp_id)

        result1 = MagicMock()
        s1 = MagicMock()
        s1.all.return_value = [rel_out]
        result1.scalars.return_value = s1

        result2 = MagicMock()
        s2 = MagicMock()
        s2.all.return_value = [rel_in]
        result2.scalars.return_value = s2

        session.execute.side_effect = [result1, result2]

        graph = ExperienceGraph(session)
        results = await graph.get_relations(exp_id, direction="both")

        assert len(results) == 2
        assert session.execute.await_count == 2

    @pytest.mark.asyncio
    async def test_get_with_relation_type_filter(self) -> None:
        session = AsyncMock()
        exp_id = uuid.uuid4()
        rel = _make_relation(source_id=exp_id, relation_type="reuse")

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [rel]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        graph = ExperienceGraph(session)
        results = await graph.get_relations(exp_id, direction="outgoing", relation_type="reuse")

        assert len(results) == 1


class TestRemoveRelation:
    """Test remove_relation."""

    @pytest.mark.asyncio
    async def test_remove_success(self) -> None:
        session = AsyncMock()
        rel = _make_relation()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = rel
        session.execute.return_value = result_mock

        graph = ExperienceGraph(session)
        result = await graph.remove_relation(rel.id)

        assert result is True
        session.delete.assert_awaited_once_with(rel)
        session.flush.assert_awaited_once()

    @pytest.mark.asyncio
    async def test_remove_not_found(self) -> None:
        session = AsyncMock()
        result_mock = MagicMock()
        result_mock.scalar_one_or_none.return_value = None
        session.execute.return_value = result_mock

        graph = ExperienceGraph(session)
        result = await graph.remove_relation(uuid.uuid4())

        assert result is False
        session.delete.assert_not_awaited()


class TestGetConnectedExperiences:
    """Test get_connected_experiences (BFS traversal)."""

    @pytest.mark.asyncio
    async def test_bfs_single_level(self) -> None:
        session = AsyncMock()
        exp_id = uuid.uuid4()
        neighbor_id = uuid.uuid4()
        rel = _make_relation(source_id=exp_id, target_id=neighbor_id, relation_type="reuse", weight=0.9)

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [rel]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        graph = ExperienceGraph(session)
        results = await graph.get_connected_experiences(exp_id, max_depth=1)

        assert len(results) == 1
        assert results[0]["experience_id"] == str(neighbor_id)
        assert results[0]["relation_type"] == "reuse"
        assert results[0]["direction"] == "outgoing"
        assert results[0]["weight"] == 0.9
        assert results[0]["depth"] == 1

    @pytest.mark.asyncio
    async def test_bfs_no_connections(self) -> None:
        session = AsyncMock()
        exp_id = uuid.uuid4()

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = []
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        graph = ExperienceGraph(session)
        results = await graph.get_connected_experiences(exp_id, max_depth=2)

        assert results == []

    @pytest.mark.asyncio
    async def test_bfs_incoming_direction(self) -> None:
        session = AsyncMock()
        exp_id = uuid.uuid4()
        source_id = uuid.uuid4()
        rel = _make_relation(source_id=source_id, target_id=exp_id, relation_type="citation")

        result_mock = MagicMock()
        scalars_mock = MagicMock()
        scalars_mock.all.return_value = [rel]
        result_mock.scalars.return_value = scalars_mock
        session.execute.return_value = result_mock

        graph = ExperienceGraph(session)
        results = await graph.get_connected_experiences(exp_id, max_depth=1)

        assert len(results) == 1
        assert results[0]["direction"] == "incoming"
        assert results[0]["experience_id"] == str(source_id)

    @pytest.mark.asyncio
    async def test_bfs_multi_level(self) -> None:
        session = AsyncMock()
        exp_id = uuid.uuid4()
        level1_id = uuid.uuid4()
        level2_id = uuid.uuid4()

        rel1 = _make_relation(source_id=exp_id, target_id=level1_id, relation_type="reuse")
        rel2 = _make_relation(source_id=level1_id, target_id=level2_id, relation_type="dependency")

        # get_relations with direction="both" makes 2 session.execute calls per call
        # Depth 1: get_relations(exp_id) -> [outgoing: [rel1], incoming: []]
        # Depth 2: get_relations(level1_id) -> [outgoing: [rel2], incoming: []]
        def _make_result(rels):
            r = MagicMock()
            s = MagicMock()
            s.all.return_value = rels
            r.scalars.return_value = s
            return r

        session.execute.side_effect = [
            _make_result([rel1]), _make_result([]),  # depth 1: exp_id
            _make_result([rel2]), _make_result([]),  # depth 2: level1_id
        ]

        graph = ExperienceGraph(session)
        results = await graph.get_connected_experiences(exp_id, max_depth=2)

        assert len(results) == 2
        assert results[0]["depth"] == 1
        assert results[1]["depth"] == 2

    @pytest.mark.asyncio
    async def test_bfs_avoids_cycles(self) -> None:
        session = AsyncMock()
        exp_id = uuid.uuid4()
        neighbor_id = uuid.uuid4()

        # exp -> neighbor (reuse), neighbor -> exp (dependency) -- cycle
        rel1 = _make_relation(source_id=exp_id, target_id=neighbor_id, relation_type="reuse")
        rel2 = _make_relation(source_id=neighbor_id, target_id=exp_id, relation_type="dependency")

        # get_relations with direction="both" makes 2 session.execute calls per call
        # Depth 1: get_relations(exp_id) -> [outgoing: [rel1], incoming: [rel2]]
        # Depth 2: get_relations(neighbor_id) -> [outgoing: [], incoming: []]
        def _make_result(rels):
            r = MagicMock()
            s = MagicMock()
            s.all.return_value = rels
            r.scalars.return_value = s
            return r

        session.execute.side_effect = [
            _make_result([rel1]), _make_result([rel2]),  # depth 1: exp_id
            _make_result([]), _make_result([]),          # depth 2: neighbor_id
        ]

        graph = ExperienceGraph(session)
        results = await graph.get_connected_experiences(exp_id, max_depth=3)

        # exp_id should only appear once (as start), neighbor_id once (depth 1)
        # The cycle back to exp_id should be skipped
        ids = [r["experience_id"] for r in results]
        assert str(neighbor_id) in ids
        assert str(exp_id) not in ids  # exp_id is the start, not included in results
