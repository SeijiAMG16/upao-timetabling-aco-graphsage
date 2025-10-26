"""
Servidor simple sin uvicorn reload para debug
"""
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # Sin reload para evitar problemas
        log_level="debug"
    )
