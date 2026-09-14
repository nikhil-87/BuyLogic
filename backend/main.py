import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.database import engine, Base, AsyncSessionLocal
from backend.seed import seed_data
from backend.routers import scenarios, data, evaluation

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Ensure tables are created and seed data exists
    try:
        await seed_data()
        print("Database initialized and seeded.")
    except Exception as e:
        print(f"Database setup error: {e}")
    yield

app = FastAPI(
    title="BuyLogic API",
    description="BuyLogic — AI Purchasing Agent for retail & quick-commerce supply chain orchestration.",
    version="1.0.0",
    lifespan=lifespan
)

# Configure CORS for local development and Next.js frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins for local dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(scenarios.router)
app.include_router(data.router)
app.include_router(evaluation.router)

@app.get("/")
async def root():
    return {
        "service": "BuyLogic API",
        "status": "operational",
        "version": "1.0.0",
        "docs": "/docs",
        "scenarios": "/api/scenarios",
        "evaluation": "/api/evaluation/run"
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
