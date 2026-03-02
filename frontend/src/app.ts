import type {
    Settings,
    FormData,
    GenerationResult,
    EvaluationResult,
    SummaryResponse,
    EvaluationResponse,
    DoctorsResponse,
    SelectedModelResponse,
    SSECompleteEvent,
    SSEErrorEvent,
    SSEEvaluationCompleteEvent
} from './types';

type ScreenType = 'input' | 'output' | 'evaluation';

interface AppState {
    settings: Settings;
    doctors: string[];
    form: FormData;
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
    evaluationElapsedTime: number;
    evaluationTimerInterval: ReturnType<typeof setInterval> | null;
    init(): Promise<void>;
    updateReferralPurpose(): void;
    updateDoctors(): Promise<void>;
    startTimer(): void;
    stopTimer(): void;
    generateSummary(): Promise<void>;
    processSSEStream(response: Response): Promise<void>;
    handleSSEEvent(eventText: string): void;
    generateSummaryFallback(): Promise<void>;
    clearForm(): void;
    backToInput(): void;
    backToOutput(): void;
    showEvaluation(): void;
    startEvaluationTimer(): void;
    stopEvaluationTimer(): void;
    evaluateOutput(): Promise<void>;
    processEvaluationSSEStream(response: Response): Promise<void>;
    handleEvaluationSSEEvent(eventText: string): void;
    evaluateOutputFallback(): Promise<void>;
    copyToClipboard(text: string): Promise<void>;
    getCurrentTabContent(): string;
    copyCurrentTab(): void;
    isActiveTab(index: number): boolean;
    getTabClass(index: number): string;
}

// APIリクエスト用のヘッダーを取得
function getHeaders(additionalHeaders: Record<string, string> = {}): Record<string, string> {
    const headers: Record<string, string> = { ...additionalHeaders };
    if (window.CSRF_TOKEN) {
        headers['X-CSRF-Token'] = window.CSRF_TOKEN;
    }
    return headers;
}

