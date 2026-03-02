import Alpine from 'alpinejs';
import { appState } from './app';
import './styles/main.css';

// Alpine.jsのデータ登録
Alpine.data('appState', appState);

// グローバルに公開（デバッグ用）
declare global {
    interface Window {
        Alpine: typeof Alpine;
    }
}
window.Alpine = Alpine;

// Alpine.js開始
Alpine.start();
