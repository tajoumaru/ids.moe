// API client for IDS.moe API key management

export interface ApiKeyResponse {
  exists?: boolean;
  key: string;
  createdAt: number;
  lastUsed?: number;
  message?: string;
}

export class ApiClient {
  private baseUrl: string;
  private getAuthToken: () => Promise<string | null>;

  constructor(baseUrl: string = '', getAuthToken: () => Promise<string | null>) {
    this.baseUrl = baseUrl;
    this.getAuthToken = getAuthToken;
  }

  private async makeRequest(path: string, options: RequestInit = {}): Promise<Response> {
    const token = await this.getAuthToken();
    if (!token) {
      throw new Error('No authentication token available');
    }

    const headers = {
      'Authorization': `Bearer ${token}`,
      'Content-Type': 'application/json',
      ...options.headers,
    };

    const response = await fetch(`${this.baseUrl}${path}`, {
      ...options,
      headers,
    });

    if (!response.ok) {
      throw new Error(`API request failed: ${response.status} ${response.statusText}`);
    }

    return response;
  }

  async getApiKey(): Promise<ApiKeyResponse> {
    const response = await this.makeRequest('/apikey');
    return response.json();
  }

  async regenerateApiKey(): Promise<ApiKeyResponse> {
    const response = await this.makeRequest('/apikey/regenerate', {
      method: 'POST',
    });
    return response.json();
  }
}