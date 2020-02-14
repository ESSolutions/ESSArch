export const BASE_URL = `/api`;

export interface ResponsePromise extends Promise<Response> {
  arrayBuffer(): Promise<ArrayBuffer>;
  blob(): Promise<Blob>;
  formData(): Promise<FormData>;
  json<T>(): Promise<T>;
  text(): Promise<string>;
}

const verifyResponse = async (response: Promise<Response>): Promise<Response> => {
  let r = await response;
  if (r.status >= 400) {
    return Promise.reject(r.status);
  }
  return r;
};

class ApiResponse extends Promise<Response> implements ResponsePromise {
  async arrayBuffer() {
    return (await verifyResponse(this)).arrayBuffer();
  }

  async blob() {
    return (await verifyResponse(this)).blob();
  }

  async formData() {
    return (await verifyResponse(this)).formData();
  }

  async json<T>(): Promise<T> {
    return (await verifyResponse(this)).json();
  }

  async text() {
    return (await verifyResponse(this)).text();
  }
}

class Api {
  constructor(public baseUrl: string) {}

  private static joinUrls(first: string, second: string) {
    if (first.endsWith('/') && second.startsWith('/')) {
      first = first.slice(0, -1);
    }

    if (first && !first.endsWith('/')) {
      first += '/';
    }

    return first + second;
  }

  public get(url: string, params = {}, signal?: AbortSignal): ApiResponse {
    const fullUrl = Api.joinUrls(this.baseUrl, url);
    const paramsString = new URLSearchParams(params).toString();
    const input = paramsString !== '' ? `${fullUrl}?${paramsString}` : fullUrl;

    const headers: any = {};

    const response = fetch(input, {method: 'GET', headers, signal});
    return new ApiResponse((resolve, reject) => {
      resolve(response);
    });
  }

  public post(url: string, data = {}, signal?: AbortSignal): ApiResponse {
    const fullUrl = Api.joinUrls(this.baseUrl, url);
    const jsonData = JSON.stringify(data);

    const headers: any = {'Content-Type': 'application/json'};
    const response = fetch(fullUrl, {method: 'POST', body: jsonData, headers, signal});
    return new ApiResponse((resolve, reject) => {
      resolve(response);
    });
  }
}

const instance = new Api(BASE_URL);
export default instance;
