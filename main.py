# main.py (GÜNCELLENMİŞ VERSİYON - on_event kaldırıldı)
import os
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi # get_openapi fonksiyonunu import edin

# mevzuat_mcp_server.py dosyasından FastMCP uygulamasını içeri aktarıyoruz
from mevzuat_mcp_server import app as mevzuat_mcp_app

# Ana FastAPI uygulamasını oluşturuyoruz
main_app = FastAPI(
    title="Mevzuat MCP Gateway",
    description="Gateway for MevzuatGovTrMCP FastMCP server, serving plugin manifests and OpenAPI schema.",
    version="0.1.0"
)

# FastMCP uygulamasını ana FastAPI uygulamasına mount ediyoruz
# Bu satır, FastAPI uygulamasının oluşturulmasından sonra,
# ancak get_openapi_json fonksiyonundan ÖNCE gelmeli.
main_app.mount("/fastmcp", mevzuat_mcp_app)

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

# OpenAPI şemasını servis etme
# ChatGPT'nin doğru şekilde çalışabilmesi için bu fonksiyonu güncelliyoruz
@main_app.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    openapi_schema = get_openapi(
        title=main_app.title,
        version=main_app.version,
        description=main_app.description,
        routes=main_app.routes, # main_app'in tüm rotalarını (mounted olanlar dahil) kullanır
    )
    
    # Plugin'in doğru URL'yi bilmesi için servers alanını ekliyoruz
    # Render.com URL'nizi buraya yazın
    openapi_schema["servers"] = [{"url": "https://mevzuat-mcp-ub26.onrender.com"}]
    
    return JSONResponse(content=openapi_schema)


# / (kök) yola erişildiğinde basit bir yanıt dön
@main_app.get("/")
async def read_root():
    return {"message": "Mevzuat MCP Gateway is running. Access /fastmcp for the main FastMCP application."}

# on_event("startup") ve on_event("shutdown") event'leri kaldırıldı
# Zira 'AttributeError: 'FastMCP' object has no attribute '_tools'' hatasına neden oluyorlardı.
# Ayrıca, bu event'ler FastAPI'nin yeni versiyonlarında "deprecated" olarak işaretlenmiştir.
