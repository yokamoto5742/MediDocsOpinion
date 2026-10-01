import type { AggregatedRecord, UsageRecord } from '../types';
import { formatDateTime, getSortIcon, sortRows, toggleSort } from '../utils';
import type { SortState } from '../utils';

interface StatisticsPage {
    aggregatedRecords: AggregatedRecord[];
    records: UsageRecord[];
    filter: { startDate: string; endDate: string; model: string; documentType: string };
    pagination: { limit: number; offset: number };
    totalRecords: number;
    isLoadingAggregated: boolean;
    isLoadingRecords: boolean;
    error: string | null;
    aggregatedSort: SortState;
    recordsSort: SortState;
    init(): Promise<void>;
    loadData(): Promise<void>;
    buildFilterParams(): URLSearchParams;
    loadAggregatedData(): Promise<void>;
    loadRecords(): Promise<void>;
    nextPage(): Promise<void>;
    previousPage(): Promise<void>;
    formatNumber(num: number): string;
    formatDateTime(dateStr: string | null): string;
    formatModelName(model: string | null): string;
    sortAggregated(column: string): void;
    sortRecords(column: string): void;
    getSortIcon(sortState: SortState, column: string): string;
}

// 統計情報ページ
export function statisticsPage(): StatisticsPage {
    return {
        aggregatedRecords: [],
        records: [],
        filter: {
            startDate: '',
            endDate: '',
            model: '',
            documentType: ''
        },
        pagination: {
            limit: 25,
            offset: 0
        },
        totalRecords: 0,
        isLoadingAggregated: false,
        isLoadingRecords: false,
        error: null,
        aggregatedSort: { column: '', direction: 'asc' },
        recordsSort: { column: '', direction: 'asc' },

        async init() {
            // デフォルトの日付範囲を設定（終了日: 本日、開始日: 7日前）
            const today = new Date();
            const sevenDaysAgo = new Date(today);
            sevenDaysAgo.setDate(today.getDate() - 7);

            this.filter.endDate = today.toISOString().split('T')[0];
            this.filter.startDate = sevenDaysAgo.toISOString().split('T')[0];

            await this.loadData();
        },

        async loadData() {
            await Promise.all([
                this.loadAggregatedData(),
                this.loadRecords()
            ]);
        },

        // 集計と使用履歴で共通の絞り込み条件をクエリパラメータにする
        buildFilterParams(): URLSearchParams {
            const params = new URLSearchParams();
            if (this.filter.startDate) {
                // Asia/Tokyo タイムゾーンで開始日の 00:00:00 を設定
                params.append('start_date', this.filter.startDate + 'T00:00:00+09:00');
            }
            if (this.filter.endDate) {
                // Asia/Tokyo タイムゾーンで終了日の 23:59:59 を設定
                const endDateTime = new Date(this.filter.endDate + 'T23:59:59+09:00');
                params.append('end_date', endDateTime.toISOString());
            }
            if (this.filter.model) params.append('model', this.filter.model);
            if (this.filter.documentType) params.append('document_type', this.filter.documentType);
            return params;
        },

        async loadAggregatedData() {
            this.isLoadingAggregated = true;
            this.error = null;

            try {
                const response = await fetch(`/api/statistics/aggregated?${this.buildFilterParams()}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                this.aggregatedRecords = await response.json() as AggregatedRecord[];
            } catch {
                this.error = window.MESSAGES.ERROR.STATISTICS_AGGREGATED_LOAD_FAILED;
            } finally {
                this.isLoadingAggregated = false;
            }
        },

        async loadRecords() {
            this.isLoadingRecords = true;
            this.error = null;

            try {
                const params = this.buildFilterParams();
                params.append('limit', String(this.pagination.limit));
                params.append('offset', String(this.pagination.offset));

                const response = await fetch(`/api/statistics/records?${params}`);
                if (!response.ok) {
                    throw new Error(`HTTP ${response.status}`);
                }
                this.records = await response.json() as UsageRecord[];

                // APIは総件数を返さないため、1ページ分が埋まっていれば次ページがあるものとして扱う
                const hasNextPage = this.records.length === this.pagination.limit;
                this.totalRecords = this.records.length > 0
                    ? this.pagination.offset + this.records.length + (hasNextPage ? 1 : 0)
                    : 0;
            } catch {
                this.error = window.MESSAGES.ERROR.STATISTICS_RECORDS_LOAD_FAILED;
            } finally {
                this.isLoadingRecords = false;
            }
        },

        async nextPage() {
            this.pagination.offset += this.pagination.limit;
            await this.loadRecords();
        },

        async previousPage() {
            this.pagination.offset = Math.max(0, this.pagination.offset - this.pagination.limit);
            await this.loadRecords();
        },

        formatNumber(num: number): string {
            return new Intl.NumberFormat('ja-JP').format(num);
        },

        formatDateTime(dateStr: string | null): string {
            return formatDateTime(dateStr);
        },

        formatModelName(model: string | null): string {
            return model || '-';
        },

        sortAggregated(column: string) {
            toggleSort(this.aggregatedSort, column);
            sortRows(this.aggregatedRecords, this.aggregatedSort);
        },

        sortRecords(column: string) {
            toggleSort(this.recordsSort, column);
            sortRows(this.records, this.recordsSort, ['date']);
        },

        getSortIcon(sortState: SortState, column: string): string {
            return getSortIcon(sortState, column);
        }
    };
}
