# main.py (DÜZELTİLMİŞ VERSİYON)
import os
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi

# mevzuat_mcp_server.py dosyasından FastMCP uygulamasını içeri aktarıyoruz
from mevzuat_mcp_server import app as mevzuat_mcp_app, fastmcp_instance

# Ana FastAPI uygulamasını oluşturuyoruz
main_app = FastAPI(
    title="Mevzuat MCP Gateway",
    description="Gateway for MevzuatGovTrMCP FastMCP server, serving plugin manifests and OpenAPI schema.",
    version="0.1.0"
)

# FastMCP uygulamasını doğrudan ana uygulamaya dahil ediyoruz (mount etmek yerine)
# Bu sayede tüm endpoint'ler ana seviyede görünür olacak
main_app.include_router(mevzuat_mcp_app.router)

# .well-known/ai-plugin.json dosyasını servis etme
@main_app.get("/.well-known/ai-plugin.json", include_in_schema=False)
async def get_ai_plugin_json():
    plugin_manifest_path = os.path.join(os.path.dirname(__file__), ".well-known", "ai-plugin.json")
    if not os.path.exists(plugin_manifest_path):
        raise HTTPException(status_code=404, detail="Plugin manifest not found")
    try:
        with open(plugin_manifest_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading plugin manifest: {str(e)}")

# OpenAPI şemasını servis etme - FastMCP endpoint'lerini de dahil eder
@main_app.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    # Ana uygulamanın OpenAPI şemasını al (FastMCP endpoint'leri dahil)
    openapi_schema = get_openapi(
        title=main_app.title,
        version=main_app.version,
        description=main_app.description,
        routes=main_app.routes,
    )
    
    # Plugin'in doğru URL'yi bilmesi için servers alanını ekliyoruz
    openapi_schema["servers"] = [{"url": "https://mevzuat-mcp-ub26.onrender.com"}]
    
    return JSONResponse(content=openapi_schema)

# Ana endpoint - FastMCP bilgilerini de göster
@main_app.get("/")
async def read_root():
    return {
        "message": "Mevzuat MCP Gateway is running",
        "fastmcp_info": {
            "name": fastmcp_instance.name,
            "instructions": fastmcp_instance.instructions,
            "available_tools": len(fastmcp_instance._tools),
        },
        "endpoints": {
            "openapi_schema": "/openapi.json",
            "ai_plugin_manifest": "/.well-known/ai-plugin.json",
            "mcp_tools": "/mcp/tools",
            "mcp_call_tool": "/mcp/call_tool"
        }
    }

# Startup event - bağlantıları başlat
@main_app.on_event("startup")
async def startup_event():
    print("Mevzuat MCP Gateway started successfully!")
    print(f"Available FastMCP tools: {list(fastmcp_instance._tools.keys())}")

# Shutdown event - bağlantıları temizle  
@main_app.on_event("shutdown")
async def shutdown_event():
    from mevzuat_mcp_server import mevzuat_client
    await mevzuat_client.close()
    print("Mevzuat MCP Gateway shutdown complete!")
