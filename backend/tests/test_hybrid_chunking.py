from app.services.chunking import ChunkDraft, ChunkingBlock, ChunkingDocument, ChunkingPolicy, HybridChunkingEngine


def plan(drafts: list[ChunkDraft], **policy: int):
    engine = HybridChunkingEngine(ChunkingPolicy(**policy))
    return engine.plan(ChunkingDocument("source", [ChunkingBlock.from_draft(draft, index) for index, draft in enumerate(drafts)]))


def test_structural_chunks_create_parent_child_tree_with_heading_context() -> None:
    result = plan([
        ChunkDraft("A meaningful first paragraph about supply zones.", "docx_text", section_title="Supply and Demand"),
        ChunkDraft("A meaningful second paragraph about confirmations.", "docx_text", section_title="Supply and Demand"),
    ], min_tokens=1, target_tokens=20, max_tokens=30, overlap_tokens=3, parent_target_tokens=30, parent_max_tokens=50)
    parent = next(chunk for chunk in result.chunks if chunk.metadata["chunk_role"] == "parent")
    children = [chunk for chunk in result.chunks if chunk.metadata["chunk_role"] == "child"]
    assert len(children) == 2
    assert all(chunk.metadata["parent_chunk_index"] == 0 for chunk in children)
    assert parent.metadata["heading_path"] == ["Supply and Demand"]


def test_large_prose_never_exceeds_hard_token_limit() -> None:
    words = " ".join(f"word{number}" for number in range(31))
    result = plan([ChunkDraft(words, "text")], min_tokens=1, target_tokens=8, max_tokens=10,
                  overlap_tokens=2, parent_target_tokens=12, parent_max_tokens=20)
    assert all(chunk.metadata["token_count"] <= 20 for chunk in result.chunks)
    assert all(len(chunk.content.split()) <= 10 for chunk in result.chunks if chunk.metadata["chunk_role"] == "child")


def test_table_row_groups_repeat_header_and_have_no_overlap() -> None:
    table = "Table: Symbol | Entry\nRow 1: Symbol: EURUSD; Entry: 1.10\nRow 2: Symbol: GBPUSD; Entry: 1.20\nRow 3: Symbol: USDJPY; Entry: 150"
    result = plan([ChunkDraft(table, "pdf_table", page_number=2, metadata={"table_index": 1})], min_tokens=1,
                  target_tokens=10, max_tokens=12, overlap_tokens=3, parent_target_tokens=15, parent_max_tokens=20,
                  table_rows_per_group=1)
    assert len(result.chunks) == 3
    assert all(chunk.content.startswith("Table: Symbol | Entry") for chunk in result.chunks)
    assert all(chunk.metadata["overlap_tokens"] == 0 for chunk in result.chunks)
    assert all(chunk.page_number == 2 and chunk.metadata["table_index"] == 1 for chunk in result.chunks)


def test_duplicate_protection_respects_location() -> None:
    result = plan([ChunkDraft("Repeated caption", "pdf_image", page_number=1), ChunkDraft("Repeated caption", "pdf_image", page_number=2)],
                  min_tokens=1, target_tokens=10, max_tokens=20, overlap_tokens=0, parent_target_tokens=20, parent_max_tokens=30)
    assert len(result.chunks) == 2
    assert result.duplicates_skipped == 0


def test_visual_metadata_and_pdf_page_context_are_preserved() -> None:
    result = plan([ChunkDraft("See the diagram below.", "pdf_text", page_number=12, section_title="Workflow"),
                   ChunkDraft("Flow goes from weekly analysis to H4 confirmation.", "pdf_diagram", page_number=12,
                              section_title="Workflow", metadata={"asset_path": "u/s/diagram.png", "nearby_text": "See the diagram below."})],
                  min_tokens=1, target_tokens=20, max_tokens=30, overlap_tokens=0, parent_target_tokens=30, parent_max_tokens=40)
    visual = next(chunk for chunk in result.chunks if chunk.content_type == "pdf_diagram")
    assert visual.page_number == 12
    assert visual.metadata["asset_path"] == "u/s/diagram.png"
    assert visual.metadata["multimodal"] is True


def test_audio_and_video_timestamps_are_never_lost() -> None:
    result = plan([ChunkDraft("First explanation.", "audio_transcript", metadata={"start_time_ms": 1000, "end_time_ms": 5000}),
                   ChunkDraft("Chart is highlighted.", "video_multimodal", metadata={"start_time_ms": 6000, "end_time_ms": 9000, "asset_path": "u/s/frame.png"})],
                  min_tokens=1, target_tokens=20, max_tokens=30, overlap_tokens=0, parent_target_tokens=30, parent_max_tokens=40)
    assert {(chunk.metadata.get("start_time_ms"), chunk.metadata.get("end_time_ms")) for chunk in result.chunks} == {(1000, 5000), (6000, 9000)}


def test_empty_blocks_and_reprocessing_plan_are_deterministic() -> None:
    drafts = [ChunkDraft("", "text"), ChunkDraft("Useful content.", "text", metadata={"source_id": "source"})]
    first = plan(drafts, min_tokens=1, target_tokens=10, max_tokens=20, overlap_tokens=0, parent_target_tokens=20, parent_max_tokens=30)
    second = plan(drafts, min_tokens=1, target_tokens=10, max_tokens=20, overlap_tokens=0, parent_target_tokens=20, parent_max_tokens=30)
    assert [(chunk.content, chunk.metadata) for chunk in first.chunks] == [(chunk.content, chunk.metadata) for chunk in second.chunks]
