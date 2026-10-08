# FlutterChatBot Project Spec

## Goal
Build a multimodal personal knowledge chatbot using Flutter + FastAPI + Supabase.

## Future inputs
TXT, PDF, DOCX, CSV, XLS/XLSX, standalone images, audio and video.

PDF/DOCX/Excel ingestion must understand useful embedded content, not text only: tables, images, screenshots, charts, graphs and diagrams must remain linked to their document/page/sheet context.

## Core architecture
- Flutter client
- FastAPI AI/backend service
- Supabase for Auth, Database, Storage, Realtime and vector search
- No separate PostgreSQL server, MySQL, Firebase, Qdrant or Pinecone by default

## Retrieval roadmap
Hybrid chunking -> embeddings -> vector + keyword retrieval -> fusion -> reranking -> Hybrid RAG.

Default answer mode is Knowledge Only. If retrieved knowledge is insufficient, the assistant must say so rather than inventing an answer.

Every answer should preserve source citations. All user data and retrieval must be strictly isolated per authenticated user.

## 20 phases
1. Project Bootstrap & Architecture
2. Supabase Connection + Authentication
3. Supabase Tables + RLS + Storage Security
4. Upload Manager + Processing Jobs
5. TXT/Text Ingestion
6. PDF Multimodal Ingestion
7. DOCX Multimodal Ingestion
8. CSV + Excel Multimodal Ingestion
9. Standalone Image OCR + Vision
10. Audio Transcription + Timestamp Knowledge
11. Video Multimodal Processing
12. Hybrid Chunking Engine
13. Embeddings + Supabase Vector Index
14. Keyword / Full-Text Search
15. Hybrid Search + Result Fusion
16. Query Understanding + Reranking
17. Hybrid RAG + Knowledge-Only Answers + Citations
18. Flutter Knowledge Library + Chat UX
19. Security + Testing + Monitoring + Performance
20. Production Deployment + Scaling + Hardening

Current phase: 3.
