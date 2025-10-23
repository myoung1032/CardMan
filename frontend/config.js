// CardMan API Configuration
// Replace the values below with your actual configuration

const CONFIG = {
    // DynamoDB API Gateway URL
    // Get this from: AWS Console → API Gateway → Your API → Stages → Invoke URL
    API_URL: 'YOUR_API_GATEWAY_URL_HERE',
    // Example: 'https://xxxxxxxxxx.execute-api.us-east-1.amazonaws.com'

    // OpenAI API Configuration
    // Get your API key from: https://platform.openai.com/api-keys
    OPENAI_API_KEY: 'YOUR_OPENAI_API_KEY_HERE',

    // If using OpenAI Prompt API (optional)
    OPENAI_PROMPT_ID: 'YOUR_PROMPT_ID_HERE',
    OPENAI_PROMPT_VERSION: '1',

    // User ID for demo purposes (can be customized)
    USER_ID: 'demo-user'
};

// Export for use in other files
window.CONFIG = CONFIG;
