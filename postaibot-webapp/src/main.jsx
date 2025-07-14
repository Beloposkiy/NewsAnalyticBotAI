import React from 'react';
import ReactDOM from 'react-dom/client';
import App from './App.jsx';
import './index.css';

document.addEventListener('DOMContentLoaded', () => {
  let telegramUser = null;

  if (typeof window !== 'undefined' && window.Telegram && window.Telegram.WebApp) {
    try {
      window.Telegram.WebApp.ready();
      telegramUser = window.Telegram.WebApp.initDataUnsafe?.user || null;
    } catch (err) {
      console.error('Telegram WebApp init error:', err);
    }
  }

  const rootEl = document.getElementById('root');
  if (rootEl) {
    ReactDOM.createRoot(rootEl).render(
      <React.StrictMode>
        <App user={telegramUser} />
      </React.StrictMode>
    );
  } else {
    console.error('root element not found');
  }
});