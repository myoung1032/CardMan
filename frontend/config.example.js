// CardMan API Configuration Example
// Copy this file to config.js and fill in your actual values

const CONFIG = {
    // ========================================
    // AWS API Gateway Configuration
    // ========================================
    // Get this from: AWS Console → API Gateway → Your API → Stages → Invoke URL
    // Example: 'https://abc123xyz.execute-api.us-east-1.amazonaws.com'
    API_URL: 'YOUR_API_GATEWAY_URL_HERE',

    // ========================================
    // OpenAI API Configuration
    // ========================================
    // Get your API key from: https://platform.openai.com/api-keys
    // IMPORTANT: Keep this key secret! Never commit it to version control.
    OPENAI_API_KEY: 'YOUR_OPENAI_API_KEY_HERE',

    // ========================================
    // Optional: OpenAI Prompt API
    // ========================================
    // Only needed if you're using custom OpenAI prompts
    // Otherwise, the app uses standard Chat Completions API
    OPENAI_PROMPT_ID: 'YOUR_PROMPT_ID_HERE',
    OPENAI_PROMPT_VERSION: '1',

    // ========================================
    // User Configuration
    // ========================================
    // Default user ID for demo purposes
    // In production, this should come from authentication
    USER_ID: 'demo-user'
};

// Export configuration
window.CONFIG = CONFIG;

// ========================================
// Security Notes
// ========================================
// ⚠️ WARNING: This is a demo configuration!
// For production applications:
// 1. Move API keys to backend environment variables
// 2. Never expose keys in frontend code
// 3. Use AWS Secrets Manager or similar for sensitive data
// 4. Implement proper authentication (AWS Cognito, etc.)
// 5. Add API rate limiting and usage quotas
