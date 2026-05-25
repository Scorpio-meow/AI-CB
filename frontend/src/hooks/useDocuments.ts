import { useState, useCallback } from 'react';
import { documentService } from '../services/api';

export interface DocumentInfo {
  id: number;
  filename: string;
  content: string;
  file_type: string;
  uploaded_by?: number;
  created_at: string;
  is_processed: boolean;
}

export function useDocuments() {
  const [documents, setDocuments] = useState<DocumentInfo[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const fetchDocuments = useCallback(async (): Promise<DocumentInfo[]> => {
    setLoading(true);
    setError(null);
    try {
      const data = await documentService.getDocuments();
      setDocuments(data);
      return data;
    } catch (err: any) {
      const errorMsg = err.message || '無法載入文件清單';
      setError(errorMsg);
      return [];
    } finally {
      setLoading(false);
    }
  }, []);

  const uploadDocument = useCallback(async (file: File): Promise<any> => {
    setLoading(true);
    setError(null);
    try {
      const data = await documentService.uploadDocument(file);
      await fetchDocuments();
      return data;
    } catch (err: any) {
      const errorMsg = err.message || '上傳文件失敗';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchDocuments]);

  const uploadDocuments = useCallback(async (files: File[]): Promise<any> => {
    setLoading(true);
    setError(null);
    try {
      const data = await documentService.uploadDocuments(files);
      await fetchDocuments();
      return data;
    } catch (err: any) {
      const errorMsg = err.message || '上傳多份文件失敗';
      setError(errorMsg);
      throw err;
    } finally {
      setLoading(false);
    }
  }, [fetchDocuments]);

  const deleteDocument = useCallback(async (documentId: number): Promise<boolean> => {
    setLoading(true);
    setError(null);
    try {
      await documentService.deleteDocument(documentId);
      setDocuments(prev => prev.filter(doc => doc.id !== documentId));
      return true;
    } catch (err: any) {
      setError(err.message || '刪除文件失敗');
      return false;
    } finally {
      setLoading(false);
    }
  }, []);

  return {
    documents,
    loading,
    error,
    fetchDocuments,
    uploadDocument,
    uploadDocuments,
    deleteDocument,
  };
}
export default useDocuments;
