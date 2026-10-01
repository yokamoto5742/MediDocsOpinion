import { errorMessageOf, fetchDoctors, getHeaders, postJson, readSSE } from './api';
import type {
    Settings,
    InputForm,
    GenerationResult,
    EvaluationResult,
    SelectedModelResponse,
    SSECompleteEvent,
    SSEErrorEvent,
    SSEEvaluationCompleteEvent
} from './types';

type ScreenType = 'input' | 'output' | 'evaluation';

interface AppState {
    settings: Settings;
    doctors: string[];
    form: InputForm;
    result: GenerationResult;
    isGenerating: boolean;
    elapsedTime: number;
    timerInterval: ReturnType<typeof setInterval> | null;
    showCopySuccess: boolean;
    error: string | null;
    activeTab: number;
    tabs: readonly string[];
    currentScreen: ScreenType;
    evaluationResult: EvaluationResult;
    isEvaluating: boolean;
    refinement: { previousSummary: string; evaluationFeedback: string };
    init(): Promise<void>;
    updateDoctors(): Promise<void>;
    updateSelectedModel(): Promise<void>;
    startTimer(): void;
    stopTimer(): void;
    runStream(url: string, body: Record<string, unknown>, onComplete: (data: unknown) => void): Promise<void>;
    buildGenerateRequestBody(): Record<string, unknown>;
    generateSummary(): Promise<void>;
    regenerateWithFeedback(): Promise<void>;
    clearForm(): void;
    backToInput(): void;
    backToOutput(): void;
    showEvaluation(): void;
    evaluateOutput(): Promise<void>;
    copyToClipboard(text: string): Promise<void>;
    getCurrentTabContent(): string;
    copyCurrentTab(): void;
    getTabClass(index: number): string;
}

function emptyResult(): GenerationResult {
    return {
        outputSummary: '',
        parsedSummary: {},
        processingTime: null,
        modelUsed: '',
        modelSwitched: false
    };
}

function emptyEvaluation(): EvaluationResult {
    return { result: '', processingTime: null };
}

