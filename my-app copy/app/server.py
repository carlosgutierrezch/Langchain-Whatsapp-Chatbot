from fastapi import FastAPI
from fastapi.responses import RedirectResponse
from langserve import add_routes
from packages.sql_llama2 import chain as sql_llama2_chain

app = FastAPI()

add_routes(app, sql_llama2_chain, path="/packages/sql-llama2")

@app.get("/")
async def redirect_root_to_docs():
    return RedirectResponse("/docs")



if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)
