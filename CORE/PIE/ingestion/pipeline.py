"""
PROGRAMMING INTELLIGENCE ENGINE - Ingestion Pipeline

Build a structured ingestion system:
Parse → Classify → Authority Score → Version Tag → Graph Link → Doctrine Create

Reject raw dumps.
Normalize everything.

System Class: ISOLATED_REASONING_ENGINE
Governance Tier: ZERO
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Generator, Tuple
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
import hashlib
import json
import re
import mimetypes
from loguru import logger

from ..engine.models import (
    EngineeringDoctrine,
    SourceReference,
    VersionMetadata,
    IngestionRecord,
    AuthorityTier,
    TrustLevel,
    ConfidenceTier,
    GraphNode
)
from ..layers.authority_hierarchy import AuthorityHierarchyEngine, AuthorityClassification
from ..layers.version_awareness import VersionAwarenessEngine
from ..layers.semantic_graph import SemanticEngineeringGraph, NodeType


class DocumentType(str, Enum):
    """Supported document types for ingestion."""
    MARKDOWN = "MARKDOWN"
    JSON = "JSON"
    HTML = "HTML"
    TEXT = "TEXT"
    YAML = "YAML"
    RST = "RST"  # ReStructuredText
    API_SPEC = "API_SPEC"  # OpenAPI, etc.


@dataclass
class ParsedDocument:
    """Result of document parsing."""
    doc_id: str
    title: str
    content: str
    doc_type: DocumentType
    sections: List[Dict[str, Any]]
    metadata: Dict[str, Any]
    source_path: str
    content_hash: str


@dataclass
class IngestionConfig:
    """Configuration for document ingestion."""
    source_path: Path
    vendor: Optional[str] = None
    category: Optional[str] = None
    tags: List[str] = field(default_factory=list)
    authority_override: Optional[AuthorityTier] = None
    version: Optional[str] = None
    recursive: bool = True
    file_patterns: List[str] = field(default_factory=lambda: ["*.md", "*.json", "*.html", "*.txt"])


class IngestionPipeline:
    """
    Structured Document Ingestion Pipeline

    Stages:
    1. PARSE - Extract structure from documents
    2. CLASSIFY - Determine authority and trust
    3. AUTHORITY_SCORE - Compute authority weight
    4. VERSION_TAG - Extract version metadata
    5. GRAPH_LINK - Connect to semantic graph
    6. DOCTRINE_CREATE - Create final doctrine

    Reject raw dumps. Normalize everything.
    """

    def __init__(
        self,
        authority_engine: AuthorityHierarchyEngine,
        version_engine: VersionAwarenessEngine,
        semantic_graph: SemanticEngineeringGraph
    ):
        self.authority = authority_engine
        self.versions = version_engine
        self.graph = semantic_graph

        self.records: List[IngestionRecord] = []
        self.failed_documents: List[Dict[str, Any]] = []

        logger.info("Ingestion Pipeline initialized")

    def ingest(self, config: IngestionConfig) -> List[EngineeringDoctrine]:
        """
        Run full ingestion pipeline on a source.

        Parse → Classify → Authority Score → Version Tag → Graph Link → Doctrine Create
        """
        logger.info(f"Starting ingestion: {config.source_path}")
        start_time = datetime.now()

        doctrines = []
        record = IngestionRecord(
            record_id=hashlib.sha256(str(config.source_path).encode()).hexdigest()[:16],
            source_path=str(config.source_path),
            source_type="directory" if config.source_path.is_dir() else "file"
        )

        try:
            # Stage 1: PARSE
            documents = list(self._parse_source(config))
            logger.info(f"Parsed {len(documents)} documents")

            for doc in documents:
                try:
                    # Stage 2: CLASSIFY
                    classification = self._classify_document(doc, config)

                    # Stage 3: AUTHORITY_SCORE
                    source_ref = self._create_source_reference(doc, classification, config)

                    # Stage 4: VERSION_TAG
                    version_meta = self._extract_version_metadata(doc, config)

                    # Stage 5: GRAPH_LINK
                    graph_nodes = self._link_to_graph(doc, classification)

                    # Stage 6: DOCTRINE_CREATE
                    doctrine = self._create_doctrine(
                        doc, source_ref, version_meta, graph_nodes, config
                    )

                    doctrines.append(doctrine)
                    record.doctrines_created += 1
                    record.graph_nodes_created += len(graph_nodes)

                except Exception as e:
                    logger.warning(f"Failed to process {doc.doc_id}: {e}")
                    self.failed_documents.append({
                        "doc_id": doc.doc_id,
                        "error": str(e),
                        "path": doc.source_path
                    })

            record.validation_passed = True

        except Exception as e:
            record.validation_passed = False
            record.validation_errors.append(str(e))
            logger.error(f"Ingestion failed: {e}")

        self.records.append(record)

        duration = (datetime.now() - start_time).total_seconds()
        logger.info(
            f"Ingestion complete: {len(doctrines)} doctrines | "
            f"Duration: {duration:.2f}s"
        )

        return doctrines

    def _parse_source(
        self,
        config: IngestionConfig
    ) -> Generator[ParsedDocument, None, None]:
        """Stage 1: PARSE - Extract structure from documents."""
        source = config.source_path

        if source.is_file():
            doc = self._parse_file(source)
            if doc:
                yield doc
        elif source.is_dir():
            for pattern in config.file_patterns:
                glob_pattern = f"**/{pattern}" if config.recursive else pattern
                for file_path in source.glob(glob_pattern):
                    if file_path.is_file():
                        doc = self._parse_file(file_path)
                        if doc:
                            yield doc

    def _parse_file(self, file_path: Path) -> Optional[ParsedDocument]:
        """Parse a single file."""
        try:
            content = file_path.read_text(encoding='utf-8', errors='ignore')
            doc_type = self._detect_document_type(file_path)

            # Parse based on type
            if doc_type == DocumentType.MARKDOWN:
                title, sections = self._parse_markdown(content)
            elif doc_type == DocumentType.JSON:
                title, sections = self._parse_json(content)
            elif doc_type == DocumentType.HTML:
                title, sections = self._parse_html(content)
            else:
                title = file_path.stem
                sections = [{"type": "text", "content": content}]

            # Extract metadata from frontmatter or comments
            metadata = self._extract_metadata(content, doc_type)

            return ParsedDocument(
                doc_id=hashlib.sha256(str(file_path).encode()).hexdigest()[:16],
                title=title or file_path.stem,
                content=content,
                doc_type=doc_type,
                sections=sections,
                metadata=metadata,
                source_path=str(file_path),
                content_hash=hashlib.sha256(content.encode()).hexdigest()
            )

        except Exception as e:
            logger.warning(f"Failed to parse {file_path}: {e}")
            return None

    def _detect_document_type(self, file_path: Path) -> DocumentType:
        """Detect document type from extension."""
        suffix = file_path.suffix.lower()
        type_map = {
            ".md": DocumentType.MARKDOWN,
            ".markdown": DocumentType.MARKDOWN,
            ".json": DocumentType.JSON,
            ".html": DocumentType.HTML,
            ".htm": DocumentType.HTML,
            ".txt": DocumentType.TEXT,
            ".yaml": DocumentType.YAML,
            ".yml": DocumentType.YAML,
            ".rst": DocumentType.RST
        }
        return type_map.get(suffix, DocumentType.TEXT)

    def _parse_markdown(self, content: str) -> Tuple[str, List[Dict]]:
        """Parse markdown document."""
        sections = []
        title = None

        # Extract title from first H1
        title_match = re.search(r'^#\s+(.+)$', content, re.MULTILINE)
        if title_match:
            title = title_match.group(1).strip()

        # Split by headers
        header_pattern = r'^(#{1,6})\s+(.+)$'
        current_section = {"type": "preamble", "content": ""}
        current_level = 0

        for line in content.split('\n'):
            header_match = re.match(header_pattern, line)
            if header_match:
                if current_section["content"].strip():
                    sections.append(current_section)

                level = len(header_match.group(1))
                header_text = header_match.group(2).strip()
                current_section = {
                    "type": f"h{level}",
                    "title": header_text,
                    "level": level,
                    "content": ""
                }
                current_level = level
            else:
                current_section["content"] += line + "\n"

        if current_section["content"].strip():
            sections.append(current_section)

        return title, sections

    def _parse_json(self, content: str) -> Tuple[str, List[Dict]]:
        """Parse JSON document."""
        try:
            data = json.loads(content)
            title = data.get("title") or data.get("name") or "Untitled"

            sections = []
            if isinstance(data, dict):
                for key, value in data.items():
                    sections.append({
                        "type": "json_field",
                        "key": key,
                        "content": json.dumps(value) if isinstance(value, (dict, list)) else str(value)
                    })
            elif isinstance(data, list):
                for i, item in enumerate(data):
                    sections.append({
                        "type": "json_array_item",
                        "index": i,
                        "content": json.dumps(item)
                    })

            return title, sections

        except json.JSONDecodeError:
            return "Invalid JSON", [{"type": "error", "content": content}]

    def _parse_html(self, content: str) -> Tuple[str, List[Dict]]:
        """Parse HTML document."""
        # Simple HTML parsing without external dependencies
        title_match = re.search(r'<title>([^<]+)</title>', content, re.IGNORECASE)
        title = title_match.group(1) if title_match else "Untitled"

        # Extract text content
        text = re.sub(r'<script[^>]*>.*?</script>', '', content, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<style[^>]*>.*?</style>', '', text, flags=re.DOTALL | re.IGNORECASE)
        text = re.sub(r'<[^>]+>', '\n', text)
        text = re.sub(r'\n+', '\n', text)

        sections = [{"type": "html_text", "content": text.strip()}]
        return title, sections

    def _extract_metadata(self, content: str, doc_type: DocumentType) -> Dict[str, Any]:
        """Extract metadata from document."""
        metadata = {}

        # YAML frontmatter (common in markdown)
        frontmatter_match = re.match(r'^---\s*\n(.+?)\n---', content, re.DOTALL)
        if frontmatter_match:
            try:
                import yaml
                metadata = yaml.safe_load(frontmatter_match.group(1)) or {}
            except:
                pass

        # Look for version info
        version_match = re.search(r'version[:\s]*v?([\d.]+)', content, re.IGNORECASE)
        if version_match:
            metadata["version"] = version_match.group(1)

        return metadata

    def _classify_document(
        self,
        doc: ParsedDocument,
        config: IngestionConfig
    ) -> AuthorityClassification:
        """Stage 2: CLASSIFY - Determine authority and trust."""
        return self.authority.classify_source(
            source_path=doc.source_path,
            content=doc.content,
            metadata={
                "vendor": config.vendor,
                **doc.metadata
            }
        )

    def _create_source_reference(
        self,
        doc: ParsedDocument,
        classification: AuthorityClassification,
        config: IngestionConfig
    ) -> SourceReference:
        """Stage 3: AUTHORITY_SCORE - Create scored source reference."""
        tier = config.authority_override or classification.tier

        return SourceReference(
            source_id=doc.doc_id,
            source_type=classification.source_type,
            authority_tier=tier,
            trust_level=classification.trust_level,
            file_path=Path(doc.source_path),
            content_hash=doc.content_hash,
            vendor=classification.vendor or config.vendor,
            last_accessed=datetime.now()
        )

    def _extract_version_metadata(
        self,
        doc: ParsedDocument,
        config: IngestionConfig
    ) -> VersionMetadata:
        """Stage 4: VERSION_TAG - Extract version metadata."""
        meta = self.versions.extract_version_metadata(
            doc.content,
            source_metadata={
                "version": config.version,
                **doc.metadata
            }
        )
        return meta

    def _link_to_graph(
        self,
        doc: ParsedDocument,
        classification: AuthorityClassification
    ) -> List[str]:
        """Stage 5: GRAPH_LINK - Connect to semantic graph."""
        node_ids = []

        # Create a node for this document
        doc_node = GraphNode(
            node_id=f"doc_{doc.doc_id}",
            node_type=self._infer_node_type(doc, classification),
            name=doc.title,
            version=doc.metadata.get("version"),
            metadata={
                "source_path": doc.source_path,
                "vendor": classification.vendor
            }
        )
        self.graph.add_node(doc_node)
        node_ids.append(doc_node.node_id)

        # Extract and link referenced concepts
        references = self._extract_references(doc.content)
        for ref_name, ref_type in references:
            ref_node_id = f"{ref_type}_{hashlib.sha256(ref_name.encode()).hexdigest()[:8]}"

            # Create or get existing node
            existing = self.graph.get_node(ref_node_id)
            if not existing:
                ref_node = GraphNode(
                    node_id=ref_node_id,
                    node_type=ref_type,
                    name=ref_name
                )
                self.graph.add_node(ref_node)

            # Link document to reference
            try:
                self.graph.add_edge(
                    doc_node.node_id,
                    ref_node_id,
                    relationship="REFERENCES"
                )
            except ValueError:
                pass  # Edge might already exist

            node_ids.append(ref_node_id)

        return node_ids

    def _infer_node_type(
        self,
        doc: ParsedDocument,
        classification: AuthorityClassification
    ) -> str:
        """Infer the node type from document content."""
        content_lower = doc.content.lower()
        title_lower = doc.title.lower()

        if any(k in content_lower for k in ["api", "endpoint", "rest", "graphql"]):
            return NodeType.API
        if any(k in content_lower for k in ["sdk", "library", "package"]):
            return NodeType.SDK
        if any(k in content_lower for k in ["oauth", "authentication", "auth", "jwt"]):
            return NodeType.AUTH_MODEL
        if any(k in content_lower for k in ["docker", "kubernetes", "terraform", "infrastructure"]):
            return NodeType.INFRASTRUCTURE
        if any(k in content_lower for k in ["framework", "react", "angular", "vue"]):
            return NodeType.FRAMEWORK

        return "DOCUMENTATION"

    def _extract_references(self, content: str) -> List[Tuple[str, str]]:
        """Extract referenced concepts from content."""
        references = []

        # Extract API/package references
        api_patterns = [
            (r'\b([A-Z][a-z]+(?:[A-Z][a-z]+)+)\b', NodeType.API),  # CamelCase
            (r'\b([a-z]+[-_][a-z]+(?:[-_][a-z]+)*)\b', NodeType.LIBRARY),  # kebab-case/snake_case
            (r'`([^`]+)`', "CODE"),  # Inline code
        ]

        for pattern, ref_type in api_patterns:
            matches = re.findall(pattern, content)
            for match in matches[:10]:  # Limit to prevent explosion
                if len(match) > 3:  # Skip short matches
                    references.append((match, ref_type))

        return references

    def _create_doctrine(
        self,
        doc: ParsedDocument,
        source_ref: SourceReference,
        version_meta: VersionMetadata,
        graph_nodes: List[str],
        config: IngestionConfig
    ) -> EngineeringDoctrine:
        """Stage 6: DOCTRINE_CREATE - Create final doctrine."""
        doctrine = EngineeringDoctrine(
            doctrine_id=f"doctrine_{doc.doc_id}",
            title=doc.title,
            content=doc.content,
            category=config.category or self._infer_category(doc),
            source_references=[source_ref],
            version_metadata=version_meta,
            related_nodes=graph_nodes,
            tags=config.tags + self._extract_tags(doc),
            confidence_tier=self._determine_confidence(source_ref, version_meta)
        )

        # Compute determinism hash
        doctrine.compute_determinism_hash()

        return doctrine

    def _infer_category(self, doc: ParsedDocument) -> str:
        """Infer category from document."""
        content_lower = doc.content.lower()

        if "api" in content_lower:
            return "API"
        if "security" in content_lower or "auth" in content_lower:
            return "SECURITY"
        if "tutorial" in content_lower or "guide" in content_lower:
            return "TUTORIAL"
        if "reference" in content_lower:
            return "REFERENCE"
        if "example" in content_lower:
            return "EXAMPLES"

        return "DOCUMENTATION"

    def _extract_tags(self, doc: ParsedDocument) -> List[str]:
        """Extract tags from document."""
        tags = []

        # From metadata
        if "tags" in doc.metadata:
            tags.extend(doc.metadata["tags"])

        # From hashtags in content
        hashtags = re.findall(r'#(\w+)', doc.content)
        tags.extend(hashtags[:10])

        return list(set(tags))

    def _determine_confidence(
        self,
        source_ref: SourceReference,
        version_meta: VersionMetadata
    ) -> ConfidenceTier:
        """Determine confidence tier for doctrine."""
        # High authority + verified version = deterministic
        if source_ref.authority_tier.value >= 80 and version_meta.last_verified:
            return ConfidenceTier.DETERMINISTIC

        if source_ref.authority_tier.value >= 60:
            return ConfidenceTier.HIGH_CONFIDENCE

        if source_ref.authority_tier.value >= 40:
            return ConfidenceTier.MODERATE

        return ConfidenceTier.LOW_CONFIDENCE

    def get_statistics(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "total_records": len(self.records),
            "total_doctrines_created": sum(r.doctrines_created for r in self.records),
            "total_graph_nodes_created": sum(r.graph_nodes_created for r in self.records),
            "failed_documents": len(self.failed_documents),
            "records": [
                {
                    "record_id": r.record_id,
                    "source": r.source_path,
                    "doctrines": r.doctrines_created,
                    "passed": r.validation_passed
                }
                for r in self.records
            ]
        }
