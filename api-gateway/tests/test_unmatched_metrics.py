"""
Tests for unmatched metrics processing.

Covers:
- Task 1: Synonym exact match in RAG mapping (report_rag_mapping.py)
- Task 2: Synonym validation against metric names (metric_generation.py)
- Task 3: Auto-generation trigger and unmatched metrics processing

Markers:
- unit: Pure unit tests with mocked dependencies
"""

import uuid
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
import pytest_asyncio
from sqlalchemy.ext.asyncio import AsyncSession

from app.services.report_rag_mapping import RagMappingService, _norm_synonym


# ==================== Task 1: Synonym exact match in RAG ====================


@pytest.mark.unit
class TestNormSynonym:
    """Test the _norm_synonym helper function."""

    def test_basic_normalization(self):
        assert _norm_synonym("Hello World") == "hello world"

    def test_strips_whitespace(self):
        assert _norm_synonym("  test  ") == "test"

    def test_nfkc_normalization(self):
        # NFKC normalizes compatibility characters
        assert _norm_synonym("ﬁ") == "fi"  # fi ligature -> fi

    def test_case_insensitive(self):
        assert _norm_synonym("УПРАВЛЕНЧЕСКИЙ ОПЫТ") == _norm_synonym("управленческий опыт")

    def test_empty_string(self):
        assert _norm_synonym("") == ""


@pytest.mark.unit
class TestRagMappingSynonymMatch:
    """Test synonym matching in RagMappingService."""

    @pytest_asyncio.fixture
    async def mock_db(self):
        """Create a mock async session."""
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest_asyncio.fixture
    async def service(self, mock_db):
        """Create RagMappingService with mocked dependencies."""
        service = RagMappingService(db=mock_db)
        return service

    @pytest.mark.asyncio
    async def test_map_label_synonym_match(self, service):
        """When label matches a synonym, should return mapped with source=synonym."""
        # Pre-populate synonym cache directly
        service._synonym_cache = {
            "управленческий опыт": "upravlencheskiy_opyt",
            "актуальный потенциал": "aktualnyy_potentsial",
        }

        result = await service.map_label("Управленческий опыт")

        assert result["status"] == "mapped"
        assert result["code"] == "upravlencheskiy_opyt"
        assert result["source"] == "synonym"
        assert result["similarity"] == 1.0

    @pytest.mark.asyncio
    async def test_map_label_synonym_no_match_falls_through(self, service):
        """When label doesn't match a synonym, should fall through to RAG."""
        service._synonym_cache = {
            "нормативность": "normativnost",
        }

        # Mock embedding service to avoid actual API calls
        mock_embedding_service = AsyncMock()
        mock_embedding_service.find_similar = AsyncMock(return_value=[])
        service._embedding_service = mock_embedding_service

        result = await service.map_label("Некая Неизвестная Метрика")

        assert result["status"] == "unknown"
        assert result["source"] is None
        # Verify RAG was called (fell through synonym check)
        mock_embedding_service.find_similar.assert_called_once()

    @pytest.mark.asyncio
    async def test_map_labels_batch_synonym_match(self, service):
        """Batch: labels matching synonyms should be resolved without RAG."""
        service._synonym_cache = {
            "управленческий опыт": "upravlencheskiy_opyt",
        }

        # Mock embedding service - should NOT be called for synonym-matched labels
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embeddings = AsyncMock(return_value=[])
        service._embedding_service = mock_embedding_service

        results = await service.map_labels_batch(["Управленческий опыт"])

        assert len(results) == 1
        assert results[0]["status"] == "mapped"
        assert results[0]["source"] == "synonym"
        assert results[0]["code"] == "upravlencheskiy_opyt"
        # Embedding generation should not be called when all match synonyms
        mock_embedding_service.generate_embeddings.assert_not_called()

    @pytest.mark.asyncio
    async def test_map_labels_batch_mixed(self, service):
        """Batch: mix of synonym-matched and unmatched labels."""
        service._synonym_cache = {
            "управленческий опыт": "upravlencheskiy_opyt",
        }

        # Mock embedding service for the non-synonym label
        mock_embedding_service = AsyncMock()
        mock_embedding_service.generate_embeddings = AsyncMock(return_value=[[0.1] * 3072])
        mock_embedding_service.find_similar_by_embedding = AsyncMock(return_value=[])
        service._embedding_service = mock_embedding_service

        results = await service.map_labels_batch(["Управленческий опыт", "Неизвестная"])

        assert len(results) == 2
        # First label matched by synonym
        assert results[0]["status"] == "mapped"
        assert results[0]["source"] == "synonym"
        # Second label went through RAG (no candidates -> unknown)
        assert results[1]["status"] == "unknown"

    @pytest.mark.asyncio
    async def test_load_synonyms_caching(self, service, mock_db):
        """Synonyms should be loaded once and cached."""
        # Mock DB queries: first for synonyms, second for metric names
        synonym_result = MagicMock()
        synonym_result.all.return_value = [
            ("Управленческий опыт", "upravlencheskiy_opyt"),
            ("Актуальный потенциал", "aktualnyy_potentsial"),
        ]
        name_result = MagicMock()
        name_result.all.return_value = []  # No extra metric names
        mock_db.execute = AsyncMock(side_effect=[synonym_result, name_result])

        # First call - loads from DB (2 queries: synonyms + metric names)
        synonyms1 = await service._load_synonyms()
        assert len(synonyms1) == 2
        assert mock_db.execute.call_count == 2

        # Second call - uses cache
        synonyms2 = await service._load_synonyms()
        assert synonyms2 is synonyms1
        assert mock_db.execute.call_count == 2  # Not called again

    @pytest.mark.asyncio
    async def test_synonym_for_rejected_metric_ignored(self, service, mock_db):
        """Synonyms for REJECTED metrics should not be loaded."""
        # The SQL query filters by moderation_status == "APPROVED"
        # If the DB returns nothing (because the metric is REJECTED), synonym_cache is empty
        mock_result = MagicMock()
        mock_result.all.return_value = []
        mock_db.execute = AsyncMock(return_value=mock_result)

        synonyms = await service._load_synonyms()
        assert len(synonyms) == 0


