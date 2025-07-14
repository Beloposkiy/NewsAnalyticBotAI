import React from 'react';

export default function App({ user }) {
  const firstName = user?.first_name || 'Гость';
  const lastName = user?.last_name ? ` ${user.last_name}` : '';

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-black to-gray-800 text-white flex flex-col items-center justify-center p-6">
      <h1 className="text-5xl font-extrabold mb-4 text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-purple-600 drop-shadow-lg">
        PostAIBot
      </h1>

      {user ? (
        <p className="text-md text-gray-400 mb-2">
          Добро пожаловать, {firstName}{lastName}!
        </p>
      ) : (
        <p className="text-md text-gray-500 mb-2">
          Вы не авторизованы в Telegram WebApp.
        </p>
      )}

      <p className="text-lg text-gray-300 mb-8 text-center max-w-xl">
        Telegram-бот для анализа новостной повестки с помощью нейросетей.
        Нажмите на кнопку ниже, чтобы открыть список топ-постов по категориям.
      </p>

      <a href="https://t.me/NewsAnaliticAI_bot?start=topics">
        <button className="bg-purple-600 hover:bg-purple-700 transition px-6 py-3 text-lg font-semibold rounded-xl shadow-md hover:shadow-xl flex items-center gap-2">
          Показать топ-посты по категориям
        </button>
      </a>
    </div>
  );
}