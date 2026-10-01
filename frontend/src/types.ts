// 設定
export interface Settings {
    department: string;
    doctor: string;
    documentType: string;
    model: string;
}

// 入力フォーム
export interface InputForm {
    previousText: string;
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
export interface DoctorsResponse {
    doctors: string[];
}

export interface SelectedModelResponse {
    selected_model: string | null;
}

export interface PromptListItem {
    id: number;
    department: string;
    document_type: string;
    doctor: string;
    selected_model: string | null;
    is_default: boolean;
    created_at: string | null;
    updated_at: string | null;
}

export interface PromptResponse extends PromptListItem {
    content: string;
}

export interface EvaluationPromptResponse {
    id: number | null;
    document_type: string;
    content: string | null;
    is_active: boolean;
    created_at: string | null;
    updated_at: string | null;
}

export interface EvaluationPromptSaveResponse {
    success: boolean;
    message: string;
    document_type: string;
}

export interface AggregatedRecord {
    document_type: string;
    department: string;
    doctor: string;
    count: number;
    input_tokens: number;
    output_tokens: number;
}

export interface UsageRecord {
    id: number;
    date: string | null;
    app_type: string | null;
    document_type: string | null;
    model: string | null;
    department: string | null;
    doctor: string | null;
    input_tokens: number | null;
    output_tokens: number | null;
    processing_time: number | null;
}

// SSEイベント型
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
