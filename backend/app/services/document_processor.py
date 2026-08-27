#!/usr/bin/env python3
import os
import json
import csv
import logging
import hashlib
from typing import Optional
from html.parser import HTMLParser
from pypdf import PdfReader
from docx import Document as DocxDocument
from pptx import Presentation
import openpyxl
from app.core.config import settings
logger = logging.getLogger(__name__)
class _HTMLTextExtractor(HTMLParser):
    def __init__(self):
        super().__init__()
        self.result = []
        self.skip = False
    def handle_starttag(self, tag, attrs):
        if tag in ('script', 'style', 'head', 'meta', 'link'):
            self.skip = True
    def handle_endtag(self, tag):
        if tag in ('script', 'style', 'head', 'meta', 'link'):
            self.skip = False
        elif tag in ('p', 'div', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 'li', 'tr', 'br', 'section', 'article'):
            self.result.append("\n")
    def handle_data(self, data):
        if not self.skip:
            text = data.strip()
            if text:
                self.result.append(text + " ")
    def get_text(self):
        return "".join(self.result).strip()
class DocumentProcessor:
    
    FILE_SIGNATURES = {
        'application/pdf': [b'%PDF'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [b'PK\x03\x04'],
        'application/vnd.openxmlformats-officedocument.presentationml.presentation': [b'PK\x03\x04'],
        'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet': [b'PK\x03\x04'],
        'text/plain': [],
        'text/markdown': [],
        'text/x-markdown': [],
        'text/csv': [],
        'application/json': [],
        'text/json': [],
        'text/html': [],
        'text/xml': [],
        'application/xml': [],
        'text/yaml': [],
        'application/x-yaml': []
    }
    SUPPORTED_EXTENSIONS = {
        '.txt', '.md', '.markdown', '.pdf', '.docx', '.pptx', '.xlsx',
        '.csv', '.json', '.yaml', '.yml', '.xml', '.html', '.htm', '.log',
        '.py', '.js', '.ts', '.tsx', '.jsx', '.java', '.cpp', '.c', '.sql',
        '.sh', '.ini', '.env'
    }
    
    @staticmethod
    def validate_file_header(file_path: str, content_type: str) -> bool:
        signatures = DocumentProcessor.FILE_SIGNATURES.get(content_type)
        if signatures is None or not signatures:
            return True
        
        try:
            with open(file_path, 'rb') as f:
                header = f.read(512)
                
            for signature in signatures:
                if header.startswith(signature):
                    return True
            
            logger.warning(f"檔案頭部驗證失敗: {file_path}, 聲稱類型: {content_type}")
            raise ValueError(
                f"檔案頭部與聲稱的類型不符。"
                f"這可能是一個偽造的檔案或損壞的檔案。"
            )
            
        except Exception as e:
            logger.error(f"驗證檔案頭部時發生錯誤: {e}")
            raise
    
    @staticmethod
    def calculate_file_hash(file_path: str) -> str:
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def extract_text_from_file(file_path: str, content_type: str) -> Optional[str]:
        try:
            ext = os.path.splitext(file_path)[1].lower()
            
            if ext == ".docx":
                content_type = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            elif ext == ".pptx":
                content_type = "application/vnd.openxmlformats-officedocument.presentationml.presentation"
            elif ext == ".xlsx":
                content_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            elif ext == ".pdf":
                content_type = "application/pdf"
            elif ext in ('.md', '.markdown'):
                content_type = "text/markdown"
            elif ext == '.csv':
                content_type = "text/csv"
            elif ext == '.json':
                content_type = "application/json"
            elif ext in ('.html', '.htm'):
                content_type = "text/html"
            DocumentProcessor.validate_file_header(file_path, content_type)
            file_size = os.path.getsize(file_path)
            max_size = int(settings.MAX_FILE_SIZE_MB) * 1024 * 1024
            if file_size > max_size:
                raise ValueError(f"檔案大小 ({file_size} bytes) 超過限制")
            if ext == ".pdf" or content_type == "application/pdf":
                return DocumentProcessor._extract_from_pdf(file_path)
            elif ext == ".docx" or content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return DocumentProcessor._extract_from_docx(file_path)
            elif ext == ".pptx" or content_type == "application/vnd.openxmlformats-officedocument.presentationml.presentation":
                return DocumentProcessor._extract_from_pptx(file_path)
            elif ext == ".xlsx" or content_type == "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet":
                return DocumentProcessor._extract_from_xlsx(file_path)
            elif ext == ".csv" or content_type == "text/csv":
                return DocumentProcessor._extract_from_csv(file_path)
            elif ext in (".js", ".ts", ".jsx", ".tsx", ".json", ".jsonl", ".py", ".yaml", ".yml", ".ini", ".env", ".sql"):
                return DocumentProcessor._extract_from_code_or_data(file_path, ext)
            elif ext in (".html", ".htm") or content_type == "text/html":
                return DocumentProcessor._extract_from_html(file_path)
            else:
                return DocumentProcessor._extract_from_txt(file_path)
        except Exception as e:
            logger.error(f"提取文本時發生錯誤: {e}")
            raise
    
    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        encodings = ['utf-8', 'utf-8-sig', 'big5', 'gbk', 'gb2312', 'latin1']
        
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding) as f:
                    content = f.read()
                if content.strip():
                    logger.info(f"成功使用 {encoding} 編碼讀取文字文件")
                    return content
            except UnicodeDecodeError:
                continue
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()
        return content
    @staticmethod
    def _extract_from_csv(file_path: str) -> str:
        encodings = ['utf-8', 'utf-8-sig', 'big5', 'gbk', 'gb2312', 'latin1']
        for encoding in encodings:
            try:
                with open(file_path, 'r', encoding=encoding, newline='') as f:
                    reader = csv.reader(f)
                    rows = []
                    for row in reader:
                        if any(cell.strip() for cell in row):
                            rows.append(" | ".join(row))
                    if rows:
                        return "\n".join(rows)
            except Exception:
                continue
        return DocumentProcessor._extract_from_txt(file_path)
    @staticmethod
    def _clean_structured_data(text: str) -> Optional[str]:
        """
        智慧識別並清洗 JS/JSON 格式的設定或資料清單 (如 const posts = [...])，
        過濾掉巨大 SVG、HTML 樣式與 Base64 等干擾噪音，重構為高密度語意文字。
        """
        import re
        match = re.search(r'(?:const|let|var|module\.exports\s*=)\s*\w*\s*=?\s*(\[\s*\{[\s\S]*\}\s*\]|\{\s*\"[\s\S]*\"\s*:\s*[\s\S]*\});?', text)
        raw_json = match.group(1) if match else text.strip()
        
        try:
            data = json.loads(raw_json)
        except Exception:
            return None
        if isinstance(data, list):
            clean_lines = []
            noise_keys = {'embedcode', 'svg', 'icon', 'rawhtml', 'path', 'base64', 'style', 'imagedata', 'svgdata'}
            
            for idx, item in enumerate(data):
                if isinstance(item, dict):
                    parts = []
                    author = item.get('author') or item.get('user') or item.get('name') or item.get('title')
                    content = item.get('content') or item.get('text') or item.get('message') or item.get('desc') or item.get('description')
                    link = item.get('postLink') or item.get('link') or item.get('url')
                    tags = item.get('tags') or item.get('categories')
                    if author:
                        parts.append(f"作者: {author}")
                    if content:
                        parts.append(f"內容: {content}")
                    if link:
                        parts.append(f"連結: {link}")
                    if tags:
                        tags_str = ', '.join(tags) if isinstance(tags, list) else str(tags)
                        parts.append(f"標籤: {tags_str}")
                    
                    for k, v in item.items():
                        if k.lower() in noise_keys:
                            continue
                        if k in ('author', 'user', 'name', 'title', 'content', 'text', 'message', 'desc', 'description', 'postLink', 'link', 'url', 'tags', 'categories'):
                            continue
                        if isinstance(v, str):
                            if v.startswith('<blockquote') or v.startswith('<svg') or (len(v) > 500 and ('<path' in v or 'data:image' in v)):
                                continue
                            if v.strip():
                                parts.append(f"{k}: {v.strip()}")
                        elif v is not None and not isinstance(v, (dict, list)):
                            parts.append(f"{k}: {v}")
                    if parts:
                        clean_lines.append(f"【記錄 {idx + 1}】\n" + "\n".join(parts))
                elif isinstance(item, str) and item.strip():
                    clean_lines.append(item.strip())
            if clean_lines:
                logger.info(f"結構化資料降噪解析成功: 從陣列提取出 {len(clean_lines)} 條語意記錄")
                return "\n\n---\n\n".join(clean_lines)
        elif isinstance(data, dict):
            clean_lines = []
            for k, v in data.items():
                if isinstance(v, str) and len(v) < 2000 and not v.startswith('<svg'):
                    clean_lines.append(f"{k}: {v}")
                elif isinstance(v, (int, float, bool)):
                    clean_lines.append(f"{k}: {v}")
            if clean_lines:
                return "\n".join(clean_lines)
        return None
    @staticmethod
    def split_structured_records(content: str) -> list:
        import re
        if not content or not content.strip():
            return []
        if "【記錄 " in content and "---" in content:
            raw_records = re.split(r'\n+(?:---|___|\*\*\*)\n+', content)
            records = []
            for rc in raw_records:
                rc_clean = rc.strip()
                if not rc_clean:
                    continue
                meta = {}
                author_m = re.search(r'作者:\s*(@?[^\n]+)', rc_clean)
                if author_m:
                    meta["author"] = author_m.group(1).strip()
                link_m = re.search(r'連結:\s*(https?://[^\s\n]+)', rc_clean)
                if link_m:
                    meta["link"] = link_m.group(1).strip()
                rec_m = re.search(r'【記錄\s*(\d+)】', rc_clean)
                if rec_m:
                    meta["record_index"] = int(rec_m.group(1))
                tags_m = re.search(r'標籤:\s*([^\n]+)', rc_clean)
                if tags_m:
                    meta["tags"] = tags_m.group(1).strip()
                records.append((rc_clean, meta))
            if records:
                return records
        trimmed = content.strip()
        if (trimmed.startswith("[") and trimmed.endswith("]")) or (trimmed.startswith("{") and trimmed.endswith("}")):
            try:
                data = json.loads(trimmed)
                if isinstance(data, list):
                    records = []
                    noise_keys = {'embedcode', 'svg', 'icon', 'rawhtml', 'path', 'base64', 'style', 'imagedata', 'svgdata'}
                    for idx, item in enumerate(data):
                        if isinstance(item, dict):
                            parts = []
                            meta = {"record_index": idx + 1}
                            author = item.get('author') or item.get('user') or item.get('name') or item.get('title')
                            text_body = item.get('content') or item.get('text') or item.get('message') or item.get('desc') or item.get('description')
                            link = item.get('postLink') or item.get('link') or item.get('url')
                            tags = item.get('tags') or item.get('categories')
                            if author:
                                parts.append(f"作者: {author}")
                                meta["author"] = str(author)
                            if text_body:
                                parts.append(f"內容: {text_body}")
                            if link:
                                parts.append(f"連結: {link}")
                                meta["link"] = str(link)
                            if tags:
                                tags_str = ', '.join(tags) if isinstance(tags, list) else str(tags)
                                parts.append(f"標籤: {tags_str}")
                                meta["tags"] = tags_str
                            for k, v in item.items():
                                if k.lower() in noise_keys:
                                    continue
                                if k in ('author', 'user', 'name', 'title', 'content', 'text', 'message', 'desc', 'description', 'postLink', 'link', 'url', 'tags', 'categories'):
                                    continue
                                if isinstance(v, str):
                                    if v.startswith('<blockquote') or v.startswith('<svg') or (len(v) > 500 and ('<path' in v or 'data:image' in v)):
                                        continue
                                    if v.strip():
                                        parts.append(f"{k}: {v.strip()}")
                                elif v is not None and not isinstance(v, (dict, list)):
                                    parts.append(f"{k}: {v}")
                            if parts:
                                chunk_text = f"【記錄 {idx + 1}】\n" + "\n".join(parts)
                                records.append((chunk_text, meta))
                    if records:
                        return records
                elif isinstance(data, dict):
                    records = []
                    for k, v in data.items():
                        if isinstance(v, (dict, list)):
                            val_str = json.dumps(v, ensure_ascii=False, indent=2)
                        else:
                            val_str = str(v)
                        chunk_text = f"【設定模組: {k}】\n{val_str}"
                        records.append((chunk_text, {"json_key": str(k)}))
                    if records:
                        return records
            except Exception:
                pass
        return []
    @staticmethod
    def _extract_from_code_or_data(file_path: str, ext: str) -> str:
        raw_text = DocumentProcessor._extract_from_txt(file_path)
        
        cleaned = DocumentProcessor._clean_structured_data(raw_text)
        if cleaned:
            return cleaned
        
        import re
        cleaned_code = re.sub(r'data:image\/[a-zA-Z]+;base64,[a-zA-Z0-9+/=]{100,}', '[BASE64_IMAGE_OMITTED]', raw_text)
        cleaned_code = re.sub(r'<svg[\s\S]*?<\/svg>', '[SVG_ICON_OMITTED]', cleaned_code)
        return cleaned_code
    @staticmethod
    def _extract_from_html(file_path: str) -> str:
        raw_text = DocumentProcessor._extract_from_txt(file_path)
        try:
            parser = _HTMLTextExtractor()
            parser.feed(raw_text)
            extracted = parser.get_text()
            if extracted:
                return extracted
        except Exception as e:
            logger.warning(f"HTML 解析失敗，改為純文字讀取: {e}")
        return raw_text
    
    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        from app.services.pdf_service import PDFService
        return PDFService.extract_text_robust(file_path)
    
    @staticmethod
    def _extract_from_docx(file_path: str) -> str:
        doc = DocxDocument(file_path)
        text_content = []
        
        for paragraph in doc.paragraphs:
            if paragraph.text.strip():
                text_content.append(paragraph.text)
        
        for table in doc.tables:
            for row in table.rows:
                row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                if row_text:
                    text_content.append(" | ".join(row_text))
        
        if not text_content:
            raise ValueError("DOCX 文件中沒有可提取的文本內容")
        
        full_text = "\n".join(text_content)
        logger.info(f"成功從 DOCX 提取 {len(doc.paragraphs)} 個段落和 {len(doc.tables)} 個表格，共 {len(full_text)} 字符")
        return full_text
    @staticmethod
    def _extract_from_pptx(file_path: str) -> str:
        prs = Presentation(file_path)
        slides_text = []
        for idx, slide in enumerate(prs.slides):
            slide_lines = [f"--- 投影片 {idx + 1} ---"]
            for shape in slide.shapes:
                if shape.has_text_frame:
                    for paragraph in shape.text_frame.paragraphs:
                        text = paragraph.text.strip()
                        if text:
                            slide_lines.append(text)
                elif shape.has_table:
                    for row in shape.table.rows:
                        row_cells = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_cells:
                            slide_lines.append(" | ".join(row_cells))
            if len(slide_lines) > 1:
                slides_text.append("\n".join(slide_lines))
        
        if not slides_text:
            raise ValueError("PPTX 文件中沒有可提取的文本內容")
        
        full_text = "\n\n".join(slides_text)
        logger.info(f"成功從 PPTX 提取 {len(prs.slides)} 頁投影片，共 {len(full_text)} 字符")
        return full_text
    @staticmethod
    def _extract_from_xlsx(file_path: str) -> str:
        wb = openpyxl.load_workbook(file_path, data_only=True)
        sheets_text = []
        for sheetname in wb.sheetnames:
            sheet = wb[sheetname]
            sheet_lines = [f"--- 工作表: {sheetname} ---"]
            for row in sheet.iter_rows(values_only=True):
                if any(cell is not None and str(cell).strip() != "" for cell in row):
                    row_str = [str(c).strip() if c is not None else "" for c in row]
                    sheet_lines.append(" | ".join(row_str))
            if len(sheet_lines) > 1:
                sheets_text.append("\n".join(sheet_lines))
        
        if not sheets_text:
            raise ValueError("XLSX 文件中沒有可提取的文本內容")
        
        full_text = "\n\n".join(sheets_text)
        logger.info(f"成功從 XLSX 提取 {len(wb.sheetnames)} 個工作表，共 {len(full_text)} 字符")
        return full_text
    
    @staticmethod
    def validate_file_type(content_type: str, file_path: str = None) -> bool:
        if content_type in DocumentProcessor.FILE_SIGNATURES:
            return True
        if file_path:
            ext = os.path.splitext(file_path)[1].lower()
            if ext in DocumentProcessor.SUPPORTED_EXTENSIONS:
                return True
        return False
    
    @staticmethod
    def get_file_info(file_path: str, content_type: str) -> dict:
        try:
            stat = os.stat(file_path)
            return {
                "file_size": stat.st_size,
                "content_type": content_type,
                "is_supported": DocumentProcessor.validate_file_type(content_type, file_path)
            }
        except Exception as e:
            logger.error(f"獲取文件信息時發生錯誤: {e}")
            return {"error": str(e)}
    @classmethod
    async def generate_document_summary_async(cls, filename: str, content: str, file_type: str = "") -> str:
        """
        使用 LLM 智能生成專業、結構化、流暢且具高資訊密度的繁體中文「文件主題與大綱摘要」。
        若 LLM 呼叫超時或發生異常，自動降級調用高品質的啟發式規則分析器。
        """
        if not content or not content.strip():
            return f"收錄內部文件《{filename}》。"
        stripped = content.strip()
        if len(stripped) <= 2800:
            sample_content = stripped
        else:
            first_part = stripped[:1500]
            mid_start = max(0, (len(stripped) // 2) - 400)
            mid_part = stripped[mid_start:mid_start + 800]
            last_part = stripped[-500:]
            sample_content = f"{first_part}\n\n[...中略...]\n\n{mid_part}\n\n[...下略...]\n\n{last_part}"
        prompt = (
            "你是一個頂級的知識庫文件分析與大綱生成專家。請根據以下文件的檔名與內文摘錄，"
            "產出一份高水準、專業、客觀且條理分明的「文件主題與大綱摘要」（繁體中文，約 70~150 字）。\n\n"
            "【嚴格準則】\n"
            "1. 核心定位：準確指明文件類型與核心主題（例如：產品規格說明書、宣傳型錄DM、LINE工作討論紀錄、社群貼文資料集、技術手冊等）。\n"
            "2. 內容大綱：提煉出主要涵蓋的章節、核心架構、功能特色或討論焦點。\n"
            "3. 噪音過濾：嚴格禁止將通訊對話人名/任務待辦（如「1. @某某」）、純頁碼、版權宣告或公司電話地址誤當作章節標題。\n"
            "4. 輸出要求：請直接輸出摘要文字本身，語句通順精煉，嚴禁客套話或前言標籤。\n\n"
            f"【文件檔名】{filename}\n"
            f"【文件類型】{file_type}\n"
            f"【內容摘錄】\n{sample_content}"
        )
        try:
            from app.core.llm_client import call_llm
            response = await call_llm(
                messages=[{"role": "user", "content": prompt}],
                timeout=18.0
            )
            cleaned = response.strip()
            for prefix in ("好的，", "這是該文件的摘要：", "這是一份", "文件摘要：", "摘要：", "以下是"):
                if cleaned.startswith(prefix) and len(cleaned) > len(prefix) + 10:
                    cleaned = cleaned[len(prefix):].strip()
            if cleaned and len(cleaned) >= 20:
                return cleaned
        except Exception as e:
            logger.warning(f"使用 LLM 生成文件大綱摘要失敗 ({e})，切換至規則解析器降級處理")
        return cls._generate_fallback_summary(filename, content, file_type)
    @classmethod
    def generate_document_summary(cls, filename: str, content: str, file_type: str = "") -> str:
        """
        同步調用封裝（若無事件迴圈則執行 LLM 生成，否則安全使用啟發式解析避免阻塞）
        """
        if not content or not content.strip():
            return f"收錄內部文件《{filename}》。"
        try:
            import asyncio
            try:
                loop = asyncio.get_running_loop()
            except RuntimeError:
                loop = None
            if loop and loop.is_running():
                return cls._generate_fallback_summary(filename, content, file_type)
            else:
                return asyncio.run(cls.generate_document_summary_async(filename, content, file_type))
        except Exception:
            return cls._generate_fallback_summary(filename, content, file_type)
    @classmethod
    def _generate_fallback_summary(cls, filename: str, content: str, file_type: str = "") -> str:
        """高品質啟發式規則分析器"""
        import re
        if not content or not content.strip():
            return f"收錄內部文件《{filename}》。"
        raw_lines = [line.strip() for line in content.strip().splitlines() if line.strip()]
        if not raw_lines:
            return f"收錄內部文件《{filename}》。"
        record_count = content.count("【記錄 ")
        if record_count > 0:
            first_block = content[:1500]
            fields = []
            for field_name in ["作者", "內容", "連結", "標籤", "時間", "標題", "狀態", "金額", "說明"]:
                if f"{field_name}:" in first_block or f"{field_name}：" in first_block:
                    fields.append(field_name)
            fields_str = "、".join(fields) if fields else "多項屬性欄位"
            return f"收錄約 {record_count} 筆結構化社群/資料記錄（包含欄位：{fields_str}），支援依據作者帳號、內容文字、特定網址 URL 與主題標籤進行精準檢索。"
        header_preview = content[:2500]
        is_line_file = filename.startswith('[LINE]') or '對話' in filename or '通訊' in filename
        line_date_matches = len(re.findall(r'\d{4}[./-]\d{2}[./-]\d{2}\s+(?:星期|週|Mon|Tue|Wed|Thu|Fri|Sat|Sun)', header_preview))
        chat_time_user_matches = len(re.findall(r'\n\d{1,2}:\d{2}\s+[\u4e00-\u9fa5a-zA-Z0-9_]{2,12}', header_preview))
        
        if is_line_file or (line_date_matches >= 1 and chat_time_user_matches >= 2):
            members = set(re.findall(r'\n\d{1,2}:\d{2}\s+([\u4e00-\u9fa5a-zA-Z0-9_]{2,10})', header_preview))
            members_filtered = [m for m in members if m not in ('All', '收到', '好的', '已預借', '已新增', '二位') and not m.isdigit()][:5]
            members_str = '、'.join(members_filtered) if members_filtered else '專案團隊成員'
            
            topics = []
            for kw in ('Agent', '建置', '部署', 'OpenClaude', 'Open Data', '會議', '簡報', '教育', '測試', '研發', '進度'):
                if kw in content and kw not in topics:
                    topics.append(kw)
            topic_str = '、'.join(topics[:5]) if topics else '專案工作事項'
            return f"本文件為內部通訊工作討論紀錄（參與人員包括：{members_str}），主要聚焦討論 {topic_str} 等相關任務與進度追蹤。"
        cleaned_lines = []
        noise_prefixes = ("---", "[", ">", "http://", "https://", "www.", "tel:", "fax:", "email:", "@")
        for line in raw_lines:
            line_str = line.strip()
            if any(line_str.startswith(np) for np in noise_prefixes):
                continue
            if re.search(r'^(?:mitac|copyright|all rights reserved|\(02\)|www\.)', line_str, re.IGNORECASE):
                continue
            if line_str in ("[本頁為圖檔或無可提取純文字]", "[SVG_ICON_OMITTED]", "[BASE64_IMAGE_OMITTED]"):
                continue
            cleaned_lines.append(line_str)
        if not cleaned_lines:
            return f"收錄內部文件《{filename}》。"
        def clean_toc_line(text: str) -> str:
            cleaned = text.lstrip("#*- •\t ")
            cleaned = re.sub(r'[\.\·\s\_]{3,}\s*\d*$', '', cleaned).strip()
            cleaned = re.sub(r'^(?:[0-9]+(?:\.[0-9]+)*\.?|[一二三四五六七八九十]+[、\.]|第[0-9一二三四五六七八九十]+[章節點條項篇]|【[^】]+】)\s*', '', cleaned).strip()
            return re.sub(r'\s+', ' ', cleaned)
        headers = []
        for line in cleaned_lines[:120]:
            cleaned_h = clean_toc_line(line)
            if len(cleaned_h) < 3 or len(cleaned_h) > 35:
                continue
            if re.search(r'^(?:第[0-9一二三四五六七八九十]+[章篇]|(?:[0-9]+|[一二三四五六七八九十]+)[、\.])\s*[^\d]', line):
                if cleaned_h not in headers:
                    headers.append(cleaned_h)
            elif line.startswith('#'):
                if cleaned_h not in headers:
                    headers.append(cleaned_h)
        title_cand = filename.rsplit('.', 1)[0]
        if headers:
            top_headers = headers[:5]
            headers_str = '、'.join(top_headers)
            return f"本文件為《{title_cand}》，核心涵蓋章節與重點包括：{headers_str} 等專業內容。"
        if "," in cleaned_lines[0] or "\t" in cleaned_lines[0] or "|" in cleaned_lines[0]:
            cols = [c.strip() for c in cleaned_lines[0].replace("|", ",").split(",") if c.strip()]
            if len(cols) >= 2:
                cols_str = "、".join(cols[:8])
                return f"結構化表格數據，收錄約 {len(cleaned_lines) - 1} 筆資料，包含欄位：{cols_str}。"
        snippet = " ".join(cleaned_lines[:4])[:120].replace("  ", " ")
        return f"本文件為《{title_cand}》，重點收錄：{snippet}...等內部專業資料。"