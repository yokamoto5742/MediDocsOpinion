// 設定
export interface Settings {
    department: string;
    doctor: string;
    documentType: string;
    model: string;
}

// フォームデータ
export interface FormData {
    referralPurpose: string;
    currentPrescription: string;
    medicalText: string;
    additionalInfo: string;
}

// 生成結果
export interface GenerationResult {
    outputSummary: string;
    parsedSummary: Record<string, string>;
    processingTime: number | null;
    modelUsed: string;
    modelSwitched: boolean;
}

// 評価結果
export interface EvaluationResult {
    result: string;
    processingTime: number | null;
}

// APIレスポンス（サーバー側のスキーマに対応）
export interface SummaryResponse {
    success: boolean;
    output_summary?: string;
    parsed_summary?: Record<string, string>;
    processing_time?: number;
    model_used?: string;
    model_switched?: boolean;
    error_message?: string;
}

export interface EvaluationResponse {
    success: boolean;
    evaluation_result?: string;
    processing_time?: number;
    error_message?: string;
}

export interface DoctorsResponse {
    doctors: string[];
}

export interface SelectedModelResponse {
    selected_model: string | null;
}

// SSEイベント型
export interface SSEProgressEvent {
    status: string;
    message: string;
}

export interface SSECompleteEvent {
    success: boolean;
    output_summary: string;
    parsed_summary: Record<string, string>;
    input_tokens: number;
    output_tokens: number;
    processing_time: number;
    model_used: string;
    model_switched: boolean;
}

export interface SSEErrorEvent {
    success: boolean;
    error_message: string;
}

export interface SSEEvaluationCompleteEvent {
    success: boolean;
    evaluation_result: string;
    input_tokens: number;
    output_tokens: number;
    processing_time: number;
}

// メッセージ定数の型定義
export interface MessagesMap {
    ERROR: Record<string, string>;
    VALIDATION: Record<string, string>;
    SUCCESS: Record<string, string>;
    INFO: Record<string, string>;
    CONFIRM: Record<string, string>;
}

// グローバル変数の型宣言
declare global {
    interface Window {
        DOCUMENT_PURPOSE_MAPPING?: Record<string, string>;
        CSRF_TOKEN?: string;
        TAB_NAMES?: readonly string[];
        MESSAGES?: MessagesMap;
    }
}
