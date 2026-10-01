import { deleteRequest, errorMessageOf, fetchDoctors, postJson } from '../api';
import type { PromptListItem, PromptResponse } from '../types';
import { consumeQueryFlag, formatDateTime, getSortIcon, sortRows, toggleSort } from '../utils';
import type { SortState } from '../utils';

interface PromptForm {
    department: string;
    doctor: string;
    documentType: string;
    selectedModel: string;
    content: string;
}

// プロンプトを保存し、成功したら redirectTo へ遷移する。失敗時はエラーメッセージを返す
// （新規作成と編集で共通。サーバー側は診療科・文書タイプ・医師の組で作成か更新かを判定する）
async function submitPrompt(form: PromptForm, redirectTo: string, fallbackError: string): Promise<string | null> {
    try {
        const response = await postJson('/api/prompts/', {
            department: form.department,
            doctor: form.doctor,
            document_type: form.documentType,
            selected_model: form.selectedModel || null,
            content: form.content
        });
        if (!response.ok) {
            return await errorMessageOf(response, fallbackError);
        }
        window.location.href = redirectTo;
        return null;
    } catch {
        return window.MESSAGES.ERROR.API_ERROR;
    }
}

interface PromptsPage {
    prompts: PromptListItem[];
    filteredPrompts: PromptListItem[];
    doctors: string[];
    filter: { department: string; doctor: string; documentType: string };
    isLoading: boolean;
    error: string | null;
    successMessage: string | null;
    sort: SortState;
    init(): Promise<void>;
    updateDoctors(): Promise<void>;
    loadPrompts(): Promise<void>;
    applyFilters(): void;
    deletePrompt(promptId: number): Promise<void>;
    formatDate(dateStr: string | null): string;
    sortPrompts(column: string): void;
    getSortIcon(column: string): string;
}

// プロンプト一覧ページ
export function promptsPage(): PromptsPage {
    return {
        prompts: [],
        filteredPrompts: [],
        doctors: ['default'],
        filter: {
            department: 'default',
            doctor: 'default',
            documentType: window.DOCUMENT_TYPES[0]
        },
        isLoading: false,
        error: null,
        successMessage: null,
        sort: { column: '', direction: 'asc' },

        async init() {
            this.successMessage = consumeQueryFlag({
                created: window.MESSAGES.SUCCESS.PROMPT_CREATED,
                updated: window.MESSAGES.SUCCESS.PROMPT_UPDATED,
                deleted: window.MESSAGES.SUCCESS.PROMPT_DELETED
            });
            await this.updateDoctors();
            await this.loadPrompts();
        },

        async updateDoctors() {
            // 診療科が「すべて」の場合は医師を絞り込めない
            if (!this.filter.department) {
                this.doctors = ['default'];
                return;
            }
            try {
                this.doctors = await fetchDoctors(this.filter.department);
                if (this.filter.doctor && !this.doctors.includes(this.filter.doctor)) {
                    this.filter.doctor = '';
                }
            } catch {
                this.doctors = ['default'];
            }
        },

        async loadPrompts() {
            this.isLoading = true;
            this.error = null;
            try {
                const response = await fetch('/api/prompts/');
                this.prompts = await response.json() as PromptListItem[];
                this.applyFilters();
            } catch {
                this.error = window.MESSAGES.ERROR.PROMPT_LOAD_FAILED;
            } finally {
                this.isLoading = false;
            }
        },

        applyFilters() {
            this.filteredPrompts = this.prompts.filter(p => {
                if (this.filter.department && p.department !== this.filter.department) return false;
                if (this.filter.doctor && p.doctor !== this.filter.doctor) return false;
                if (this.filter.documentType && p.document_type !== this.filter.documentType) return false;
                return true;
            });
        },

        async deletePrompt(promptId: number) {
            if (!confirm(window.MESSAGES.CONFIRM.DELETE_PROMPT)) return;

            try {
                const response = await deleteRequest(`/api/prompts/${promptId}`);
                if (response.ok) {
                    this.successMessage = window.MESSAGES.SUCCESS.PROMPT_DELETED;
                    await this.loadPrompts();
                } else {
                    this.error = await errorMessageOf(response, window.MESSAGES.ERROR.PROMPT_DELETE_FAILED);
                }
            } catch {
                this.error = window.MESSAGES.ERROR.API_ERROR;
            }
        },

        formatDate(dateStr: string | null): string {
            return formatDateTime(dateStr);
        },

        sortPrompts(column: string) {
            toggleSort(this.sort, column);
            sortRows(this.filteredPrompts, this.sort, ['updated_at']);
        },

        getSortIcon(column: string): string {
            return getSortIcon(this.sort, column);
        }
    };
}

