// 一覧テーブルのソート状態
export interface SortState {
    column: string;
    direction: 'asc' | 'desc';
}

// 日時文字列を「YYYY/MM/DD HH:mm」形式で表示
export function formatDateTime(dateStr: string | null | undefined): string {
    if (!dateStr) return '-';
    return new Date(dateStr).toLocaleString('ja-JP', {
        year: 'numeric',
        month: '2-digit',
        day: '2-digit',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// ソート対象の列を切り替える（同じ列をもう一度選ぶと昇順・降順を反転）
export function toggleSort(sort: SortState, column: string): void {
    if (sort.column === column) {
        sort.direction = sort.direction === 'asc' ? 'desc' : 'asc';
    } else {
        sort.column = column;
        sort.direction = 'asc';
    }
}

// 数値は数値として、それ以外は大文字小文字を区別しない文字列として比較する
function compareValues(a: unknown, b: unknown): number {
    if (typeof a === 'number' && typeof b === 'number') return a - b;
    const aText = String(a ?? '').toLowerCase();
    const bText = String(b ?? '').toLowerCase();
    if (aText < bText) return -1;
    if (aText > bText) return 1;
    return 0;
}

// 現在のソート状態で行を並べ替える（dateColumns の列は日時として比較）
export function sortRows<T extends object>(rows: T[], sort: SortState, dateColumns: string[] = []): void {
    const column = sort.column as keyof T;
    const sign = sort.direction === 'asc' ? 1 : -1;
    const isDate = dateColumns.includes(sort.column);
    const keyOf = (row: T): unknown =>
        isDate ? new Date(row[column] as string).getTime() : row[column];

    rows.sort((a, b) => sign * compareValues(keyOf(a), keyOf(b)));
}

export function getSortIcon(sort: SortState, column: string): string {
    if (sort.column !== column) return '⇅';
    return sort.direction === 'asc' ? '↑' : '↓';
}

// ?created=1 のような完了フラグに対応するメッセージを返し、URLからクエリを取り除く
// （再読み込みで同じメッセージが再表示されないようにするため）
export function consumeQueryFlag(messages: Record<string, string>): string | null {
    const params = new URLSearchParams(window.location.search);
    for (const [flag, message] of Object.entries(messages)) {
        if (params.get(flag) === '1') {
            window.history.replaceState({}, document.title, window.location.pathname);
            return message;
        }
    }
    return null;
}
