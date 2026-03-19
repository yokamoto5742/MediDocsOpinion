import Alpine from 'alpinejs';
import { appState } from './app';
import './styles/main.css';

// Alpine.jsのデータ登録
Alpine.data('appState', appState);

// Alpine.js開始
Alpine.start();