export function appState(): AppState {
    return {
        // Settings
        settings: {
            department: 'default',
            doctor: 'default',
            documentType: (window as any).DOCUMENT_TYPES?.[0],
            model: 'Claude'
        },
        doctors: ['default'],

        // Form
        form: {
            referralPurpose: '',
            currentPrescription: '',
            medicalText: '',
            additionalInfo: ''
        },

        // Result
        result: {
            outputSummary: '',
            parsedSummary: {},
            processingTime: null,
            modelUsed: '',
            modelSwitched: false
        },

        // UI state
        isGenerating: false,
        elapsedTime: 0,
        timerInterval: null,
        showCopySuccess: false,
        error: null,
        activeTab: 0,
        tabs: window.TAB_NAMES ?? ['全文'],
        currentScreen: 'input',

        // Evaluation state
        evaluationResult: {
            result: '',
            processingTime: null
        },
        isEvaluating: false,
        evaluationElapsedTime: 0,
        evaluationTimerInterval: null,

        async init() {
            await this.updateDoctors();
            this.updateReferralPurpose();
            await this.updateSelectedModel();
        },

        updateReferralPurpose() {
            if (window.DOCUMENT_PURPOSE_MAPPING && window.DOCUMENT_PURPOSE_MAPPING[this.settings.documentType]) {
                this.form.referralPurpose = window.DOCUMENT_PURPOSE_MAPPING[this.settings.documentType];
            }
        },

        async updateDoctors() {
            try {
                const response = await fetch(`/api/settings/doctors/${this.settings.department}`, {
                    headers: getHeaders()
                });
                if (!response.ok) {
                    console.error('医師リストの取得に失敗しました:', response.status, response.statusText);
                    return;
                }
                const data = await response.json() as DoctorsResponse;
                this.doctors = data.doctors;
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

        async generateSummary() {
            if (!this.form.medicalText.trim()) {
                this.error = window.MESSAGES?.VALIDATION?.NO_INPUT ?? 'カルテ情報を入力してください';
                return;
            }

            this.isGenerating = true;
            this.error = null;
            this.startTimer();

            try {
                const response = await fetch('/api/summary/generate-stream', {
                    method: 'POST',
                    headers: getHeaders({ 'Content-Type': 'application/json' }),
                    body: JSON.stringify({
                        referral_purpose: this.form.referralPurpose,
                        current_prescription: this.form.currentPrescription,
                        medical_text: this.form.medicalText,
                        additional_info: this.form.additionalInfo,
                        department: this.settings.department,
                        doctor: this.settings.doctor,
                        document_type: this.settings.documentType,
                        model: this.settings.model,
                        model_explicitly_selected: true
                    })
                });

                if (!response.ok) {
                    console.warn(`SSEストリーミングエンドポイントが利用不可 (status: ${response.status})、非ストリーミングにフォールバック`);
                    await this.generateSummaryFallback();
                    return;
                }

                await this.processSSEStream(response);

            } catch (e) {
                console.error('SSEストリーミング中にエラーが発生:', e);
                // ネットワークエラー時は非ストリーミングにフォールバック
                try {
                    await this.generateSummaryFallback();
                } catch (fallbackError) {
                    console.error('フォールバックも失敗:', fallbackError);
                    this.error = window.MESSAGES?.ERROR?.API_ERROR ?? 'API エラーが発生しました';
                }
            } finally {
                this.stopTimer();
                this.isGenerating = false;
            }
        },

        async processSSEStream(response: Response) {
            if (!response.body) {
                throw new Error(window.MESSAGES?.ERROR?.RESPONSE_BODY_EMPTY ?? 'レスポンスボディが空です');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            try {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const events = buffer.split('\n\n');
                    buffer = events.pop() || '';

                    for (const eventText of events) {
                        if (!eventText.trim()) continue;
                        this.handleSSEEvent(eventText);
                    }
                }

                // 残りのバッファを処理
                if (buffer.trim()) {
                    this.handleSSEEvent(buffer);
                }
            } catch (e) {
                console.error('SSEストリーム読み取り中にエラーが発生:', e);
                throw e;
            } finally {
                reader.releaseLock();
            }
        },

        handleSSEEvent(eventText: string) {
            const lines = eventText.split('\n');
            let eventType = '';
            let data = '';

            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    eventType = line.slice(7).trim();
                } else if (line.startsWith('data: ')) {
                    data = line.slice(6);
                }
            }

            if (!eventType || !data) return;

            const parsed = JSON.parse(data);

            switch (eventType) {
                case 'progress':
                    // ハートビート - UIのステータス表示を更新可能
                    break;
                case 'complete':
                    if ((parsed as SSECompleteEvent).success) {
                        const completeData = parsed as SSECompleteEvent;
                        this.result = {
                            outputSummary: completeData.output_summary || '',
                            parsedSummary: completeData.parsed_summary || {},
                            processingTime: completeData.processing_time || null,
                            modelUsed: completeData.model_used || '',
                            modelSwitched: completeData.model_switched || false
                        };
                        this.evaluationResult = { result: '', processingTime: null };
                        this.activeTab = 0;
                        this.currentScreen = 'output';
                    } else {
                        this.error = (parsed as SSEErrorEvent).error_message || (window.MESSAGES?.ERROR?.GENERIC_ERROR ?? 'エラーが発生しました');
                    }
                    break;
                case 'error':
                    this.error = (parsed as SSEErrorEvent).error_message || (window.MESSAGES?.ERROR?.GENERIC_ERROR ?? 'エラーが発生しました');
                    break;
            }
        },

        async generateSummaryFallback() {
            const response = await fetch('/api/summary/generate', {
                method: 'POST',
                headers: getHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({
                    referral_purpose: this.form.referralPurpose,
                    current_prescription: this.form.currentPrescription,
                    medical_text: this.form.medicalText,
                    additional_info: this.form.additionalInfo,
                    department: this.settings.department,
                    doctor: this.settings.doctor,
                    document_type: this.settings.documentType,
                    model: this.settings.model,
                    model_explicitly_selected: true
                })
            });

            const data = await response.json() as SummaryResponse;

            if (data.success) {
                this.result = {
                    outputSummary: data.output_summary || '',
                    parsedSummary: data.parsed_summary || {},
                    processingTime: data.processing_time || null,
                    modelUsed: data.model_used || '',
                    modelSwitched: data.model_switched || false
                };
                this.evaluationResult = { result: '', processingTime: null };
                this.activeTab = 0;
                this.currentScreen = 'output';
            } else {
                this.error = data.error_message || (window.MESSAGES?.ERROR?.GENERIC_ERROR ?? 'エラーが発生しました');
            }
        },

        clearForm() {
            this.form = {
                referralPurpose: '',
                currentPrescription: '',
                medicalText: '',
                additionalInfo: ''
            };
            this.result = {
                outputSummary: '',
                parsedSummary: {},
                processingTime: null,
                modelUsed: '',
                modelSwitched: false
            };
            this.evaluationResult = {
                result: '',
                processingTime: null
            };
            this.error = null;
        },

        backToInput() {
            this.clearForm();
            this.currentScreen = 'input';
            this.error = null;
        },

        backToOutput() {
            this.currentScreen = 'output';
        },

        showEvaluation() {
            this.currentScreen = 'evaluation';
        },

        startEvaluationTimer() {
            this.evaluationElapsedTime = 0;
            this.evaluationTimerInterval = setInterval(() => {
                this.evaluationElapsedTime++;
            }, 1000);
        },

        stopEvaluationTimer() {
            if (this.evaluationTimerInterval !== null) {
                clearInterval(this.evaluationTimerInterval);
                this.evaluationTimerInterval = null;
            }
        },

        async evaluateOutput() {
            if (!this.result.outputSummary) {
                this.error = window.MESSAGES?.VALIDATION?.EVALUATION_NO_OUTPUT ?? '評価対象の出力がありません';
                return;
            }

            // 既に評価結果がある場合は確認ダイアログを表示
            if (this.evaluationResult.result) {
                if (!confirm(window.MESSAGES?.CONFIRM?.RE_EVALUATE ?? '前回の評価をクリアして再評価しますか？')) {
                    return;
                }
            }

            this.isEvaluating = true;
            this.error = null;
            this.startEvaluationTimer();

            try {
                const response = await fetch('/api/evaluation/evaluate-stream', {
                    method: 'POST',
                    headers: getHeaders({ 'Content-Type': 'application/json' }),
                    body: JSON.stringify({
                        document_type: this.settings.documentType,
                        input_text: this.form.medicalText,
                        current_prescription: this.form.currentPrescription,
                        additional_info: this.form.additionalInfo,
                        output_summary: this.result.outputSummary
                    })
                });

                if (!response.ok) {
                    console.warn(`SSEストリーミングエンドポイントが利用不可 (status: ${response.status})、非ストリーミングにフォールバック`);
                    await this.evaluateOutputFallback();
                    return;
                }

                await this.processEvaluationSSEStream(response);

            } catch (e) {
                console.error('SSEストリーミング中にエラーが発生:', e);
                try {
                    await this.evaluateOutputFallback();
                } catch (fallbackError) {
                    console.error('フォールバックも失敗:', fallbackError);
                    this.error = window.MESSAGES?.ERROR?.API_ERROR ?? 'API エラーが発生しました';
                }
            } finally {
                this.stopEvaluationTimer();
                this.isEvaluating = false;
            }
        },

        async processEvaluationSSEStream(response: Response) {
            if (!response.body) {
                throw new Error(window.MESSAGES?.ERROR?.RESPONSE_BODY_EMPTY ?? 'レスポンスボディが空です');
            }

            const reader = response.body.getReader();
            const decoder = new TextDecoder();
            let buffer = '';

            try {
                while (true) {
                    const { done, value } = await reader.read();
                    if (done) break;

                    buffer += decoder.decode(value, { stream: true });
                    const events = buffer.split('\n\n');
                    buffer = events.pop() || '';

                    for (const eventText of events) {
                        if (!eventText.trim()) continue;
                        this.handleEvaluationSSEEvent(eventText);
                    }
                }

                // 残りのバッファを処理
                if (buffer.trim()) {
                    this.handleEvaluationSSEEvent(buffer);
                }
            } catch (e) {
                console.error('SSEストリーム読み取り中にエラーが発生:', e);
                throw e;
            } finally {
                reader.releaseLock();
            }
        },

        handleEvaluationSSEEvent(eventText: string) {
            const lines = eventText.split('\n');
            let eventType = '';
            let data = '';

            for (const line of lines) {
                if (line.startsWith('event: ')) {
                    eventType = line.slice(7).trim();
                } else if (line.startsWith('data: ')) {
                    data = line.slice(6);
                }
            }

            if (!eventType || !data) return;

            const parsed = JSON.parse(data);

            switch (eventType) {
                case 'progress':
                    // ハートビート - UIのステータス表示を更新可能
                    break;
                case 'complete':
                    if ((parsed as SSEEvaluationCompleteEvent).success) {
                        const completeData = parsed as SSEEvaluationCompleteEvent;
                        this.evaluationResult = {
                            result: completeData.evaluation_result || '',
                            processingTime: completeData.processing_time || null
                        };
                        this.currentScreen = 'evaluation';
                    } else {
                        this.error = (parsed as SSEErrorEvent).error_message || (window.MESSAGES?.ERROR?.GENERIC_ERROR ?? 'エラーが発生しました');
                    }
                    break;
                case 'error':
                    this.error = (parsed as SSEErrorEvent).error_message || (window.MESSAGES?.ERROR?.GENERIC_ERROR ?? 'エラーが発生しました');
                    break;
            }
        },

        async evaluateOutputFallback() {
            const response = await fetch('/api/evaluation/evaluate', {
                method: 'POST',
                headers: getHeaders({ 'Content-Type': 'application/json' }),
                body: JSON.stringify({
                    document_type: this.settings.documentType,
                    input_text: this.form.medicalText,
                    current_prescription: this.form.currentPrescription,
                    additional_info: this.form.additionalInfo,
                    output_summary: this.result.outputSummary
                })
            });

            const data = await response.json() as EvaluationResponse;

            if (data.success) {
                this.evaluationResult = {
                    result: data.evaluation_result || '',
                    processingTime: data.processing_time || null
                };
                this.currentScreen = 'evaluation';
            } else {
                this.error = data.error_message || (window.MESSAGES?.ERROR?.EVALUATION_ERROR ?? '評価中にエラーが発生しました');
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
                this.error = window.MESSAGES?.ERROR?.COPY_FAILED ?? 'テキストのコピーに失敗しました';
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

        isActiveTab(index: number): boolean {
            return this.activeTab === index;
        },

        getTabClass(index: number): string {
            return this.isActiveTab(index)
                ? 'border-blue-500 text-blue-600 dark:border-blue-400 dark:text-blue-400'
                : 'border-transparent text-white hover:text-gray-700 dark:hover:text-gray-300';
        }
    };
}
