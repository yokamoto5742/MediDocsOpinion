import Alpine from 'alpinejs';
import { appState } from './app';
import { evaluationPromptEditPage, evaluationPromptsPage } from './pages/evaluationPrompts';
import { promptEditPage, promptNewPage, promptsPage } from './pages/prompts';
import { statisticsPage } from './pages/statistics';
import './styles/main.css';

// Alpine.jsのデータ登録（テンプレートの x-data から名前で参照する）
Alpine.data('appState', appState);
Alpine.data('promptsPage', promptsPage);
Alpine.data('promptNewPage', promptNewPage);
Alpine.data('promptEditPage', promptEditPage);
Alpine.data('evaluationPromptsPage', evaluationPromptsPage);
Alpine.data('evaluationPromptEditPage', evaluationPromptEditPage);
Alpine.data('statisticsPage', statisticsPage);

// Alpine.js開始
Alpine.start();
