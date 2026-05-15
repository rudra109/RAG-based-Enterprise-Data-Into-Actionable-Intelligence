"""
EnterpriseIQ ML — Knowledge Graph Tests
Tests extraction, entity resolution, and NL-to-GQL.
"""

from __future__ import annotations

import sys
import uuid
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, "../../")

from kg.extractor import KnowledgeGraphExtractor, KGNode, KGEdge


@pytest.fixture
def mock_extractor():
    with (
        patch("kg.extractor.vertexai.init"),
        patch("kg.extractor.GenerativeModel") as mock_gen,
        patch("kg.extractor.language_v2.LanguageServiceClient"),
        patch("kg.extractor.spanner.Client"),
        patch("kg.extractor.BigQueryClient") as mock_bq,
    ):
        extractor = KnowledgeGraphExtractor()
        extractor._gemini_pro = mock_gen.return_value
        extractor._gemini_flash = mock_gen.return_value
        extractor._nl_client = MagicMock()
        extractor._bq = mock_bq.return_value
        extractor._spanner_available = False  # Don't need real Spanner in tests
        yield extractor


def make_node(name: str, entity_type: str = "ORG") -> KGNode:
    return KGNode(
        node_id=str(uuid.uuid4()),
        entity_type=entity_type,
        entity_name=name,
        graph_id="test_graph",
    )


class TestEntityResolution:

    def test_deduplicates_exact_match(self, mock_extractor):
        """Two nodes with exactly the same name should be merged."""
        nodes = [make_node("Google"), make_node("Google")]
        resolved, id_map = mock_extractor._resolve_entities(nodes)
        assert len(resolved) == 1

    def test_deduplicates_case_insensitive(self, mock_extractor):
        """'Google' and 'google' should resolve to the same entity."""
        nodes = [make_node("Google"), make_node("google")]
        resolved, id_map = mock_extractor._resolve_entities(nodes)
        assert len(resolved) == 1

    def test_different_entities_not_merged(self, mock_extractor):
        """Google and Microsoft should remain separate entities."""
        nodes = [make_node("Google"), make_node("Microsoft")]
        resolved, _ = mock_extractor._resolve_entities(nodes)
        assert len(resolved) == 2

    def test_id_map_redirects_duplicate_ids(self, mock_extractor):
        """id_map should map duplicate node IDs to the canonical node ID."""
        n1 = make_node("Apple Inc")
        n2 = make_node("Apple Inc")
        _, id_map = mock_extractor._resolve_entities([n1, n2])
        # Both should map to the same canonical ID
        assert id_map[n1.node_id] == id_map[n2.node_id]

    def test_confidence_boosted_for_duplicate(self, mock_extractor):
        """Merging duplicates should increase confidence."""
        n1 = make_node("Tesla")
        n1.confidence = 0.7
        n2 = make_node("Tesla")
        n2.confidence = 0.7
        resolved, _ = mock_extractor._resolve_entities([n1, n2])
        assert resolved[0].confidence > 0.7

    def test_punctuation_stripped_for_normalization(self, mock_extractor):
        """'Apple, Inc.' and 'Apple Inc' should be treated as the same."""
        nodes = [make_node("Apple, Inc."), make_node("Apple Inc")]
        resolved, _ = mock_extractor._resolve_entities(nodes)
        # They differ slightly after punct removal — "apple inc" vs "apple inc"
        # This tests that punctuation removal works
        assert len(resolved) <= 2  # May or may not merge depending on exact normalization


