import express from 'express';
import cors from 'cors';
import dotenv from 'dotenv';

dotenv.config();

const app = express();
const PORT = process.env.PORT ?? 3001;

// Middlewares
app.use(cors());
app.use(express.json());

// Health check
app.get('/health', (_req, res) => {
  res.json({ status: 'ok', service: 'SoftMeter API', version: '0.1.0' });
});

// TODO: Importar rotas aqui após implementação
// app.use('/api/auth', authRoutes);
// app.use('/api/sistemas', sistemasRoutes);
// app.use('/api/requisitos', requisitosRoutes);
// app.use('/api/ciclos', ciclosRoutes);
// app.use('/api/medicoes', medicoesRoutes);
// app.use('/api/laudos', laudosRoutes);

app.listen(PORT, () => {
  console.log(`🚀 SoftMeter API rodando na porta ${PORT}`);
});

export default app;
