import api from './api';

export type ReportType = 'analise_unica' | 'historico_completo';

interface ReportResponse {
  id: string;
  tipo: ReportType;
  gerado_em: string;
  download_url: string;
}

/**
 * Gera o relatório no backend e dispara o download do PDF no navegador. O download
 * exige o header `Authorization`, por isso não pode ser um simples link `<a href>` —
 * o PDF é buscado via axios (que já injeta o token) e convertido em Blob local.
 */
export async function generateAndDownloadReport(
  repositoryId: string,
  tipo: ReportType,
  analiseId?: string,
): Promise<void> {
  const { data: report } = await api.post<ReportResponse>(
    `/api/v1/repositories/${repositoryId}/reports`,
    { tipo, analise_id: analiseId },
  );

  const pdfResponse = await api.get<Blob>(report.download_url, { responseType: 'blob' });
  const blobUrl = URL.createObjectURL(new Blob([pdfResponse.data], { type: 'application/pdf' }));

  const link = document.createElement('a');
  link.href = blobUrl;
  link.download = `softmeter-relatorio-${report.id}.pdf`;
  link.click();
  URL.revokeObjectURL(blobUrl);
}
