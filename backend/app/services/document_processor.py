#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
from typing import Optional
from pypdf import PdfReader  # 使用新的 pypdf 替代 PyPDF2
from docx import Document as DocxDocument
import logging
import hashlib

logger = logging.getLogger(__name__)

class DocumentProcessor:
    """文檔處理器，支援 TXT、PDF 和 DOCX 格式，並增強安全性"""
    
    # 檔案頭部 magic numbers 用於驗證
    FILE_SIGNATURES = {
        'application/pdf': [b'%PDF'],
        'application/vnd.openxmlformats-officedocument.wordprocessingml.document': [
            b'PK\x03\x04',  # ZIP 格式（DOCX 是壓縮檔）
        ],
        'text/plain': []  # 文本文件沒有特定的 magic number
    }
    
    @staticmethod
    def validate_file_header(file_path: str, content_type: str) -> bool:
        """
        驗證檔案頭部以確保檔案類型真實性
        
        Args:
            file_path: 檔案路徑
            content_type: 聲稱的 MIME 類型
            
        Returns:
            bool: 驗證是否通過
            
        Raises:
            ValueError: 如果驗證失敗
        """
        if content_type not in DocumentProcessor.FILE_SIGNATURES:
            raise ValueError(f"不支援的檔案類型: {content_type}")
        
        signatures = DocumentProcessor.FILE_SIGNATURES[content_type]
        
        # 文本文件跳過頭部檢查
        if not signatures:
            return True
        
        try:
            with open(file_path, 'rb') as f:
                header = f.read(512)  # 讀取前 512 bytes
                
            # 檢查是否匹配任何已知的 magic number
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
        """
        計算檔案的 SHA256 雜湊值
        
        Args:
            file_path: 檔案路徑
            
        Returns:
            str: SHA256 雜湊值
        """
        sha256_hash = hashlib.sha256()
        with open(file_path, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)
        return sha256_hash.hexdigest()
    
    @staticmethod
    def extract_text_from_file(file_path: str, content_type: str) -> Optional[str]:
        """從文件中提取文本內容，增強安全性"""
        try:
            # 安全檢查：驗證檔案頭部
            DocumentProcessor.validate_file_header(file_path, content_type)
            
            # 安全檢查：檔案大小（在這裡再次確認）
            file_size = os.path.getsize(file_path)
            max_size = int(os.getenv("MAX_FILE_SIZE_MB", "10")) * 1024 * 1024
            if file_size > max_size:
                raise ValueError(f"檔案大小 ({file_size} bytes) 超過限制")
            
            if content_type == "text/plain":
                return DocumentProcessor._extract_from_txt(file_path)
            elif content_type == "application/pdf":
                return DocumentProcessor._extract_from_pdf(file_path)
            elif content_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document":
                return DocumentProcessor._extract_from_docx(file_path)
            else:
                logger.warning(f"不支援的文件類型: {content_type}")
                return None
        except Exception as e:
            logger.error(f"提取文本時發生錯誤: {e}")
            raise
    
    @staticmethod
    def _extract_from_txt(file_path: str) -> str:
        """從 TXT 文件提取文本"""
        try:
            # 嘗試不同的編碼
            encodings = ['utf-8', 'utf-8-sig', 'big5', 'gb2312', 'gbk']
            
            for encoding in encodings:
                try:
                    with open(file_path, 'r', encoding=encoding) as f:
                        content = f.read()
                    logger.info(f"成功使用 {encoding} 編碼讀取 TXT 文件")
                    return content
                except UnicodeDecodeError:
                    continue
            
            # 如果所有編碼都失敗，使用錯誤處理
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            logger.warning("使用 UTF-8 with errors='ignore' 讀取 TXT 文件")
            return content
            
        except Exception as e:
            logger.error(f"讀取 TXT 文件時發生錯誤: {e}")
            raise
    
    @staticmethod
    def _extract_from_pdf(file_path: str) -> str:
        """從 PDF 文件提取文本"""
        try:
            text_content = []
            
            with open(file_path, 'rb') as file:
                pdf_reader = PdfReader(file)  # 使用新的 PdfReader
                
                # 檢查 PDF 是否被加密
                if pdf_reader.is_encrypted:
                    logger.warning("PDF 文件被加密，嘗試空密碼解密")
                    try:
                        pdf_reader.decrypt("")
                    except:
                        raise ValueError("PDF 文件被密碼保護，無法讀取")
                
                # 提取每一頁的文本
                for page_num, page in enumerate(pdf_reader.pages):
                    try:
                        page_text = page.extract_text()
                        if page_text.strip():
                            text_content.append(f"--- 第 {page_num + 1} 頁 ---\n{page_text}\n")
                    except Exception as e:
                        logger.warning(f"提取第 {page_num + 1} 頁時發生錯誤: {e}")
                        continue
                
                if not text_content:
                    raise ValueError("PDF 文件中沒有可提取的文本內容")
                
                full_text = "\n".join(text_content)
                logger.info(f"成功從 PDF 提取 {len(pdf_reader.pages)} 頁，共 {len(full_text)} 字符")
                return full_text
                
        except Exception as e:
            logger.error(f"讀取 PDF 文件時發生錯誤: {e}")
            raise
    
    @staticmethod
    def _extract_from_docx(file_path: str) -> str:
        """從 DOCX 文件提取文本"""
        try:
            doc = DocxDocument(file_path)
            text_content = []
            
            # 提取段落文本
            for paragraph in doc.paragraphs:
                if paragraph.text.strip():
                    text_content.append(paragraph.text)
            
            # 提取表格文本
            for table in doc.tables:
                for row in table.rows:
                    row_text = []
                    for cell in row.cells:
                        if cell.text.strip():
                            row_text.append(cell.text.strip())
                    if row_text:
                        text_content.append(" | ".join(row_text))
            
            if not text_content:
                raise ValueError("DOCX 文件中沒有可提取的文本內容")
            
            full_text = "\n".join(text_content)
            logger.info(f"成功從 DOCX 提取 {len(doc.paragraphs)} 個段落和 {len(doc.tables)} 個表格，共 {len(full_text)} 字符")
            return full_text
            
        except Exception as e:
            logger.error(f"讀取 DOCX 文件時發生錯誤: {e}")
            raise
    
    @staticmethod
    def validate_file_type(content_type: str) -> bool:
        """驗證文件類型是否支援"""
        supported_types = [
            "text/plain",
            "application/pdf", 
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        ]
        return content_type in supported_types
    
    @staticmethod
    def get_file_info(file_path: str, content_type: str) -> dict:
        """獲取文件基本信息"""
        try:
            stat = os.stat(file_path)
            return {
                "file_size": stat.st_size,
                "content_type": content_type,
                "is_supported": DocumentProcessor.validate_file_type(content_type)
            }
        except Exception as e:
            logger.error(f"獲取文件信息時發生錯誤: {e}")
            return {"error": str(e)}
