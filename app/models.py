from sqlalchemy import Column, Integer, String, ForeignKey, Float, DateTime, LargeBinary
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.sql import func
from pgvector.sqlalchemy import Vector
from .database import Base
import uuid

class AudioFile(Base):
    __tablename__ = "audio_files"

    # ID is a primary key
    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Metadata
    filename: Mapped[str] = mapped_column(String, nullable=False)
    file_hash: Mapped[str] = mapped_column(String, unique=True, index=True) # SHA256 to prevent duplicates
    duration_seconds: Mapped[float] = mapped_column(Float)
    
    # THE BLOBS (Binary Large Object) - Actual Audio Data
    # In a real startup, you'd put this in AWS S3, but for this DBMS project, 
    # we put it in the DB to show off binary handling.
    binary_data: Mapped[bytes] = mapped_column(LargeBinary)

    # THE AI BRAIN
    # We are reserving space for a 128-dimensional vector
    embedding: Mapped[list[float]] = mapped_column(Vector(128))

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

class AudioLineage(Base):
    __tablename__ = "audio_lineage"

    id: Mapped[int] = mapped_column(primary_key=True, index=True)
    
    # Recursive Relationship
    parent_id: Mapped[int] = mapped_column(ForeignKey("audio_files.id"))
    child_id: Mapped[int] = mapped_column(ForeignKey("audio_files.id"))
    
    # How similar are they? (0.0 to 1.0)
    similarity_score: Mapped[float] = mapped_column(Float)
    
    detected_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())