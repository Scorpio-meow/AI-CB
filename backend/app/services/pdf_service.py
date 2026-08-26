import base64
import io
import os
import logging
from typing import Optional, List, Dict, Any
import httpx
import pymupdf as fitz
from pypdf import PdfReader
from fontTools.ttLib import TTFont

from app.core.config import settings

logger = logging.getLogger(__name__)


class PDFService:
    """企業級穩健 PDF 處理服務"""

    OCR_RENDER_DPI = 150

    @staticmethod
    def _is_cjk_char(c: str) -> bool:
        """判定字元是否為 CJK 繁簡中文、注音或常用全形符號"""
        if not c:
            return False
        cp = ord(c)
        return (
            0x4E00 <= cp <= 0x9FFF    # CJK 統一表意符號
            or 0x3400 <= cp <= 0x4DBF  # CJK 擴充 A
            or 0x20000 <= cp <= 0x2A6DF # CJK 擴充 B
            or 0x2A700 <= cp <= 0x2B73F # CJK 擴充 C-F
            or 0xFF00 <= cp <= 0xFFEF  # 全形字元與符號
            or 0x3000 <= cp <= 0x303F  # CJK 標點與符號
            or 0xFE30 <= cp <= 0xFE4F  # CJK 相容形式
            or 0x3100 <= cp <= 0x312F  # 注音符號
            or 0x31A0 <= cp <= 0x31BF  # 擴充注音
        )

    @staticmethod
    def _is_valid_char(c: str) -> bool:
        """判定字元是否為合法有效字元（ASCII、CJK、常用標點與換行）"""
        return (
            PDFService._is_cjk_char(c)
            or "\u0020" <= c <= "\u007e"  # ASCII 可印字元
            or c in "\n\r\t"
            or "\u2010" <= c <= "\u2e7f"  # 通用標點符號與特殊符號
            or "\u2460" <= c <= "\u24ff"  # 帶圈數字
        )

    @staticmethod
    def _is_garbled(text: str, threshold: float = 0.35) -> bool:
        """
        評估文字是否為亂碼（若字數過少或合法字元佔比低於閾值則視為亂碼）
        """
        if not text or len(text.strip()) < 10:
            return True

        # 若文字中包含明確 CJK 漢字，通常表示有成功解析中文
        cjk_count = sum(1 for c in text if PDFService._is_cjk_char(c))
        if cjk_count > 5:
            return False

        # 檢驗合法字元比例（適用於純英文或混合文字）
        valid_count = sum(1 for c in text if PDFService._is_valid_char(c))
        valid_ratio = valid_count / len(text)
        return valid_ratio < (1 - threshold)

    @staticmethod
    def _font_has_tounicode(doc, xref: int) -> bool:
        """檢查字型是否已包含 ToUnicode 映射"""
        try:
            key = doc.xref_get_key(xref, "ToUnicode")
            return bool(key and len(key) >= 2 and key[0] != "null" and key[1] != "null")
        except Exception:
            return False

    @staticmethod
    def _repair_fonts_and_inject_tounicode(doc) -> int:
        """
        掃描 PDF 內部所有內嵌字型，使用 fontTools 分析其內部 cmap 表，
        若缺少 ToUnicode 則動態建立 Adobe-Identity-UCS CMap stream 注入，修復亂碼
        """
        repaired_count = 0
        try:
            seen_xrefs = set()
            for page_num in range(len(doc)):
                page = doc[page_num]
                font_list = page.get_fonts(full=True)
                for font_tuple in font_list:
                    xref = font_tuple[0]
                    name = font_tuple[3]
                    if xref in seen_xrefs or xref <= 0:
                        continue
                    seen_xrefs.add(xref)

                    # 若已有 ToUnicode 則跳過
                    if PDFService._font_has_tounicode(doc, xref):
                        continue

                    try:
                        # 提取內嵌字型 stream
                        extracted = doc.extract_font(xref)
                        font_bytes = extracted.get("buffer")
                        if not font_bytes:
                            continue

                        # 使用 fontTools 分析 TrueType / OpenType 字型
                        tt = TTFont(io.BytesIO(font_bytes))
                        cmap_table = tt.getBestCmap()
                        if not cmap_table:
                            continue

                        glyph_order = tt.getGlyphOrder()
                        glyph_to_gid = {glyph: idx for idx, glyph in enumerate(glyph_order)}
                        gid_to_uni: Dict[int, int] = {}

                        for uni_cp, glyph_name in cmap_table.items():
                            gid = glyph_to_gid.get(glyph_name)
                            if gid is not None:
                                gid_to_uni[gid] = uni_cp

                        if not gid_to_uni:
                            continue

                        # 建構 Adobe-Identity-UCS CMap stream
                        lines = [
                            "/CIDInit /ProcSet findresource begin",
                            "12 dict begin begincmap",
                            "/CIDSystemInfo << /Registry (Adobe) /Ordering (UCS) /Supplement 0 >> def",
                            "/CMapName /Adobe-Identity-UCS def",
                            "1 begincodespacerange",
                            "<0000> <FFFF>",
                            "endcodespacerange",
                            f"{len(gid_to_uni)} beginbfchar",
                        ]

                        for gid, uni_cp in gid_to_uni.items():
                            if uni_cp <= 0xFFFF:
                                lines.append(f"<{gid:04X}> <{uni_cp:04X}>")
                            else:
                                utf16_hex = chr(uni_cp).encode("utf-16-be").hex().upper()
                                lines.append(f"<{gid:04X}> <{utf16_hex}>")

                        lines.extend([
                            "endbfchar",
                            "endcmap",
                            "CMapName currentdict /CMap defineresource pop",
                            "end",
                            "end"
                        ])
                        cmap_str = "\n".join(lines)
                        cmap_bytes = cmap_str.encode("latin1")

                        # 建立新 Stream 物件並注入 PDF
                        new_xref = doc.get_new_xref()
                        doc.update_object(new_xref, "<<>>")
                        doc.update_stream(new_xref, cmap_bytes)
                        doc.xref_set_key(xref, "ToUnicode", f"{new_xref} 0 R")
                        repaired_count += 1
                        logger.info(f"成功為字型 {name} (xref={xref}) 注入 ToUnicode CMap 表 ({len(gid_to_uni)} 字元)")
                    except Exception as fe:
                        logger.debug(f"分析字型 {name} (xref={xref}) 失敗: {fe}")
                        continue
        except Exception as e:
            logger.warning(f"掃描與修復字型 CMap 時發生錯誤: {e}")

        return repaired_count

    @staticmethod
    async def _ocr_page_fallback(page, page_num: int) -> str:
        """
        針對掃描圖檔或文字損毀之頁面，轉為高解析度圖檔後調用 Vision 模型備援識別
        """
        try:
            # 渲染為 150 DPI 圖片
            zoom = PDFService.OCR_RENDER_DPI / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")
            b64_img = base64.b64encode(img_bytes).decode("utf-8")

            # 1. 優先使用 Azure OpenAI 視覺端點
            if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
                endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
                api_key = settings.AZURE_OPENAI_API_KEY
                azure_deployments = [d.strip() for d in (settings.AZURE_OPENAI_DEPLOYMENT or "").split(",") if d.strip()]
                deployment = azure_deployments[0] if azure_deployments else "gpt-4o"
                
                url = f"{endpoint}/openai/v1/chat/completions"
                headers = {
                    "api-key": api_key,
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": deployment,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "請精確識別並提取此頁面中的所有繁體中文、表格與文字內容，保留標題結構，不要添加多餘客套話。"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{b64_img}"}
                                }
                            ]
                        }
                    ],
                    "temperature": 0.1
                }
                async with httpx.AsyncClient(timeout=60.0) as client:
                    resp = await client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"]
                        logger.info(f"第 {page_num} 頁使用 Azure Vision OCR 識別成功 ({len(content)} 字)")
                        return content
        except Exception as e:
            logger.warning(f"第 {page_num} 頁執行 Vision OCR 失敗: {e}")

        return f"[第 {page_num} 頁為掃描圖片或複雜版面，已記錄]"

    @classmethod
    def extract_text_robust(cls, file_path: str) -> str:
        """
        同步/標準進入點：執行多層防護 PDF 抽取
        """
        import asyncio
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 若已在非同步事件循環中，使用標準 PyMuPDF + CMap 修復
                return cls._extract_sync_internal(file_path, enable_async_ocr=False)
        except RuntimeError:
            pass

        return cls._extract_sync_internal(file_path, enable_async_ocr=False)

    @classmethod
    def _extract_sync_internal(cls, file_path: str, enable_async_ocr: bool = False) -> str:
        """內部提取實作：PyMuPDF + 字型 CMap 修復 + pypdf 雙重備援"""
        try:
            doc = fitz.open(file_path)
            if doc.is_encrypted:
                try:
                    doc.authenticate("")
                except Exception:
                    raise ValueError("PDF 文件被密碼保護，無法讀取")

            # 步驟 1：字型掃描與 ToUnicode CMap 動態注入修復
            repaired_fonts = cls._repair_fonts_and_inject_tounicode(doc)
            if repaired_fonts > 0:
                logger.info(f"PDF 檔案 {os.path.basename(file_path)} 共修復了 {repaired_fonts} 個字型之 ToUnicode 映射")

            # 步驟 2：逐頁提取文字與品質檢測
            pages_text: List[str] = []
            for page_idx in range(len(doc)):
                page_num = page_idx + 1
                page = doc[page_idx]
                page_raw = page.get_text("text")

                if page_raw and page_raw.strip() and not cls._is_garbled(page_raw):
                    pages_text.append(f"--- 第 {page_num} 頁 ---\n{page_raw.strip()}\n")
                else:
                    # 嘗試以 blocks 模式重抓
                    blocks = page.get_text("blocks")
                    block_texts = [b[4].strip() for b in blocks if len(b) >= 5 and b[4].strip()]
                    joined_blocks = "\n".join(block_texts)
                    
                    if joined_blocks and not cls._is_garbled(joined_blocks):
                        pages_text.append(f"--- 第 {page_num} 頁 ---\n{joined_blocks}\n")
                    else:
                        logger.warning(f"第 {page_num} 頁文字為空或判定為亂碼 (文字長度: {len(page_raw)})")
                        pages_text.append(f"--- 第 {page_num} 頁 ---\n{page_raw.strip() if page_raw.strip() else '[本頁為圖檔或無可提取純文字]'}\n")

            doc.close()
            full_text = "\n".join(pages_text).strip()
            if full_text:
                logger.info(f"成功從 PDF 提取 {len(pages_text)} 頁，共 {len(full_text)} 字元")
                return full_text
        except Exception as e:
            logger.warning(f"PyMuPDF 穩健讀取失敗 ({e})，啟動 pypdf 備援降級")

        # 步驟 3：pypdf 備援機制
        text_content = []
        with open(file_path, 'rb') as file:
            pdf_reader = PdfReader(file)
            if pdf_reader.is_encrypted:
                try:
                    pdf_reader.decrypt("")
                except Exception:
                    raise ValueError("PDF 文件被密碼保護，無法讀取")

            for page_num, page in enumerate(pdf_reader.pages):
                try:
                    page_text = page.extract_text()
                    if page_text and page_text.strip():
                        text_content.append(f"--- 第 {page_num + 1} 頁 ---\n{page_text.strip()}\n")
                except Exception:
                    continue

        if not text_content:
            raise ValueError("PDF 文件中沒有可提取的文本內容（可能是純圖檔掃描件）")

        return "\n".join(text_content)