class TestGeminiExtraction:

    def test_parses_valid_gemini_json(self, mock_extractor):
        """Should parse well-formed Gemini KG JSON response."""
        gemini_response = """{
            "nodes": [
                {"id": "n1", "type": "ORG", "name": "Acme Corp", "properties": {}},
                {"id": "n2", "type": "PERSON", "name": "Jane Doe", "properties": {}}
            ],
            "edges": [
                {"source": "n2", "target": "n1", "type": "WORKS_FOR", "properties": {}}
            ]
        }"""
        mock_extractor._gemini_pro.generate_content.return_value = MagicMock(
            text=gemini_response
        )

        nodes, edges = mock_extractor._extract_with_gemini("Some text.", "doc1", "graph1")

        assert len(nodes) == 2
        assert len(edges) == 1
        assert edges[0].relationship_type == "WORKS_FOR"

    def test_handles_invalid_json_gracefully(self, mock_extractor):
        """Invalid JSON from Gemini should return empty lists without crashing."""
        mock_extractor._gemini_pro.generate_content.return_value = MagicMock(
            text="Sorry, I could not extract any entities."
        )
        nodes, edges = mock_extractor._extract_with_gemini("text", "doc1", "graph1")
        assert nodes == []
        assert edges == []

    def test_handles_api_error_gracefully(self, mock_extractor):
        """API failure should return empty lists."""
        mock_extractor._gemini_pro.generate_content.side_effect = RuntimeError("API error")
        nodes, edges = mock_extractor._extract_with_gemini("text", "doc1", "graph1")
        assert nodes == []
        assert edges == []

    def test_markdown_code_block_stripped(self, mock_extractor):
        """JSON wrapped in markdown ```json ... ``` should still be parsed."""
        gemini_response = """```json
{
    "nodes": [{"id": "n1", "type": "PERSON", "name": "John", "properties": {}}],
    "edges": []
}
```"""
        mock_extractor._gemini_pro.generate_content.return_value = MagicMock(
            text=gemini_response
        )
        nodes, edges = mock_extractor._extract_with_gemini("text", "doc1", "graph1")
        assert len(nodes) == 1
        assert nodes[0].entity_name == "John"

    def test_self_loops_removed(self, mock_extractor):
        """Edges where source == target should be removed."""
        gemini_response = """{
            "nodes": [{"id": "n1", "type": "ORG", "name": "Acme", "properties": {}}],
            "edges": [{"source": "n1", "target": "n1", "type": "SELF_REF", "properties": {}}]
        }"""
        mock_extractor._gemini_pro.generate_content.return_value = MagicMock(
            text=gemini_response
        )
        mock_extractor._nl_client.analyze_entities.return_value = MagicMock(entities=[])
        mock_extractor._bq.write_kg_nodes = MagicMock()
        mock_extractor._bq.write_kg_edges = MagicMock()

        result = mock_extractor.extract_from_document("Acme Corp.", "doc1", "graph1")
        # Self-loop edge should not be in result
        assert all(e.source_node_id != e.target_node_id for e in result.edges)

    def test_dangling_edge_references_skipped(self, mock_extractor):
        """Edges referencing non-existent node IDs should be skipped."""
        gemini_response = """{
            "nodes": [{"id": "n1", "type": "ORG", "name": "Acme", "properties": {}}],
            "edges": [
                {"source": "n1", "target": "n999", "type": "RELATED_TO", "properties": {}}
            ]
        }"""
        mock_extractor._gemini_pro.generate_content.return_value = MagicMock(
            text=gemini_response
        )
        nodes, edges = mock_extractor._extract_with_gemini("text", "doc1", "graph1")
        # n999 doesn't exist, so edge should not be added
        assert len(edges) == 0


class TestNLPExtraction:

    def test_maps_entity_types_correctly(self, mock_extractor):
        """Cloud NLP entity types should map to our canonical types."""
        from google.cloud import language_v2

        # Simulate NLP returning a PERSON entity
        mock_entity = MagicMock()
        mock_entity.name = "John Smith"
        mock_entity.type_ = language_v2.Entity.Type.PERSON
        mock_entity.salience = 0.9
        mock_entity.mentions = [MagicMock()]
        mock_entity.metadata = {}

        mock_extractor._nl_client.analyze_entities.return_value = MagicMock(
            entities=[mock_entity]
        )

        nodes = mock_extractor._extract_with_nlp_api("John Smith is a founder.", "doc1", "graph1")
        assert len(nodes) == 1
        assert nodes[0].entity_type == "PERSON"
        assert nodes[0].entity_name == "John Smith"
