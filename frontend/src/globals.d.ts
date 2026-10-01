// base.html のインラインスクリプトでサーバーから渡される値
interface Window {
    CSRF_TOKEN: string;
    TAB_NAMES: string[];
    MESSAGES: Record<string, Record<string, string>>;
    DOCUMENT_TYPES: string[];
}