interface PromptNewPage {
    form: PromptForm;
    doctors: string[];
    isSaving: boolean;
    error: string | null;
    init(): Promise<void>;
    updateDoctors(): Promise<void>;
    savePrompt(): Promise<void>;
}

// プロンプト新規作成ページ
export function promptNewPage(): PromptNewPage {
    return {
        form: {
            department: 'default',
            doctor: 'default',
            documentType: window.DOCUMENT_TYPES[0],
            selectedModel: '',
            content: ''
        },
        doctors: ['default'],
        isSaving: false,
        error: null,

        async init() {
            await this.updateDoctors();
        },

        async updateDoctors() {
            try {
                this.doctors = await fetchDoctors(this.form.department);
                if (!this.doctors.includes(this.form.doctor)) {
                    this.form.doctor = this.doctors[0];
                }
            } catch {
                this.doctors = ['default'];
            }
        },

        async savePrompt() {
            if (!this.form.department || !this.form.doctor || !this.form.documentType || !this.form.content.trim()) {
                this.error = window.MESSAGES.VALIDATION.ALL_REQUIRED_FIELDS;
                return;
            }

            this.isSaving = true;
            this.error = await submitPrompt(
                this.form, '/prompts?created=1', window.MESSAGES.ERROR.PROMPT_CREATE_FAILED
            );
            this.isSaving = false;
        }
    };
}

interface PromptEditPage {
    promptId: number;
    form: PromptForm;
    isLoading: boolean;
    isSaving: boolean;
    error: string | null;
    loadError: string | null;
    init(): Promise<void>;
    loadPrompt(): Promise<void>;
    updatePrompt(): Promise<void>;
    deletePrompt(): Promise<void>;
}

// プロンプト編集ページ
export function promptEditPage(promptId: number): PromptEditPage {
    return {
        promptId,
        form: {
            department: '',
            doctor: '',
            documentType: '',
            selectedModel: '',
            content: ''
        },
        isLoading: true,
        isSaving: false,
        error: null,
        loadError: null,

        async init() {
            await this.loadPrompt();
        },

        async loadPrompt() {
            this.isLoading = true;
            this.loadError = null;

            try {
                const response = await fetch(`/api/prompts/${this.promptId}`);
                if (response.ok) {
                    const data = await response.json() as PromptResponse;
                    this.form = {
                        department: data.department,
                        doctor: data.doctor,
                        documentType: data.document_type,
                        selectedModel: data.selected_model || '',
                        content: data.content
                    };
                } else if (response.status === 404) {
                    this.loadError = window.MESSAGES.ERROR.PROMPT_NOT_FOUND;
                } else {
                    this.loadError = window.MESSAGES.ERROR.PROMPT_LOAD_FAILED;
                }
            } catch {
                this.loadError = window.MESSAGES.ERROR.API_ERROR;
            } finally {
                this.isLoading = false;
            }
        },

        async updatePrompt() {
            if (!this.form.content.trim()) {
                this.error = window.MESSAGES.VALIDATION.PROMPT_CONTENT_REQUIRED;
                return;
            }

            this.isSaving = true;
            this.error = await submitPrompt(
                this.form, '/prompts?updated=1', window.MESSAGES.ERROR.PROMPT_UPDATE_FAILED
            );
            this.isSaving = false;
        },

        async deletePrompt() {
            if (!confirm(window.MESSAGES.CONFIRM.DELETE_PROMPT)) return;

            this.isSaving = true;
            this.error = null;

            try {
                const response = await deleteRequest(`/api/prompts/${this.promptId}`);
                if (response.ok) {
                    window.location.href = '/prompts?deleted=1';
                } else {
                    this.error = await errorMessageOf(response, window.MESSAGES.ERROR.PROMPT_DELETE_FAILED);
                }
            } catch {
                this.error = window.MESSAGES.ERROR.API_ERROR;
            } finally {
                this.isSaving = false;
            }
        }
    };
}
