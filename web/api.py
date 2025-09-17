"""
FastAPI web API for duplicate management interface.
"""

import os
from typing import Any, Dict, List, Optional
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel

from .models import db_manager, DuplicateCandidate, MatchConfidence, DuplicateStatus
from .services import DuplicateManagementService


# Pydantic models for API requests/responses
class UpdateRequest(BaseModel):
    update_data: Dict[str, Any]
    user_decision: Optional[str] = None


class RejectRequest(BaseModel):
    reason: Optional[str] = None


class FlagRequest(BaseModel):
    reason: Optional[str] = None


class DuplicateResponse(BaseModel):
    id: int
    linkedin_contact_data: Dict[str, Any]
    crm_contact_data: Dict[str, Any]
    confidence: str
    similarity_score: float
    reasoning: str
    matching_fields: List[str]
    conflicting_fields: List[str]
    status: str
    user_decision: Optional[str]
    update_data: Optional[Dict[str, Any]]
    created_at: str
    updated_at: str


class PaginatedDuplicatesResponse(BaseModel):
    duplicates: List[DuplicateResponse]
    total: int
    page: int
    per_page: int
    pages: int


class StatsResponse(BaseModel):
    total_duplicates: int
    pending: int
    approved: int
    rejected: int
    updated: int
    flagged: int
    errors: int
    by_confidence: Dict[str, int]


# Database dependency
def get_db():
    """Get database session."""
    db = db_manager.get_session()
    try:
        yield db
    finally:
        db.close()


