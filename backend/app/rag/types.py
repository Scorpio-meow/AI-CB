from typing import Dict, Any, List, Optional

try:
    from langchain_core.documents import Document
except ImportError:
    class Document:
        def __init__(self, page_content: str = "", metadata: Optional[Dict[str, Any]] = None):
            self.page_content = page_content
            self.metadata = metadata if metadata is not None else {}

        def __repr__(self):
            preview = self.page_content[:30].replace("\n", " ")
            return f"Document(page_content='{preview}...', metadata={self.metadata})"

try:
    from langchain_text_splitters import RecursiveCharacterTextSplitter
except ImportError:
    class RecursiveCharacterTextSplitter:
        def __init__(
            self,
            chunk_size: int = 300,
            chunk_overlap: int = 100,
            separators: Optional[List[str]] = None,
            length_function=len
        ):
            self.chunk_size = chunk_size
            self.chunk_overlap = chunk_overlap
            self.separators = separators or ["\n\n", "。", "！", "？", "；", "：", "，", "\n", " ", ""]
            self.length_function = length_function

        def split_text(self, text: str) -> List[str]:
            if not text:
                return []
            chunks = []
            start = 0
            text_len = len(text)
            step = max(1, self.chunk_size - self.chunk_overlap)
            while start < text_len:
                end = min(start + self.chunk_size, text_len)
                chunk = text[start:end]
                if chunk.strip():
                    chunks.append(chunk)
                if end >= text_len:
                    break
                start += step
            return chunks
