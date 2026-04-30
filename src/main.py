from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from loguru import logger

from routers import tracking_router, videos_router

# Configure logger
logger.remove()
logger.add(
    "logs/app.log",
    rotation="500 MB",
    retention="10 days",
    level="INFO",
)
logger.add(
    lambda msg: print(msg, end=""),
    level="INFO",
)


# Create FastAPI app
app = FastAPI(
    title="Tracking API",
    description="Multi-object tracking API powered by ByteTrack",
    version="1.0.0",
)


# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Include routers
app.include_router(tracking_router)
app.include_router(videos_router)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Welcome to ByteTrack API",
        "docs": "/docs",
        "tracking_endpoints": "/docs#/tracking",
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    
    logger.info("Starting ByteTrack API server...")
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8085,
        reload=True,
        log_level="info",
    )
