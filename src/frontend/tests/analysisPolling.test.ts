import { AxiosError } from 'axios';

import api from '../src/services/api';
import {
  AnalysisPollingTimeoutError,
  POLL_INTERVAL_MS,
  POLL_TIMEOUT_MS,
  isAbortError,
  triggerAnalysis,
} from '../src/services/analysisService';

jest.mock('../src/services/api', () => ({
  __esModule: true,
  default: { post: jest.fn(), get: jest.fn() },
  ACCESS_TOKEN_KEY: 'softmeter_token',
}));

const PROCESSING = { id: 'a-1', status: 'processando' };
const DONE = { id: 'a-1', status: 'concluida', status_conformidade_geral: 'Conforme', medicoes: [] };

function networkError() {
  return new AxiosError('Network Error');
}

describe('triggerAnalysis polling', () => {
  beforeEach(() => {
    jest.useFakeTimers();
    (api.post as jest.Mock).mockResolvedValue({ data: PROCESSING });
  });
  afterEach(() => {
    jest.useRealTimers();
    jest.clearAllMocks();
  });

  it('returns right away when the backend answers with a finished analysis', async () => {
    (api.post as jest.Mock).mockResolvedValueOnce({ data: DONE });

    await expect(triggerAnalysis('repo-1')).resolves.toEqual(DONE);
    expect(api.get).not.toHaveBeenCalled();
  });

  it('polls until the analysis finishes', async () => {
    (api.get as jest.Mock).mockResolvedValueOnce({ data: PROCESSING }).mockResolvedValueOnce({ data: DONE });

    const promise = triggerAnalysis('repo-1');
    await jest.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 3);

    await expect(promise).resolves.toEqual(DONE);
    expect(api.get).toHaveBeenCalledTimes(2);
  });

  it('gives up after the maximum wait instead of polling forever', async () => {
    // Regressão: era um laço infinito — uma análise presa no servidor deixava a tela girando para sempre.
    (api.get as jest.Mock).mockResolvedValue({ data: PROCESSING });

    const promise = triggerAnalysis('repo-1');
    const assertion = expect(promise).rejects.toBeInstanceOf(AnalysisPollingTimeoutError);
    await jest.advanceTimersByTimeAsync(POLL_TIMEOUT_MS + POLL_INTERVAL_MS * 2);

    await assertion;
    const calls = (api.get as jest.Mock).mock.calls.length;
    await jest.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 10);
    expect(api.get).toHaveBeenCalledTimes(calls); // parou de consultar
  });

  it('stops polling when the caller cancels (leaving the page)', async () => {
    (api.get as jest.Mock).mockResolvedValue({ data: PROCESSING });
    const controller = new AbortController();

    const promise = triggerAnalysis('repo-1', controller.signal);
    const outcome = promise.catch((err) => err);
    await jest.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 2);
    controller.abort();
    await jest.advanceTimersByTimeAsync(POLL_INTERVAL_MS);

    expect(isAbortError(await outcome)).toBe(true);
    const calls = (api.get as jest.Mock).mock.calls.length;
    await jest.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 10);
    expect(api.get).toHaveBeenCalledTimes(calls);
  });

  it('tolerates brief network failures during polling', async () => {
    (api.get as jest.Mock)
      .mockRejectedValueOnce(networkError())
      .mockRejectedValueOnce(networkError())
      .mockResolvedValueOnce({ data: DONE });

    const promise = triggerAnalysis('repo-1');
    await jest.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 4);

    await expect(promise).resolves.toEqual(DONE);
  });

  it('gives up after several network failures in a row', async () => {
    (api.get as jest.Mock).mockRejectedValue(networkError());

    const promise = triggerAnalysis('repo-1');
    const assertion = expect(promise).rejects.toBeInstanceOf(AxiosError);
    await jest.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 5);

    await assertion;
    expect(api.get).toHaveBeenCalledTimes(3);
  });

  it('stops right away when the analysis no longer exists (repository deleted)', async () => {
    const notFound = new AxiosError('Not Found');
    notFound.response = { status: 404, data: {}, statusText: '', headers: {}, config: {} as never };
    (api.get as jest.Mock).mockRejectedValue(notFound);

    const promise = triggerAnalysis('repo-1');
    const assertion = expect(promise).rejects.toBe(notFound);
    await jest.advanceTimersByTimeAsync(POLL_INTERVAL_MS * 2);

    await assertion;
    expect(api.get).toHaveBeenCalledTimes(1);
  });
});
