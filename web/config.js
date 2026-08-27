/**
 * CrimeGraph AI — Frontend Runtime Configuration
 * Architected by Shruti for SIH 2026.
 *
 * Centralizes API base URL and runtime settings for development & production deployments.
 */

window.CRIMEGRAPH_CONFIG = window.CRIMEGRAPH_CONFIG || {
    // Backend API Base URL (Can be overridden dynamically or by environment)
    API_BASE_URL: (typeof window !== "undefined" && window.location && window.location.origin && window.location.origin.startsWith("http"))
        ? window.location.origin
        : "http://127.0.0.1:8000",
    
    // Application Metadata
    APP_NAME: "CrimeGraph AI",
    VERSION: "1.0.0",
    ENVIRONMENT: "production",

    // Timeout & Retry Settings
    API_TIMEOUT_MS: 5000
};
