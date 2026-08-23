/**
 * CrimeGraphDataService & HttpCrimeGraphAdapter Reference Implementation.
 * 
 * Demonstrates how Shruti's frontend UI components (Graph Canvas, Dashboard, Timeline, Evidence Panel)
 * consume the real FastAPI backend over HTTP (default: http://127.0.0.1:8000).
 * 
 * Strictly follows API_CONTRACT.md.
 */

class HttpCrimeGraphAdapter {
  constructor(baseUrl = 'http://127.0.0.1:8000') {
    this.baseUrl = baseUrl;
  }

  async _fetchJson(endpoint, options = {}) {
    const url = `${this.baseUrl}${endpoint}`;
    try {
      const response = await fetch(url, {
        headers: {
          'Content-Type': 'application/json',
          ...(options.headers || {})
        },
        ...options
      });

      if (!response.ok) {
        const errorData = await response.json().catch(() => ({ detail: response.statusText }));
        throw new Error(errorData.detail || `HTTP Error ${response.status}`);
      }

      return await response.json();
    } catch (error) {
      console.error(`[HttpCrimeGraphAdapter] Error calling ${endpoint}:`, error);
      throw error;
    }
  }

  /**
   * GET /api/cases/{case_id}/graph
   * Retrieves visual graph nodes and edges for a specific case.
   */
  async getCaseGraph(caseId) {
    return await this._fetchJson(`/api/cases/${encodeURIComponent(caseId)}/graph`);
  }

  /**
   * GET /api/entities/{entity_id}
   * Retrieves entity details, connected relationships, cases, and supporting evidence.
   */
  async getEntityDetails(entityId) {
    return await this._fetchJson(`/api/entities/${encodeURIComponent(entityId)}`);
  }

  /**
   * GET /api/cases/connections?case_a=CASE_101&case_b=CASE_204
   * Discovers multi-hop relationship chains between two cases.
   */
  async getCrossCaseConnections(caseA = 'CASE_101', caseB = 'CASE_204', maxDepth = 6) {
    return await this._fetchJson(`/api/cases/connections?case_a=${encodeURIComponent(caseA)}&case_b=${encodeURIComponent(caseB)}&max_depth=${maxDepth}`);
  }

  /**
   * GET /api/cases/{case_id}/timeline
   * Retrieves chronological events for a case.
   */
  async getCaseTimeline(caseId) {
    return await this._fetchJson(`/api/cases/${encodeURIComponent(caseId)}/timeline`);
  }

  /**
   * GET /api/cases
   * Lists all cases registered in the system.
   */
  async listCases(status = null) {
    const query = status ? `?status=${encodeURIComponent(status)}` : '';
    return await this._fetchJson(`/api/cases${query}`);
  }

  /**
   * GET /api/entities
   * Search and filter entities by type, query, or minimum confidence.
   */
  async listEntities(params = {}) {
    const searchParams = new URLSearchParams(params).toString();
    const query = searchParams ? `?${searchParams}` : '';
    return await this._fetchJson(`/api/entities${query}`);
  }

  /**
   * GET /api/evidence/{evidence_id}
   * Retrieves detailed source text excerpt and extraction metadata.
   */
  async getEvidence(evidenceId) {
    return await this._fetchJson(`/api/evidence/${encodeURIComponent(evidenceId)}`);
  }

  /**
   * POST /api/reports
   * Generates an evidence-backed case summary report.
   */
  async generateReport(caseId) {
    return await this._fetchJson('/api/reports', {
      method: 'POST',
      body: JSON.stringify({ case_id: caseId })
    });
  }

  /**
   * POST /api/investigate
   * Sends a natural language query to the AI investigator.
   */
  async queryInvestigator(question) {
    return await this._fetchJson('/api/investigate', {
      method: 'POST',
      body: JSON.stringify({ question })
    });
  }
}

/**
 * CrimeGraphDataService
 * Higher-level data service that can switch between Mock and Real HTTP Adapter.
 */
class CrimeGraphDataService {
  constructor(adapter = new HttpCrimeGraphAdapter()) {
    this.adapter = adapter;
  }

  async loadCaseNetwork(caseId) {
    return await this.adapter.getCaseGraph(caseId);
  }

  async inspectEntity(entityId) {
    return await this.adapter.getEntityDetails(entityId);
  }

  async discoverCaseConnections(caseA, caseB) {
    return await this.adapter.getCrossCaseConnections(caseA, caseB);
  }

  async loadTimeline(caseId) {
    return await this.adapter.getCaseTimeline(caseId);
  }

  async askInvestigator(question) {
    return await this.adapter.queryInvestigator(question);
  }
}

// Export for Node / Web module systems
if (typeof module !== 'undefined' && module.exports) {
  module.exports = { HttpCrimeGraphAdapter, CrimeGraphDataService };
}
