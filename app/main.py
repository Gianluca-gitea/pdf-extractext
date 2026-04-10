from fastapi import FastAPI


app = FastAPI(title="PDF Extractext API")


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}