# ==================== Task 2: Synonym validation ====================


@pytest.mark.unit
class TestSynonymCollisionValidation:
    """Test that synonym validation prevents collisions with metric names."""

    @pytest_asyncio.fixture
    async def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        return db

    @pytest.mark.asyncio
    async def test_collision_with_metric_name(self, mock_db):
        """Synonym matching name of another metric should be rejected."""
        from app.services.metric_generation import MetricGenerationService

        service = MetricGenerationService.__new__(MetricGenerationService)
        service.db = mock_db

        # Create mock rows as tuples (id, name, name_ru, code)
        id1 = uuid.uuid4()
        id2 = uuid.uuid4()
        mock_rows = [
            (id1, "Управленческий опыт", "Управленческий опыт", "upravlencheskiy_opyt"),
            (id2, "Потенциал к руководству", "Потенциал к руководству", "potentsial_k_rukovodstvu"),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Trying to add "Управленческий опыт" as synonym for metric2 should collide
        collides = await service._synonym_collides_with_metric(
            "Управленческий опыт",
            exclude_metric_id=id2,
        )
        assert collides is True

    @pytest.mark.asyncio
    async def test_no_collision_for_same_metric(self, mock_db):
        """Synonym matching name of the SAME metric is OK (not a collision)."""
        from app.services.metric_generation import MetricGenerationService

        service = MetricGenerationService.__new__(MetricGenerationService)
        service.db = mock_db

        id1 = uuid.uuid4()
        mock_rows = [
            (id1, "Управленческий опыт", "Управленческий опыт", "upravlencheskiy_opyt"),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        # Trying to add "Управленческий опыт" as synonym for metric1 (same) - no collision
        collides = await service._synonym_collides_with_metric(
            "Управленческий опыт",
            exclude_metric_id=id1,
        )
        assert collides is False

    @pytest.mark.asyncio
    async def test_no_collision_for_unique_synonym(self, mock_db):
        """Unique synonym that doesn't match any metric name should pass."""
        from app.services.metric_generation import MetricGenerationService

        service = MetricGenerationService.__new__(MetricGenerationService)
        service.db = mock_db

        id1 = uuid.uuid4()
        mock_rows = [
            (id1, "Нормативность", "Нормативность", "normativnost"),
        ]

        mock_result = MagicMock()
        mock_result.all.return_value = mock_rows
        mock_db.execute = AsyncMock(return_value=mock_result)

        collides = await service._synonym_collides_with_metric(
            "Совершенно другой текст",
            exclude_metric_id=None,
        )
        assert collides is False


# ==================== Task 3: Unmatched metrics processing ====================


@pytest.mark.unit
class TestProcessUnmatchedMetrics:
    """Test process_unmatched_metrics method."""

    @pytest_asyncio.fixture
    async def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest_asyncio.fixture
    async def service(self, mock_db):
        """Create MetricGenerationService with mocked dependencies."""
        from app.services.metric_generation import MetricGenerationService

        service = MetricGenerationService.__new__(MetricGenerationService)
        service.db = mock_db
        service.redis = None
        service._client = AsyncMock()
        service.embedding_service = AsyncMock()
        service._prompts = {"system_prompt": "test"}
        return service

    @pytest.mark.asyncio
    async def test_unknown_label_with_semantic_match(self, service):
        """unknown_label that semantically matches should add synonym."""
        # Mock: get_existing_metrics and get_existing_synonyms
        service.get_existing_metrics = AsyncMock(return_value=[])
        service.get_existing_synonyms = AsyncMock(return_value=[])

        # Mock: semantic match returns a match
        matched_metric = MagicMock()
        matched_metric.id = uuid.uuid4()
        matched_metric.code = "test_metric"
        service.match_metric_semantic = AsyncMock(return_value=(matched_metric, 0.85))
        service._add_synonym_if_new = AsyncMock(return_value=True)

        unmatched = [
            {"label": "Test Label", "value": "5.0", "error_type": "unknown_label"},
        ]

        result = await service.process_unmatched_metrics("task-1", unmatched)

        assert result["metrics_matched"] == 1
        assert result["synonyms_added"] == 1
        assert result["metrics_created"] == 0
        service._add_synonym_if_new.assert_called_once_with(matched_metric.id, "Test Label")

    @pytest.mark.asyncio
    async def test_unknown_label_no_match_creates_pending(self, service):
        """unknown_label without match should create PENDING MetricDef."""
        service.get_existing_metrics = AsyncMock(return_value=[])
        service.get_existing_synonyms = AsyncMock(return_value=[])

        # No semantic match
        service.match_metric_semantic = AsyncMock(return_value=(None, 0.0))

        new_metric = MagicMock()
        new_metric.code = "test_label"
        service.get_or_create_pending_metric = AsyncMock(return_value=(new_metric, True))

        unmatched = [
            {"label": "Test Label", "value": "5.0", "error_type": "unknown_label"},
        ]

        result = await service.process_unmatched_metrics("task-1", unmatched)

        assert result["metrics_created"] == 1
        assert result["metrics_matched"] == 0
        service.get_or_create_pending_metric.assert_called_once()

    @pytest.mark.asyncio
    async def test_evidence_missing_creates_pending(self, service):
        """evidence_missing_value should create PENDING MetricDef."""
        service.get_existing_metrics = AsyncMock(return_value=[])
        service.get_existing_synonyms = AsyncMock(return_value=[])

        new_metric = MagicMock()
        new_metric.code = "test_label"
        service.get_or_create_pending_metric = AsyncMock(return_value=(new_metric, True))

        unmatched = [
            {
                "label": "Test Label",
                "value": "3.0",
                "error_type": "evidence_missing_value",
                "quotes": ["some quote"],
            },
        ]

        result = await service.process_unmatched_metrics("task-1", unmatched)

        assert result["metrics_created"] == 1
        # Verify the metric_data passed has the unverified description (in Russian)
        call_args = service.get_or_create_pending_metric.call_args
        metric_data = call_args[0][0]
        assert "Не подтверждено" in metric_data.description

    @pytest.mark.asyncio
    async def test_empty_unmatched_labels(self, service):
        """Empty input should return zeros."""
        service.get_existing_metrics = AsyncMock(return_value=[])
        service.get_existing_synonyms = AsyncMock(return_value=[])

        result = await service.process_unmatched_metrics("task-1", [])

        assert result["metrics_created"] == 0
        assert result["metrics_matched"] == 0

    @pytest.mark.asyncio
    async def test_no_generation_without_errors(self, service):
        """When there are no unmatched items, nothing should be processed."""
        service.get_existing_metrics = AsyncMock(return_value=[])
        service.get_existing_synonyms = AsyncMock(return_value=[])

        result = await service.process_unmatched_metrics("task-1", [])
        assert result["metrics_created"] == 0
        assert result["metrics_matched"] == 0
        assert len(result["errors"]) == 0


@pytest.mark.unit
class TestExtractionTrigger:
    """Test that extraction triggers generation for unmatched metrics."""

    def test_build_extract_warning_with_unknowns(self):
        """_build_extract_warning should produce warning for unknown labels."""
        from app.tasks.extraction import _build_extract_warning

        msg, details = _build_extract_warning(
            unknown_labels=["Управленческий опыт", "Актуальный потенциал"],
            ambiguous=[],
        )

        assert msg is not None
        assert details is not None
        assert details["unknown_count"] == 2
        assert "Управленческий опыт" in details["unknown_labels"]

    def test_build_extract_warning_no_issues(self):
        """No issues should return None."""
        from app.tasks.extraction import _build_extract_warning

        msg, details = _build_extract_warning(
            unknown_labels=[],
            ambiguous=[],
        )

        assert msg is None
        assert details is None


# ==================== Regression: LogRecord 'created' collision ====================


@pytest.mark.unit
class TestLogRecordCreatedCollision:
    """Regression test: logging with extra fields must not collide with LogRecord attributes.

    Python's logging.LogRecord has a reserved 'created' attribute (timestamp).
    Using extra={"created": ...} raises KeyError. This test verifies that
    process_unmatched_metrics uses safe key names.
    """

    @pytest_asyncio.fixture
    async def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest_asyncio.fixture
    async def service(self, mock_db):
        from app.services.metric_generation import MetricGenerationService

        service = MetricGenerationService.__new__(MetricGenerationService)
        service.db = mock_db
        service.redis = None
        service._client = AsyncMock()
        service.embedding_service = AsyncMock()
        service._prompts = {"system_prompt": "test"}
        return service

    @pytest.mark.asyncio
    async def test_no_logrecord_collision_on_unknown_label(self, service):
        """process_unmatched_metrics must not crash on logging for unknown_label."""
        service.get_existing_metrics = AsyncMock(return_value=[])
        service.get_existing_synonyms = AsyncMock(return_value=[])

        new_metric = MagicMock()
        new_metric.code = "test_label"
        service.match_metric_semantic = AsyncMock(return_value=(None, 0.0))
        service.get_or_create_pending_metric = AsyncMock(return_value=(new_metric, True))

        unmatched = [
            {"label": "Test Label", "value": "5.0", "error_type": "unknown_label"},
        ]

        # This must not raise KeyError: "Attempt to overwrite 'created' in LogRecord"
        result = await service.process_unmatched_metrics("task-1", unmatched)
        assert len(result["errors"]) == 0
        assert result["metrics_created"] == 1

    @pytest.mark.asyncio
    async def test_no_logrecord_collision_on_evidence_missing(self, service):
        """process_unmatched_metrics must not crash on logging for evidence_missing_value."""
        service.get_existing_metrics = AsyncMock(return_value=[])
        service.get_existing_synonyms = AsyncMock(return_value=[])

        new_metric = MagicMock()
        new_metric.code = "test_label"
        service.get_or_create_pending_metric = AsyncMock(return_value=(new_metric, True))

        unmatched = [
            {"label": "Test Label", "value": "3.0", "error_type": "evidence_missing_value"},
        ]

        # This must not raise KeyError: "Attempt to overwrite 'created' in LogRecord"
        result = await service.process_unmatched_metrics("task-1", unmatched)
        assert len(result["errors"]) == 0
        assert result["metrics_created"] == 1

    @pytest.mark.asyncio
    async def test_no_logrecord_collision_on_semantic_match(self, service):
        """process_unmatched_metrics must not crash on logging for semantic match."""
        service.get_existing_metrics = AsyncMock(return_value=[])
        service.get_existing_synonyms = AsyncMock(return_value=[])

        matched_metric = MagicMock()
        matched_metric.id = uuid.uuid4()
        matched_metric.code = "test_metric"
        service.match_metric_semantic = AsyncMock(return_value=(matched_metric, 0.85))
        service._add_synonym_if_new = AsyncMock(return_value=True)

        unmatched = [
            {"label": "Test Label", "value": "5.0", "error_type": "unknown_label"},
        ]

        # This must not raise KeyError: "Attempt to overwrite 'created' in LogRecord"
        result = await service.process_unmatched_metrics("task-1", unmatched)
        assert len(result["errors"]) == 0
        assert result["metrics_matched"] == 1


# ==================== Exact match bypass in process_unmatched_metrics ====================


@pytest.mark.unit
class TestProcessUnmatchedExactMatch:
    """Test that process_unmatched_metrics tries exact name/synonym match before semantic/creation."""

    @pytest_asyncio.fixture
    async def mock_db(self):
        db = AsyncMock(spec=AsyncSession)
        db.commit = AsyncMock()
        db.rollback = AsyncMock()
        return db

    @pytest_asyncio.fixture
    async def service(self, mock_db):
        from app.services.metric_generation import MetricGenerationService

        service = MetricGenerationService.__new__(MetricGenerationService)
        service.db = mock_db
        service.redis = None
        service._client = AsyncMock()
        service.embedding_service = AsyncMock()
        service._prompts = {"system_prompt": "test"}
        return service

    @pytest.mark.asyncio
    async def test_unknown_label_exact_name_match_skips_semantic(self, service):
        """When label exactly matches an existing metric name, skip semantic search."""
        existing_metric = MagicMock()
        existing_metric.id = uuid.uuid4()
        existing_metric.code = "svyazi"
        existing_metric.name = "СВЯЗИ"

        service.get_existing_metrics = AsyncMock(return_value=[
            {"name": "СВЯЗИ", "name_ru": "СВЯЗИ", "code": "svyazi"},
        ])
        service.get_existing_synonyms = AsyncMock(return_value=[])
        service.match_existing_metric = AsyncMock(return_value=existing_metric)
        service._add_synonym_if_new = AsyncMock(return_value=False)
        service.match_metric_semantic = AsyncMock()  # Should NOT be called

        unmatched = [
            {"label": "СВЯЗИ", "value": "7.0", "error_type": "unknown_label"},
        ]

        result = await service.process_unmatched_metrics("task-1", unmatched)

        assert result["metrics_matched"] == 1
        assert result["metrics_created"] == 0
        service.match_existing_metric.assert_called_once()
        service.match_metric_semantic.assert_not_called()

    @pytest.mark.asyncio
    async def test_evidence_missing_exact_match_skips_creation(self, service):
        """When evidence_missing label exactly matches, skip PENDING creation."""
        existing_metric = MagicMock()
        existing_metric.id = uuid.uuid4()
        existing_metric.code = "rukovodstvo"
        existing_metric.name = "РУКОВОДСТВО"

        service.get_existing_metrics = AsyncMock(return_value=[
            {"name": "РУКОВОДСТВО", "name_ru": "РУКОВОДСТВО", "code": "rukovodstvo"},
        ])
        service.get_existing_synonyms = AsyncMock(return_value=[])
        service.match_existing_metric = AsyncMock(return_value=existing_metric)
        service._add_synonym_if_new = AsyncMock(return_value=False)
        service.get_or_create_pending_metric = AsyncMock()  # Should NOT be called

        unmatched = [
            {
                "label": "РУКОВОДСТВО",
                "value": "5.0",
                "error_type": "evidence_missing_value",
                "quotes": ["some quote"],
            },
        ]

        result = await service.process_unmatched_metrics("task-1", unmatched)

        assert result["metrics_matched"] == 1
        assert result["metrics_created"] == 0
        service.match_existing_metric.assert_called_once()
        service.get_or_create_pending_metric.assert_not_called()

    @pytest.mark.asyncio
    async def test_no_exact_match_falls_through_to_semantic(self, service):
        """When no exact match, semantic search should still work as before."""
        service.get_existing_metrics = AsyncMock(return_value=[
            {"name": "СВЯЗИ", "name_ru": "СВЯЗИ", "code": "svyazi"},
        ])
        service.get_existing_synonyms = AsyncMock(return_value=[])
        service.match_existing_metric = AsyncMock(return_value=None)

        matched_metric = MagicMock()
        matched_metric.id = uuid.uuid4()
        matched_metric.code = "svyazi"
        service.match_metric_semantic = AsyncMock(return_value=(matched_metric, 0.88))
        service._add_synonym_if_new = AsyncMock(return_value=True)

        unmatched = [
            {"label": "Связи и отношения", "value": "6.0", "error_type": "unknown_label"},
        ]

        result = await service.process_unmatched_metrics("task-1", unmatched)

        assert result["metrics_matched"] == 1
        assert result["synonyms_added"] == 1
        service.match_existing_metric.assert_called_once()
        service.match_metric_semantic.assert_called_once()

    @pytest.mark.asyncio
    async def test_synonym_added_on_exact_match(self, service):
        """When exact match found, label should be added as synonym."""
        existing_metric = MagicMock()
        existing_metric.id = uuid.uuid4()
        existing_metric.code = "dengi"
        existing_metric.name = "ДЕНЬГИ"

        service.get_existing_metrics = AsyncMock(return_value=[
            {"name": "ДЕНЬГИ", "name_ru": "ДЕНЬГИ", "code": "dengi"},
        ])
        service.get_existing_synonyms = AsyncMock(return_value=[])
        service.match_existing_metric = AsyncMock(return_value=existing_metric)
        service._add_synonym_if_new = AsyncMock(return_value=True)

        unmatched = [
            {"label": "деньги", "value": "4.0", "error_type": "unknown_label"},
        ]

        result = await service.process_unmatched_metrics("task-1", unmatched)

        assert result["metrics_matched"] == 1
        assert result["synonyms_added"] == 1
        service._add_synonym_if_new.assert_called_once_with(existing_metric.id, "деньги")
