import { Message, Conversation } from '../../services/api';
export interface SourceDetail {
  source: string;
  chunk?: number;
  score?: number | null;
  snippet?: string;
  url?: string;
}
export interface ResearchTraceStep {
  step: number;
  tool: string;
  arguments?: Record<string, any>;
  output_preview?: string;
  duration_seconds?: number;
  status?: 'success' | 'error' | string;
}
export interface ModelDetail {
  name: string;
  description?: string;
  context_window?: number;
  pricing?: string;
}
export interface SnackbarState {
  open: boolean;
  message: string;
  severity: 'success' | 'info' | 'warning' | 'error';
}
export type ReasoningEffort = 'none' | 'low' | 'medium' | 'high' | 'xhigh';
export interface ChatHeaderProps {
  availableModels: string[];
  selectedModel: string;
  onSelectModel: (model: string) => void;
  reasoningEffort: string;
  onSelectReasoningEffort: (effort: string) => void;
  modelsLoading: boolean;
  onRefreshModels: () => void;
  currentConversation: Conversation | null;
  onOpenSidebar?: () => void;
}
export interface ChatSidebarProps {
  open: boolean;
  onClose: () => void;
  conversations: Conversation[];
  currentConversation: Conversation | null;
  onSelectConversation: (id: number) => void;
  onNewConversation: () => void;
  onDeleteConversation: (id: number) => void;
  loading: boolean;
}
export interface ChatMessageItemProps {
  message: Message;
  isThinkingOpen: boolean;
  onToggleThinking: () => void;
  onCopyMessage: (text: string) => void;
}
export interface ChatMessageListProps {
  messages: Message[];
  loading: boolean;
  loadingMore: boolean;
  hasMoreMessages: boolean;
  onLoadMore: () => void;
  thinkOpenArr: Record<number | string, boolean>;
  onToggleThinking: (id: number | string) => void;
  onCopyMessage: (text: string) => void;
  onSelectPrompt?: (prompt: string) => void;
  messagesEndRef: React.RefObject<HTMLDivElement | null>;
  messagesTopRef: React.RefObject<HTMLDivElement | null>;
}
export type { ChatAttachment } from '../../services/api';
import type { ChatAttachment } from '../../services/api';
export interface ChatInputAreaProps {
  value: string;
  onChange: (val: string) => void;
  onSend: () => void;
  loading: boolean;
  disabled?: boolean;
  attachments?: ChatAttachment[];
  onAddAttachments?: (attachments: ChatAttachment[]) => void;
  onRemoveAttachment?: (index: number) => void;
}
export interface SourceBadgesProps {
  sources?: string[];
  sourcesDetail?: SourceDetail[];
}
export interface ThinkBlockProps {
  thinkContent: string;
  isOpen: boolean;
  onToggle: () => void;
}
export interface ResearchTraceBlockProps {
  trace: ResearchTraceStep[];
}
