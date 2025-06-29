# main.py
import os
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles

# mevzuat_mcp_server.py dosyasından FastMCP uygulamasını içeri aktarıyoruz
# Buradaki 'app' artık doğrudan FastMCP uygulaması olacak
from mevzuat_mcp_server import app as mevzuat_mcp_app # 'app' adını çakışmaması için değiştirdik

# Ana FastAPI uygulamasını oluşturuyoruz
main_app = FastAPI(
    title="Mevzuat MCP Gateway",
    description="Gateway for MevzuatGovTrMCP FastMCP server, serving plugin manifests and OpenAPI schema.",
    version="0.1.0"
)

# Statik dosyaların bulunduğu dizinleri tanımla
# FastAPI, .well-known gibi özel dizinleri doğrudan sunamaz, bu yüzden endpoint tanımlıyoruz.
# Ancak, eğer başka statik dosyalarınız varsa (örneğin logo.png gibi),
# bunları '/static' altında sunmak için aşağıdaki gibi bir mount kullanabilirsiniz:
# static_dir = os.path.join(os.path.dirname(__file__))
# main_app.mount("/static", StaticFiles(directory=static_dir), name="static")

# .well-known/ai-plugin.json dosyasını servis etme
# FastAPI'nin .well-known/ dizinini otomatik olarak sunmasını sağlamak zor olabilir
# bu yüzden bu endpoint'i manuel olarak tanımlıyoruz.
@main_app.get("/.well-known/ai-plugin.json", include_in_schema=False)
async def get_ai_plugin_json():
    # .well-known klasörünün ana dizinle aynı seviyede olduğunu varsayıyoruz
    plugin_manifest_path = os.path.join(os.path.dirname(__file__), ".well-known", "ai-plugin.json")
    
    if not os.path.exists(plugin_manifest_path):
        raise HTTPException(status_code=404, detail="Plugin manifest not found")
    
    try:
        with open(plugin_manifest_path, "r", encoding="utf-8") as f:
            return JSONResponse(content=json.load(f))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error reading plugin manifest: {str(e)}")

# OpenAPI şemasını servis etme
# FastMCP'nin kendi şemasını döndürecektir.
# Bu endpoint, ChatGPT'ye vereceğimiz URL olacak.
@main_app.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    # FastMCP uygulamasının OpenAPI şemasına doğrudan erişim
    # Render.com'daki FastMCP uygulamamızın URL'si ön eklenecek.
    # Örn: https://mevzuat-mcp-ub26.onrender.com/fastmcp/openapi.json
    return mevzuat_mcp_app.openapi()


# FastMCP uygulamasını ana FastAPI uygulamasına mount ediyoruz
# FastMCP uygulaması artık '/fastmcp' prefix'i altında çalışacak.
# Yani, ChatGPT'nin araçlarını çağırırken isteği https://mevzuat-mcp-ub26.onrender.com/fastmcp/tools adresine gönderecek.
main_app.mount("/fastmcp", mevzuat_mcp_app)

# / (kök) yola erişildiğinde basit bir yanıt dön
@main_app.get("/")
async def read_root():
    return {"message": "Mevzuat MCP Gateway is running. Access /fastmcp for the main FastMCP application."}