export function appState(): AppState {
    return {
        // Settings
        settings: {
            department: 'default',
            doctor: 'default',
            documentType: window.DOCUMENT_TYPES[0],
            model: 'Claude'
        },
        doctors: ['default'],

        // Form
        form: {
            previousText: '',
            medicalText: '',
            additionalInfo: ''
        },

        // Result
        result: emptyResult(),

        // UI state（生成と評価は同時に走らないため、タイマーは共有する）
        isGenerating: false,
        elapsedTime: 0,
        timerInterval: null,
        showCopySuccess: false,
        error: null,
        activeTab: 0,
        tabs: window.TAB_NAMES,
        currentScreen: 'input',

        // Evaluation state
        evaluationResult: emptyEvaluation(),
        isEvaluating: false,

        // 指摘を反映した再生成用コンテキスト
        refinement: {
            previousSummary: '',
            evaluationFeedback: ''
        },

        async init() {
            await this.updateDoctors();
            await this.updateSelectedModel();
        },

        async updateDoctors() {
            try {
                this.doctors = await fetchDoctors(this.settings.department);
                if (!this.doctors.includes(this.settings.doctor)) {
                    this.settings.doctor = this.doctors[0];
                }
            } catch (error) {
                console.error('医師リストの取得中にエラーが発生しました:', error);
            }
        },

        async updateSelectedModel() {
            try {
                const params = new URLSearchParams({
                    department: this.settings.department,
                    document_type: this.settings.documentType,
                    doctor: this.settings.doctor
                });
                const response = await fetch(`/api/settings/selected-model?${params}`, {
                    headers: getHeaders()
                });
                if (!response.ok) {
                    console.error('選択モデルの取得に失敗しました:', response.status, response.statusText);
                    return;
                }
                const data = await response.json() as SelectedModelResponse;
                if (data.selected_model) {
                    this.settings.model = data.selected_model;
                }
            } catch (error) {
                console.error('選択モデルの取得中にエラーが発生しました:', error);
            }
        },

        startTimer() {
            this.elapsedTime = 0;
            this.timerInterval = setInterval(() => {
                this.elapsedTime++;
            }, 1000);
        },

        stopTimer() {
            if (this.timerInterval !== null) {
                clearInterval(this.timerInterval);
                this.timerInterval = null;
            }
        },

        // SSEエンドポイントを呼び出し、complete イベントで onComplete を実行する
        async runStream(url: string, body: Record<string, unknown>, onComplete: (data: unknown) => void) {
            this.error = null;
            this.startTimer();

            try {
                const response = await postJson(url, body);
                if (!response.ok) {
                    this.error = await errorMessageOf(response, window.MESSAGES.ERROR.API_ERROR);
                    return;
                }

                await readSSE(response, (eventType, data) => {
                    // progress はハートビートのため何もしない
                    if (eventType === 'complete') {
                        onComplete(data);
                    } else if (eventType === 'error') {
                        this.error = (data as SSEErrorEvent).error_message || window.MESSAGES.ERROR.GENERIC_ERROR;
                    }
                });
            } catch (e) {
                console.error('SSEストリーミング中にエラーが発生:', e);
                this.error = window.MESSAGES.ERROR.API_ERROR;
            } finally {
                this.stopTimer();
            }
        },

        buildGenerateRequestBody(): Record<string, unknown> {
            return {
                previous_text: this.form.previousText,
                medical_text: this.form.medicalText,
                additional_info: this.form.additionalInfo,
                department: this.settings.department,
                doctor: this.settings.doctor,
                document_type: this.settings.documentType,
                model: this.settings.model,
                model_explicitly_selected: true,
                previous_summary: this.refinement.previousSummary,
                evaluation_feedback: this.refinement.evaluationFeedback
            };
        },

        async generateSummary() {
            if (!this.form.medicalText.trim()) {
                this.error = window.MESSAGES.VALIDATION.NO_INPUT;
                return;
            }

            this.isGenerating = true;
            try {
                await this.runStream('/api/summary/generate-stream', this.buildGenerateRequestBody(), (data) => {
                    const complete = data as SSECompleteEvent;
                    this.result = {
                        outputSummary: complete.output_summary || '',
                        parsedSummary: complete.parsed_summary || {},
                        processingTime: complete.processing_time || null,
                        modelUsed: complete.model_used || '',
                        modelSwitched: complete.model_switched || false
                    };
                    this.evaluationResult = emptyEvaluation();
                    this.activeTab = 0;
                    this.currentScreen = 'output';
                });
            } finally {
                this.isGenerating = false;
            }
        },

        async regenerateWithFeedback() {
            if (!this.result.outputSummary || !this.evaluationResult.result) {
                this.error = window.MESSAGES.VALIDATION.EVALUATION_NO_OUTPUT;
                return;
            }

            this.refinement = {
                previousSummary: this.result.outputSummary,
                evaluationFeedback: this.evaluationResult.result
            };
            try {
                await this.generateSummary();
            } finally {
                this.refinement = { previousSummary: '', evaluationFeedback: '' };
            }
        },

        clearForm() {
            this.form = {
                previousText: '',
                medicalText: '',
                additionalInfo: ''
            };
            this.result = emptyResult();
            this.evaluationResult = emptyEvaluation();
            this.error = null;
        },

        backToInput() {
            this.clearForm();
            this.currentScreen = 'input';
        },

        backToOutput() {
            this.currentScreen = 'output';
        },

        showEvaluation() {
            this.currentScreen = 'evaluation';
        },

        async evaluateOutput() {
            if (!this.result.outputSummary) {
                this.error = window.MESSAGES.VALIDATION.EVALUATION_NO_OUTPUT;
                return;
            }

            // 既に評価結果がある場合は確認ダイアログを表示
            if (this.evaluationResult.result && !confirm(window.MESSAGES.CONFIRM.RE_EVALUATE)) {
                return;
            }

            const body = {
                document_type: this.settings.documentType,
                input_text: this.form.medicalText,
                previous_text: this.form.previousText,
                additional_info: this.form.additionalInfo,
                output_summary: this.result.outputSummary
            };

            this.isEvaluating = true;
            try {
                await this.runStream('/api/evaluation/evaluate-stream', body, (data) => {
                    const complete = data as SSEEvaluationCompleteEvent;
                    this.evaluationResult = {
                        result: complete.evaluation_result || '',
                        processingTime: complete.processing_time || null
                    };
                    this.currentScreen = 'evaluation';
                });
            } finally {
                this.isEvaluating = false;
            }
        },

        async copyToClipboard(text: string) {
            try {
                await navigator.clipboard.writeText(text);
                this.showCopySuccess = true;
                setTimeout(() => {
                    this.showCopySuccess = false;
                }, 2000);
            } catch (e) {
                this.error = window.MESSAGES.ERROR.COPY_FAILED;
            }
        },

        // ヘルパー関数
        getCurrentTabContent(): string {
            if (this.activeTab === 0) {
                return this.result.outputSummary;
            }
            return this.result.parsedSummary[this.tabs[this.activeTab]] || '';
        },

        copyCurrentTab() {
            this.copyToClipboard(this.getCurrentTabContent());
        },

        getTabClass(index: number): string {
            return this.activeTab === index
                ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                : 'border-transparent text-white hover:text-gray-700 dark:hover:text-gray-300';
        }
    };
}
