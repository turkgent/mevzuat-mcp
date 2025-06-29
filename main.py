# main.py (En Son GÜNCELLENMİŞ VERSİYON - OpenAPI Manuel Birleştirme)
import os
import json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import JSONResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.openapi.utils import get_openapi
from fastapi.routing import APIRoute

# mevzuat_mcp_server.py dosyasından FastMCP uygulamasını içeri aktarıyoruz
from mevzuat_mcp_server import app as mevzuat_mcp_app

# Ana FastAPI uygulamasını oluşturuyoruz
main_app = FastAPI(
    title="Mevzuat MCP Gateway",
    description="Gateway for MevzuatGovTrMCP FastMCP server, serving plugin manifests and OpenAPI schema.",
    version="0.1.0"
)

# FastMCP uygulamasını ana FastAPI uygulamasına mount ediyoruz
# Bu satırın sırası önemli, APIRoute nesneleri oluşturulmadan önce olmalı.
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
# Bu fonksiyonu, hem ana uygulamanın hem de mounted FastMCP uygulamasının
# rotalarını içerecek şekilde manuel olarak birleştiriyoruz.
@main_app.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    # 1. Ana uygulamanın temel OpenAPI şemasını al
    main_openapi_schema = get_openapi(
        title=main_app.title,
        version=main_app.version,
        description=main_app.description,
        routes=main_app.routes,
    )
    
    # 2. FastMCP uygulamasının OpenAPI şemasını al
    # FastMCP'nin içindeki API endpoint'leri '/fastmcp' prefix'i altında olduğu için,
    # FastMCP'nin kendi openapi() metodunu çağırmalıyız.
    fastmcp_openapi_schema = mevzuat_mcp_app.openapi() # Bu, FastMCP'nin kendi içindeki tool'ları içerir

    # 3. FastMCP şemasındaki yolları ana şemaya ekle, prefix'i düzgünce ayarla
    for path, path_item in fastmcp_openapi_schema.get("paths", {}).items():
        # FastMCP'nin yolları zaten '/tools' gibi alt yollara sahip,
        # ana uygulamada '/fastmcp' altına mount edildiği için onları yeniden prefix'lemeye gerek yok.
        # FastMCP'nin FastMCP("name", "desc", "deps") yapısı otomatik olarak '/tools' gibi yolları oluşturur.
        # Bu yolları doğrudan '/fastmcp' prefix'i altına ekliyoruz.
        main_openapi_schema["paths"][f"/fastmcp{path}"] = path_item

    # 4. FastMCP şemasındaki bileşenleri (schemas/definitions) ana şemaya ekle
    # Pydantic modelleri gibi şema tanımlarını birleştiriyoruz
    if "components" in fastmcp_openapi_schema:
        if "components" not in main_openapi_schema:
            main_openapi_schema["components"] = {}
        if "schemas" in fastmcp_openapi_schema["components"]:
            if "schemas" not in main_openapi_schema["components"]:
                main_openapi_schema["components"]["schemas"] = {}
            main_openapi_schema["components"]["schemas"].update(
                fastmcp_openapi_schema["components"]["schemas"]
            )

    # 5. servers alanını ekle (ChatGPT için kritik)
    main_openapi_schema["servers"] = [{"url": "https://mevzuat-mcp-ub26.onrender.com"}]
    
    return JSONResponse(content=main_openapi_schema)


# / (kök) yola erişildiğinde basit bir yanıt dön
@main_app.get("/")
async def read_root():
    return {"message": "Mevzuat MCP Gateway is running. Access /fastmcp for the main FastMCP application."}