# Service dependency
def get_duplicate_service(db=Depends(get_db)):
    """Get duplicate management service."""
    return DuplicateManagementService(db)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager."""
    # Startup
    db_manager.create_tables()
    yield
    # Shutdown (nothing to do for SQLite)


# Create FastAPI app
app = FastAPI(
    title="LinkedIn-CRM Duplicate Management",
    description="Web interface for managing duplicate contacts between LinkedIn and CRM",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],  # React dev server
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# API Routes
@app.get("/api/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "service": "duplicate-management"}


@app.get("/api/duplicates", response_model=PaginatedDuplicatesResponse)
async def get_duplicates(
    page: int = Query(1, ge=1),
    per_page: int = Query(20, ge=1, le=100),
    confidence: Optional[MatchConfidence] = Query(None),
    status: Optional[DuplicateStatus] = Query(DuplicateStatus.PENDING),
    service: DuplicateManagementService = Depends(get_duplicate_service)
):
    """Get paginated list of duplicate candidates."""
    try:
        offset = (page - 1) * per_page

        # Filter by status if provided
        if status:
            duplicates, total = service.get_pending_duplicates(
                limit=per_page,
                offset=offset,
                confidence_filter=confidence
            )
        else:
            duplicates, total = service.get_pending_duplicates(
                limit=per_page,
                offset=offset,
                confidence_filter=confidence
            )

        # Convert to response format
        duplicate_responses = []
        for dup in duplicates:
            duplicate_responses.append(DuplicateResponse(
                id=dup.id,
                linkedin_contact_data=dup.linkedin_contact_data,
                crm_contact_data=dup.crm_contact_data,
                confidence=dup.confidence.value,
                similarity_score=dup.similarity_score,
                reasoning=dup.reasoning,
                matching_fields=dup.matching_fields,
                conflicting_fields=dup.conflicting_fields,
                status=dup.status.value,
                user_decision=dup.user_decision,
                update_data=dup.update_data,
                created_at=dup.created_at.isoformat(),
                updated_at=dup.updated_at.isoformat()
            ))

        pages = (total + per_page - 1) // per_page

        return PaginatedDuplicatesResponse(
            duplicates=duplicate_responses,
            total=total,
            page=page,
            per_page=per_page,
            pages=pages
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving duplicates: {str(e)}")


@app.get("/api/duplicates/{duplicate_id}", response_model=DuplicateResponse)
async def get_duplicate(
    duplicate_id: int,
    service: DuplicateManagementService = Depends(get_duplicate_service)
):
    """Get a specific duplicate candidate by ID."""
    try:
        duplicate = service.get_duplicate_by_id(duplicate_id)
        if not duplicate:
            raise HTTPException(status_code=404, detail="Duplicate not found")

        return DuplicateResponse(
            id=duplicate.id,
            linkedin_contact_data=duplicate.linkedin_contact_data,
            crm_contact_data=duplicate.crm_contact_data,
            confidence=duplicate.confidence.value,
            similarity_score=duplicate.similarity_score,
            reasoning=duplicate.reasoning,
            matching_fields=duplicate.matching_fields,
            conflicting_fields=duplicate.conflicting_fields,
            status=duplicate.status.value,
            user_decision=duplicate.user_decision,
            update_data=duplicate.update_data,
            created_at=duplicate.created_at.isoformat(),
            updated_at=duplicate.updated_at.isoformat()
        )

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving duplicate: {str(e)}")


@app.post("/api/duplicates/{duplicate_id}/approve")
async def approve_duplicate(
    duplicate_id: int,
    request: UpdateRequest,
    service: DuplicateManagementService = Depends(get_duplicate_service)
):
    """Approve duplicate and update CRM."""
    try:
        success = await service.approve_duplicate_and_update_crm(
            duplicate_id,
            request.update_data,
            request.user_decision
        )

        if not success:
            raise HTTPException(status_code=400, detail="Failed to approve duplicate")

        return {"message": "Duplicate approved and CRM updated successfully", "duplicate_id": duplicate_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error approving duplicate: {str(e)}")


@app.post("/api/duplicates/{duplicate_id}/reject")
async def reject_duplicate(
    duplicate_id: int,
    request: RejectRequest,
    service: DuplicateManagementService = Depends(get_duplicate_service)
):
    """Reject duplicate match."""
    try:
        success = await service.reject_duplicate(duplicate_id, request.reason)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to reject duplicate")

        return {"message": "Duplicate rejected successfully", "duplicate_id": duplicate_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error rejecting duplicate: {str(e)}")


@app.post("/api/duplicates/{duplicate_id}/flag")
async def flag_duplicate(
    duplicate_id: int,
    request: FlagRequest,
    service: DuplicateManagementService = Depends(get_duplicate_service)
):
    """Flag duplicate for later review."""
    try:
        success = await service.flag_for_later(duplicate_id, request.reason)

        if not success:
            raise HTTPException(status_code=400, detail="Failed to flag duplicate")

        return {"message": "Duplicate flagged for later review", "duplicate_id": duplicate_id}

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error flagging duplicate: {str(e)}")


@app.get("/api/stats", response_model=StatsResponse)
async def get_duplicate_stats(
    service: DuplicateManagementService = Depends(get_duplicate_service)
):
    """Get duplicate statistics for dashboard."""
    try:
        stats = service.get_duplicate_stats()
        return StatsResponse(**stats)

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving stats: {str(e)}")


@app.get("/api/sessions")
async def get_recent_sessions(
    limit: int = Query(10, ge=1, le=50),
    service: DuplicateManagementService = Depends(get_duplicate_service)
):
    """Get recent sync sessions."""
    try:
        sessions = service.get_recent_sessions(limit)
        return [session.to_dict() for session in sessions]

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error retrieving sessions: {str(e)}")


# Serve static files for the React frontend (if built)
import os
from pathlib import Path

frontend_build_path = Path("web/frontend/build")
if frontend_build_path.exists():
    app.mount("/static", StaticFiles(directory="web/frontend/build/static"), name="static")

    @app.get("/")
    async def serve_react_app():
        """Serve the React frontend."""
        return FileResponse("web/frontend/build/index.html")

    @app.get("/{path:path}")
    async def serve_react_app_catch_all(path: str):
        """Catch-all route to serve React app for client-side routing."""
        # Check if it's an API route
        if path.startswith("api/"):
            raise HTTPException(status_code=404, detail="API endpoint not found")

        # Serve React app for all other routes
        return FileResponse("web/frontend/build/index.html")
else:
    @app.get("/")
    async def serve_api_only():
        """Serve API-only mode when frontend is not built."""
        return {
            "message": "LinkedIn-CRM Duplicate Management API",
            "status": "running",
            "docs": "/docs",
            "api": "/api",
            "note": "Frontend not built. Build with: ./scripts/build_frontend.sh"
        }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)