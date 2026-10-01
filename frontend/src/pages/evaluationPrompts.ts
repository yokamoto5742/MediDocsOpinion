import { deleteRequest, errorMessageOf, postJson } from '../api';
import type { EvaluationPromptResponse, EvaluationPromptSaveResponse } from '../types';
import { consumeQueryFlag, formatDateTime } from '../utils';

interface EvaluationPromptsPage {
    prompts: EvaluationPromptResponse[];
    documentTypes: string[];
    isLoading: boolean;
    error: string | null;
    successMessage: string | null;
    init(): Promise<void>;
    loadPrompts(): Promise<void>;
    getPrompt(docType: string): EvaluationPromptResponse | undefined;
    hasPrompt(docType: string): boolean;
    getPromptPreview(docType: string): string;
    getUpdatedAt(docType: string): string;
    deletePrompt(docType: string): Promise<void>;
}

// 評価プロンプト一覧ページ（文書タイプごとに1件）
export function evaluationPromptsPage(): EvaluationPromptsPage {
    return {
        prompts: [],
        documentTypes: window.DOCUMENT_TYPES,
        isLoading: false,
        error: null,
        successMessage: null,

        async init() {
            this.successMessage = consumeQueryFlag({
                saved: window.MESSAGES.SUCCESS.PROMPT_SAVED,
                deleted: window.MESSAGES.SUCCESS.PROMPT_DELETED
            });
            await this.loadPrompts();
        },

        async loadPrompts() {
            this.isLoading = true;
            this.error = null;
            try {
                const response = await fetch('/api/evaluation/prompts');
                const data = await response.json() as { prompts?: EvaluationPromptResponse[] };
                this.prompts = data.prompts || [];
            } catch {
                this.error = window.MESSAGES.ERROR.PROMPT_LOAD_FAILED;
            } finally {
                this.isLoading = false;
            }
        },

        getPrompt(docType: string) {
            return this.prompts.find(p => p.document_type === docType);
        },

        hasPrompt(docType: string): boolean {
            return !!this.getPrompt(docType);
        },

        getPromptPreview(docType: string): string {
            const content = this.getPrompt(docType)?.content;
            if (!content) return '未設定';
            return content.length > 50 ? content.substring(0, 50) + '...' : content;
        },

        getUpdatedAt(docType: string): string {
            return formatDateTime(this.getPrompt(docType)?.updated_at);
        },

        async deletePrompt(docType: string) {
            const confirmMessage = window.MESSAGES.CONFIRM.DELETE_EVALUATION_PROMPT.replace('{document_type}', docType);
            if (!confirm(confirmMessage)) return;

            try {
                const response = await deleteRequest(`/api/evaluation/prompts/${encodeURIComponent(docType)}`);
                if (!response.ok) {
                    this.error = await errorMessageOf(response, window.MESSAGES.ERROR.EVALUATION_PROMPT_DELETE_FAILED);
                    return;
                }
                const data = await response.json() as EvaluationPromptSaveResponse;
                if (data.success) {
                    this.successMessage = data.message;
                    await this.loadPrompts();
                } else {
                    this.error = data.message || window.MESSAGES.ERROR.EVALUATION_PROMPT_DELETE_FAILED;
                }
            } catch {
                this.error = window.MESSAGES.ERROR.API_ERROR;
            }
        }
    };
}

interface EvaluationPromptEditPage {
    documentType: string;
    content: string;
    isSaving: boolean;
    error: string | null;
    init(): Promise<void>;
    loadPrompt(): Promise<void>;
    savePrompt(): Promise<void>;
}

// 評価プロンプト編集ページ
export function evaluationPromptEditPage(documentType: string): EvaluationPromptEditPage {
    return {
        documentType,
        content: '',
        isSaving: false,
        error: null,

        async init() {
            await this.loadPrompt();
        },

        async loadPrompt() {
            try {
                const response = await fetch(`/api/evaluation/prompts/${encodeURIComponent(this.documentType)}`);
                const data = await response.json() as EvaluationPromptResponse;
                if (data.content) {
                    this.content = data.content;
                }
            } catch {
                this.error = window.MESSAGES.ERROR.EVALUATION_PROMPT_LOAD_FAILED;
            }
        },

        async savePrompt() {
            if (!this.content.trim()) {
                this.error = window.MESSAGES.VALIDATION.PROMPT_CONTENT_REQUIRED;
                return;
            }

            this.isSaving = true;
            this.error = null;

            try {
                const response = await postJson('/api/evaluation/prompts', {
                    document_type: this.documentType,
                    content: this.content
                });
                if (!response.ok) {
                    this.error = await errorMessageOf(response, window.MESSAGES.ERROR.EVALUATION_PROMPT_SAVE_FAILED);
                    return;
                }
                const data = await response.json() as EvaluationPromptSaveResponse;
                if (data.success) {
                    window.location.href = '/evaluation-prompts?saved=1';
                } else {
                    this.error = data.message || window.MESSAGES.ERROR.EVALUATION_PROMPT_SAVE_FAILED;
                }
            } catch {
                this.error = window.MESSAGES.ERROR.API_ERROR;
            } finally {
                this.isSaving = false;
            }
        }
    };
}
