/**
 * CrimeGraph AI — Frontend Runtime Configuration
 * Architected by Shruti for SIH 2026.
 *
 * Centralizes API base URL and runtime settings for development & production deployments.
 */

window.CRIMEGRAPH_API_URL = window.CRIMEGRAPH_API_URL || "http://127.0.0.1:8000";

window.CRIMEGRAPH_CONFIG = window.CRIMEGRAPH_CONFIG || {
    // Backend API Base URL (Can be overridden dynamically or by window.CRIMEGRAPH_API_URL)
    API_BASE_URL: window.CRIMEGRAPH_API_URL || "http://127.0.0.1:8000",
    
    // Application Metadata
    APP_NAME: "CrimeGraph AI",
    VERSION: "1.0.0",
    ENVIRONMENT: "development",
    DATA_MODE: window.CRIMEGRAPH_DATA_MODE || "api",

    // Timeout & Retry Settings
    API_TIMEOUT_MS: 10000
};
