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
            0x4E00 <= cp <= 0x9FFF
            or 0x3400 <= cp <= 0x4DBF
            or 0x20000 <= cp <= 0x2A6DF
            or 0x2A700 <= cp <= 0x2B73F
            or 0xFF00 <= cp <= 0xFFEF
            or 0x3000 <= cp <= 0x303F
            or 0xFE30 <= cp <= 0xFE4F
            or 0x3100 <= cp <= 0x312F
            or 0x31A0 <= cp <= 0x31BF
        )
    @staticmethod
    def _is_valid_char(c: str) -> bool:
        """判定字元是否為合法有效字元（ASCII、CJK、常用標點與換行）"""
        return (
            PDFService._is_cjk_char(c)
            or "\u0020" <= c <= "\u007e"
            or c in "\n\r\t"
            or "\u2010" <= c <= "\u2e7f"
            or "\u2460" <= c <= "\u24ff"
        )
    @staticmethod
    def _is_garbled(text: str, threshold: float = 0.35) -> bool:
        """
        評估文字是否為亂碼（若字數過少或合法字元佔比低於閾值則視為亂碼）
        """
        if not text or len(text.strip()) < 10:
            return True
        cjk_count = sum(1 for c in text if PDFService._is_cjk_char(c))
        if cjk_count > 5:
            return False
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
                    if PDFService._font_has_tounicode(doc, xref):
                        continue
                    try:
                        extracted = doc.extract_font(xref)
                        font_bytes = extracted.get("buffer")
                        if not font_bytes:
                            continue
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
    def _is_vision_available() -> bool:
        """檢查是否配置了可用的 Vision 模型端點"""
        return bool(
            (settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY)
            or settings.OPENAI_API_KEY
            or settings.GEMINI_API_KEY
        )
    @classmethod
    def _ocr_page_sync(cls, page, page_num: int) -> str:
        """
        針對掃描圖檔或文字損毀之頁面，轉為高解析度圖檔後調用 Vision 模型識別（同步執行）
        """
        if not cls._is_vision_available():
            logger.warning(f"第 {page_num} 頁文字為空，但未配置 Vision API 端點，略過 OCR")
            return f"[第 {page_num} 頁為掃描圖片或複雜版面]"
        try:
            zoom = cls.OCR_RENDER_DPI / 72.0
            mat = fitz.Matrix(zoom, zoom)
            pix = page.get_pixmap(matrix=mat, alpha=False)
            img_bytes = pix.tobytes("png")
            b64_img = base64.b64encode(img_bytes).decode("utf-8")
            if settings.AZURE_OPENAI_ENDPOINT and settings.AZURE_OPENAI_API_KEY:
                endpoint = settings.AZURE_OPENAI_ENDPOINT.rstrip('/')
                api_key = settings.AZURE_OPENAI_API_KEY
                azure_deployments = [d.strip() for d in (settings.AZURE_OPENAI_DEPLOYMENT or "").split(",") if d.strip()]
                deployment = azure_deployments[0] if azure_deployments else settings.OPENAI_VISION_MODEL
                
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
                                "text": "精確識別並提取此頁面中的所有繁體中文、英文、表格與文字內容，保留標題結構與階層，排版整潔，不要添加任何多餘的問候或客套話。"
                            },
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64_img}"}
                            }
                        ]
                    }
                ]
            }
                with httpx.Client(timeout=settings.LLM_TIMEOUT) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"].strip()
                        logger.info(f"第 {page_num} 頁使用 Azure Vision OCR 識別成功 ({len(content)} 字)")
                        return content
                    else:
                        logger.warning(f"第 {page_num} 頁 Azure Vision OCR 回傳錯誤 ({resp.status_code}): {resp.text[:200]}")
            elif settings.OPENAI_API_KEY:
                base_url = settings.OPENAI_API_BASE.rstrip('/')
                url = f"{base_url}/chat/completions"
                headers = {
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": settings.OPENAI_VISION_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "請精確識別並提取此頁面中的所有繁體中文、英文、表格與文字內容，保留標題結構與階層，排版整潔，不要添加任何多餘的問候或客套話。"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{b64_img}"}
                                }
                            ]
                        }
                    ]
                }
                with httpx.Client(timeout=settings.LLM_TIMEOUT) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"].strip()
                        logger.info(f"第 {page_num} 頁使用 OpenAI Vision OCR 識別成功 ({len(content)} 字)")
                        return content
            elif settings.GEMINI_API_KEY:
                base_url = settings.GEMINI_API_BASE.rstrip('/')
                url = f"{base_url}/v1beta/openai/chat/completions"
                headers = {
                    "Authorization": f"Bearer {settings.GEMINI_API_KEY}",
                    "Content-Type": "application/json"
                }
                payload = {
                    "model": settings.GEMINI_VISION_MODEL,
                    "messages": [
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": "請精確識別並提取此頁面中的所有繁體中文、英文、表格與文字內容，保留標題結構與階層，排版整潔，不要添加任何多餘的問候或客套話。"
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {"url": f"data:image/png;base64,{b64_img}"}
                                }
                            ]
                        }
                    ]
                }
                with httpx.Client(timeout=settings.LLM_TIMEOUT) as client:
                    resp = client.post(url, headers=headers, json=payload)
                    if resp.status_code == 200:
                        content = resp.json()["choices"][0]["message"]["content"].strip()
                        logger.info(f"第 {page_num} 頁使用 Gemini Vision OCR 識別成功 ({len(content)} 字)")
                        return content
        except Exception as e:
            logger.warning(f"第 {page_num} 頁執行 Vision OCR 失敗: {e}")
        return f"[第 {page_num} 頁為掃描圖片或複雜版面，已記錄]"
    @classmethod
    def extract_text_robust(cls, file_path: str) -> str:
        """
        同步/標準進入點：執行多層防護 PDF 抽取（支援內嵌字型修復 + Vision OCR 智慧補全）
        """
        return cls._extract_sync_internal(file_path)
    @classmethod
    def _extract_sync_internal(cls, file_path: str) -> str:
        """內部提取實作：PyMuPDF + 字型 CMap 修復 + Vision OCR + pypdf 雙重備援"""
        import concurrent.futures
        try:
            doc = fitz.open(file_path)
            if doc.is_encrypted:
                try:
                    doc.authenticate("")
                except Exception:
                    raise ValueError("PDF 文件被密碼保護，無法讀取")
            repaired_fonts = cls._repair_fonts_and_inject_tounicode(doc)
            if repaired_fonts > 0:
                logger.info(f"PDF 檔案 {os.path.basename(file_path)} 共修復了 {repaired_fonts} 個字型之 ToUnicode 映射")
            pages_text: List[Optional[str]] = [None] * len(doc)
            ocr_jobs = []
            for page_idx in range(len(doc)):
                page_num = page_idx + 1
                page = doc[page_idx]
                page_raw = page.get_text("text")
                if page_raw and page_raw.strip() and not cls._is_garbled(page_raw):
                    pages_text[page_idx] = f"--- 第 {page_num} 頁 ---\n{page_raw.strip()}\n"
                else:
                    blocks = page.get_text("blocks")
                    block_texts = [b[4].strip() for b in blocks if len(b) >= 5 and b[4].strip()]
                    joined_blocks = "\n".join(block_texts)
                    
                    if joined_blocks and not cls._is_garbled(joined_blocks):
                        pages_text[page_idx] = f"--- 第 {page_num} 頁 ---\n{joined_blocks}\n"
                    else:
                        logger.warning(f"第 {page_num} 頁文字為空或判定為亂碼 (文字長度: {len(page_raw)})，加入 OCR 佇列")
                        ocr_jobs.append((page_idx, page_num, page))
            if ocr_jobs and cls._is_vision_available():
                logger.info(f"正在對 {len(ocr_jobs)} 頁純圖檔/掃描頁面啟動 Vision OCR 並行識別...")
                max_workers = min(len(ocr_jobs), 4)
                with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                    future_to_job = {
                        executor.submit(cls._ocr_page_sync, job[2], job[1]): job
                        for job in ocr_jobs
                    }
                    for future in concurrent.futures.as_completed(future_to_job):
                        job = future_to_job[future]
                        page_idx = job[0]
                        page_num = job[1]
                        try:
                            ocr_text = future.result()
                            if ocr_text and not ocr_text.startswith("[第 "):
                                pages_text[page_idx] = f"--- 第 {page_num} 頁 (OCR 識別) ---\n{ocr_text.strip()}\n"
                            else:
                                pages_text[page_idx] = f"--- 第 {page_num} 頁 ---\n{ocr_text.strip()}\n"
                        except Exception as e:
                            logger.warning(f"第 {page_num} 頁 OCR 任務執行失敗: {e}")
                            pages_text[page_idx] = f"--- 第 {page_num} 頁 ---\n[本頁為圖檔或無可提取純文字]\n"
            elif ocr_jobs:
                for job in ocr_jobs:
                    page_idx = job[0]
                    page_num = job[1]
                    pages_text[page_idx] = f"--- 第 {page_num} 頁 ---\n[本頁為圖檔或無可提取純文字]\n"
            doc.close()
            final_pages = [p for p in pages_text if p is not None]
            full_text = "\n".join(final_pages).strip()
            if full_text:
                logger.info(f"成功從 PDF 提取 {len(final_pages)} 頁，共 {len(full_text)} 字元")
                return full_text
        except Exception as e:
            logger.warning(f"PyMuPDF 穩健讀取失敗 ({e})，啟動 pypdf 備援降級")
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