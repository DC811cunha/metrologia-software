import React from 'react';

/**
 * SoftMeter — Frontend React
 * Páginas planejadas:
 * /login       → Autenticação
 * /dashboard   → Visão geral dos sistemas
 * /sistemas    → Lista e cadastro de sistemas
 * /ciclos/:id  → Ciclo de teste ativo
 * /laudos/:id  → Laudo de conformidade gerado
 */
function App() {
  return (
    <div style={{ fontFamily: 'Arial, sans-serif', padding: '2rem', maxWidth: '800px', margin: '0 auto' }}>
      <h1>📐 SoftMeter</h1>
      <p><strong>Metrologia de Software</strong> — Plataforma de Inspeção e Conformidade</p>
      <hr />
      <p>Frontend em desenvolvimento. Próximas telas:</p>
      <ul>
        <li>🔐 Login / Cadastro</li>
        <li>📊 Dashboard</li>
        <li>⚙️ Gestão de Sistemas e Requisitos</li>
        <li>🧪 Registro de Medições</li>
        <li>📄 Laudo de Conformidade</li>
      </ul>
    </div>
  );
}

export default App;
