# Dynamic Waste Reduction Engine - Deployment TODO
Status: [3/7] Local test + GCP auth + File cleanup complete

## Plan Breakdown (Approved by User)

1. [x] **Local Test Verification** - Run main.py --test-tools & streamlit dashboard (DEMO_MODE)
2. [x] **Check/Install Prerequisites** - Docker, gcloud CLI, Git Bash (Windows)
3. [x] **File Cleanup** - Removed models/, architecture.html, temp SA JSON
4. [ ] **Run GCP Setup** - cd scripts && bash setup.sh (BigQuery, APIs, RAG, etc.)
5. [ ] **Deploy Cloud Run** - cd scripts && bash deploy.sh (build/push/deploy app.py)
6. [ ] **Deploy Agent Engine** - python agent_engine_deploy.py --project tcs-1770741130267
7. [ ] **End-to-End Test** - Access Cloud Run URL, test Agent Engine query, API endpoints
8. [ ] **Final Commands Summary** - Provide all ADK/gcloud commands for user reference

**Notes**: 
- Uses Cloud Run (not App Engine)
- Project: tcs-1770741130267 (fixed)
- Windows: Use Git Bash for bash scripts
- SA key removed (temp); scripts expect gcloud auth or GOOGLE_APPLICATION_CREDENTIALS env
- Structure optimized, tests pass
