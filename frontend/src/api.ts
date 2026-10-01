import type { DoctorsResponse } from './types';

// APIリクエスト用のヘッダーを取得（CSRFトークン付き）
export function getHeaders(additionalHeaders: Record<string, string> = {}): Record<string, string> {
    return { ...additionalHeaders, 'X-CSRF-Token': window.CSRF_TOKEN };
}

// JSONボディ付きのPOSTリクエストを送信
export function postJson(url: string, body: unknown): Promise<Response> {
    return fetch(url, {
        method: 'POST',
        headers: getHeaders({ 'Content-Type': 'application/json' }),
        body: JSON.stringify(body)
    });
}

// DELETEリクエストを送信
export function deleteRequest(url: string): Promise<Response> {
    return fetch(url, { method: 'DELETE', headers: getHeaders() });
}

// エラーレスポンスからサーバーのメッセージを取り出す
// 例外ハンドラは error_message、HTTPException は detail を返す
export async function errorMessageOf(response: Response, fallback: string): Promise<string> {
    try {
        const data = await response.json();
        if (typeof data.error_message === 'string') return data.error_message;
        if (typeof data.detail === 'string') return data.detail;
    } catch {
        // JSON以外のレスポンスは定型文にフォールバック
    }
    return fallback;
}

// 診療科の医師リストを取得（失敗時は例外を送出）
export async function fetchDoctors(department: string): Promise<string[]> {
    const response = await fetch(`/api/settings/doctors/${encodeURIComponent(department)}`, {
        headers: getHeaders()
    });
    if (!response.ok) {
        throw new Error(`HTTP ${response.status}`);
    }
    const data = await response.json() as DoctorsResponse;
    return data.doctors;
}

// SSEレスポンスを読み取り、イベントごとに onEvent を呼び出す
export async function readSSE(
    response: Response,
    onEvent: (eventType: string, data: unknown) => void
): Promise<void> {
    if (!response.body) {
        throw new Error(window.MESSAGES.ERROR.RESPONSE_BODY_EMPTY);
    }

    const dispatch = (block: string): void => {
        let eventType = '';
        let data = '';
        for (const line of block.split('\n')) {
            if (line.startsWith('event: ')) {
                eventType = line.slice(7).trim();
            } else if (line.startsWith('data: ')) {
                data = line.slice(6);
            }
        }
        if (eventType && data) {
            onEvent(eventType, JSON.parse(data));
        }
    };

    const reader = response.body.getReader();
    const decoder = new TextDecoder();
    let buffer = '';

    try {
        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            // イベントは空行区切り。末尾の未完成ブロックは次の読み取りまで保持する
            buffer += decoder.decode(value, { stream: true });
            const blocks = buffer.split('\n\n');
            buffer = blocks.pop() ?? '';
            blocks.forEach(dispatch);
        }
        dispatch(buffer);
    } finally {
        reader.releaseLock();
    }
}
