# mevzuat_mcp_server.py
import asyncio
import logging
import os
import json
from pydantic import Field
from typing import Optional, List, Dict, Any, Union

from fastmcp import FastMCP
from fastmcp.exceptions import ToolError

from mevzuat_client import MevzuatApiClient
from mevzuat_models import (
    MevzuatSearchRequest, MevzuatSearchResult,
    MevzuatTurEnum, SortFieldEnum, SortDirectionEnum,
    MevzuatArticleNode, MevzuatArticleContent
)

# Logging ayarları
LOG_DIRECTORY = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logs")
os.makedirs(LOG_DIRECTORY, exist_ok=True)
LOG_FILE_PATH = os.path.join(LOG_DIRECTORY, "mevzuat_mcp_server.log")
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(threadName)s - %(message)s',
    handlers=[logging.FileHandler(LOG_FILE_PATH, mode='a', encoding='utf-8'),
              logging.StreamHandler()]
)
logging.getLogger("httpx").setLevel(logging.WARNING)
logger = logging.getLogger(__name__)

# FastMCP sunucusunu başlat
fastmcp_instance = FastMCP(
    name="MevzuatGovTrMCP",
    instructions="MCP server for Adalet Bakanlığı Mevzuat Bilgi Sistemi. Allows detailed searching of Turkish legislation and retrieving the content of specific articles.",
    dependencies=["httpx", "beautifulsoup4", "lxml", "markitdown", "pypdf"]
)

# ASGI sunucusu için app
app = fastmcp_instance.http_app

# ========================================================================
# ÖNEMLİ EKLENTİLER: ai-plugin.json ve openapi.json dosyalarını sunmak için endpoint'ler
# Bu, ChatGPT'nin plugin'inizi ve API şemanızı keşfetmesini sağlar.
# ========================================================================

# .well-known/ai-plugin.json dosyasını FastAPI üzerinden servis etme
@app.get("/.well-known/ai-plugin.json", include_in_schema=False)
async def get_ai_plugin_json():
    plugin_manifest_path = os.path.join(os.path.dirname(__file__), ".well-known", "ai-plugin.json")
    if not os.path.exists(plugin_manifest_path):
        logger.error(f"ai-plugin.json not found at {plugin_manifest_path}")
        # Hata durumunda 404 döndür, ancak sorun yaratmaması için geçerli bir JSON objesiyle
        return {"error": "Plugin manifest not found", "detail": f"Path: {plugin_manifest_path}"}, 404
    try:
        with open(plugin_manifest_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        logger.exception(f"Error reading ai-plugin.json: {e}")
        return {"error": "Error reading plugin manifest", "detail": str(e)}, 500

# openapi.json dosyasını FastAPI üzerinden servis etme
# FastMCP'nin kendisi OpenAPI şemasını FastMCP.http_app.openapi() üzerinden sağlar.
# Bu endpoint, GPT'nin doğrudan alabileceği bir yol sağlar.
@app.get("/openapi.json", include_in_schema=False)
async def get_openapi_json():
    # FastMCP'nin dahili FastAPI uygulamasının otomatik oluşturduğu OpenAPI şemasını döndür
    return app.openapi()


# ========================================================================
# EKLENTİLER BURADA SONA ERİYOR
# ========================================================================


# Mevzuat API istemcisi
mevzuat_client = MevzuatApiClient()

@fastmcp_instance.tool()
async def search_mevzuat(
    mevzuat_adi: Optional[str] = Field(None),
    phrase: Optional[str] = Field(None),
    mevzuat_no: Optional[str] = Field(None),
    resmi_gazete_sayisi: Optional[str] = Field(None),
    mevzuat_turleri: Optional[Union[List[MevzuatTurEnum], str]] = Field(None),
    page_number: int = Field(1, ge=1),
    page_size: int = Field(10, ge=1, le=50),
    sort_field: SortFieldEnum = Field(SortFieldEnum.RESMI_GAZETE_TARIHI),
    sort_direction: SortDirectionEnum = Field(SortDirectionEnum.DESC)
) -> MevzuatSearchResult:
    if not mevzuat_adi and not phrase and not mevzuat_no:
        raise ToolError("At least one search criterion must be provided.")

    if mevzuat_adi and phrase:
        raise ToolError("Cannot search by both 'mevzuat_adi' and 'phrase' at the same time.")

    processed_turler = mevzuat_turleri
    if isinstance(mevzuat_turleri, str):
        try:
            parsed_list = json.loads(mevzuat_turleri)
            if isinstance(parsed_list, list):
                processed_turler = parsed_list
            else:
                raise ToolError(f"'mevzuat_turleri' string must be a JSON list.")
        except json.JSONDecodeError:
            raise ToolError(f"'mevzuat_turleri' string is not valid JSON.")

    search_req = MevzuatSearchRequest(
        mevzuat_adi=mevzuat_adi,
        phrase=phrase,
        mevzuat_no=mevzuat_no,
        resmi_gazete_sayisi=resmi_gazete_sayisi,
        mevzuat_tur_list=processed_turler if processed_turler is not None else [tur for tur in MevzuatTurEnum],
        page_number=page_number,
        page_size=page_size,
        sort_field=sort_field,
        sort_direction=sort_direction
    )

    logger.info(f"Tool 'search_mevzuat' called with: {search_req.model_dump(exclude_defaults=True)}")

    try:
        result = await mevzuat_client.search_documents(search_req)
        if not result.documents and not result.error_message:
            result.error_message = "No legislation found matching the specified criteria."
        return result
    except Exception as e:
        logger.exception("search_mevzuat error")
        return MevzuatSearchResult(
            documents=[], total_results=0, current_page=page_number, page_size=page_size,
            total_pages=0, query_used=search_req.model_dump(exclude_defaults=True),
            error_message=f"Unexpected error: {str(e)}"
        )

@fastmcp_instance.tool()
async def get_mevzuat_article_tree(mevzuat_id: str = Field(...)) -> List[MevzuatArticleNode]:
    logger.info(f"Tool 'get_mevzuat_article_tree' for mevzuat_id: {mevzuat_id}")
    try:
        return await mevzuat_client.get_article_tree(mevzuat_id)
    except Exception as e:
        logger.exception("get_mevzuat_article_tree error")
        raise ToolError(f"Error retrieving article tree: {str(e)}")

@fastmcp_instance.tool()
async def get_mevzuat_article_content(
    mevzuat_id: str = Field(...),
    madde_id: str = Field(...)
) -> MevzuatArticleContent:
    logger.info(f"Tool 'get_mevzuat_article_content' for madde_id: {madde_id}")
    try:
        return await mevzuat_client.get_article_content(madde_id, mevzuat_id)
    except Exception as e:
        logger.exception("get_mevzuat_article_content error")
        return MevzuatArticleContent(
            madde_id=madde_id, mevzuat_id=mevzuat_id,
            markdown_content="", error_message=f"Unexpected error: {str(e)}"
        )
