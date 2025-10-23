// OpenAI API Helper Functions

/**
 * Call OpenAI API to search for card information by name
 * @param {string} cardName - The name of the credit card
 * @returns {Promise<Object>} Card information with cashback categories
 */
async function searchCardWithOpenAI(cardName) {
    try {
        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${CONFIG.OPENAI_API_KEY}`
            },
            body: JSON.stringify({
                model: "gpt-4o-mini",
                messages: [
                    {
                        role: "system",
                        content: `You are a credit card rewards expert. Return information in this EXACT JSON format:
{
  "card_name": "Full card name",
  "issuer": "Bank name",
  "cashback_categories": [
    {"category": "Category name", "rate": "X%"},
    {"category": "Another category", "rate": "Y%"}
  ],
  "notes": "Additional notes about the card"
}

IMPORTANT: cashback_categories must be an array with at least one category. Focus on cashback/rewards rates, NOT annual fees.`
                    },
                    {
                        role: "user",
                        content: `Find the cashback rates and reward categories for: ${cardName}`
                    }
                ],
                response_format: { type: "json_object" }
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.error('OpenAI API error:', errorData);
            throw new Error(`OpenAI API error: ${response.status} - ${errorData.error?.message || 'Unknown error'}`);
        }

        const data = await response.json();

        // Parse the response
        const cardInfo = JSON.parse(data.choices[0].message.content);

        return cardInfo;

    } catch (error) {
        console.error('Error calling OpenAI API:', error);
        throw error;
    }
}

/**
 * Call OpenAI API to analyze card image
 * @param {string} base64Image - Base64 encoded image
 * @returns {Promise<Object>} Card information extracted from image
 */
async function analyzeCardImage(base64Image) {
    try {
        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${CONFIG.OPENAI_API_KEY}`
            },
            body: JSON.stringify({
                model: "gpt-4o-mini",
                messages: [
                    {
                        role: "system",
                        content: `You are a credit card rewards expert. Analyze credit card images and return information in this EXACT JSON format:
{
  "card_name": "Full card name from the image",
  "issuer": "Bank name",
  "cashback_categories": [
    {"category": "Category name", "rate": "X%"},
    {"category": "Another category", "rate": "Y%"}
  ],
  "notes": "Additional notes"
}

IMPORTANT:
- cashback_categories must be an array with at least one category
- If you can't see cashback info on the card, use your knowledge to provide typical rates for this card
- Focus on rewards/cashback, NOT annual fees`
                    },
                    {
                        role: "user",
                        content: [
                            {
                                type: "text",
                                text: "Analyze this credit card image. Extract the card name and issuer from the image. Then provide the typical cashback categories and rates for this card based on your knowledge."
                            },
                            {
                                type: "image_url",
                                image_url: {
                                    url: `data:image/jpeg;base64,${base64Image}`
                                }
                            }
                        ]
                    }
                ],
                response_format: { type: "json_object" },
                max_tokens: 1000
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.error('OpenAI API error:', errorData);
            throw new Error(`OpenAI API error: ${response.status} - ${errorData.error?.message || 'Unknown error'}`);
        }

        const data = await response.json();

        // Parse the response
        const cardInfo = JSON.parse(data.choices[0].message.content);

        return cardInfo;

    } catch (error) {
        console.error('Error analyzing image:', error);
        throw error;
    }
}

/**
 * Convert OpenAI response format to DynamoDB format
 * @param {Object} aiResponse - Response from OpenAI API
 * @returns {Object} Card data in DynamoDB format
 */
function convertAIResponseToCardData(aiResponse) {
    console.log('Converting AI response:', aiResponse);

    // Validate required fields
    if (!aiResponse.card_name) {
        throw new Error('Missing card_name in AI response');
    }
    if (!aiResponse.issuer) {
        throw new Error('Missing issuer in AI response');
    }
    if (!aiResponse.cashback_categories || !Array.isArray(aiResponse.cashback_categories)) {
        console.warn('Missing or invalid cashback_categories, using empty object');
        aiResponse.cashback_categories = [];
    }

    // Convert cashback_categories array to object format
    const cashbackCategories = {};

    aiResponse.cashback_categories.forEach(cat => {
        if (!cat.category || !cat.rate) {
            console.warn('Skipping invalid category:', cat);
            return;
        }

        // Clean up category name (remove special characters, make lowercase)
        const categoryKey = cat.category.toLowerCase()
            .replace(/[^a-z0-9\s]/g, '')
            .replace(/\s+/g, '-')
            .substring(0, 30);

        // Extract rate number from string like "5%" or "1.5%"
        const rateMatch = cat.rate.toString().match(/[\d.]+/);
        const rateString = rateMatch ? rateMatch[0] : "0";

        // Keep as string for DynamoDB to avoid Float type error
        // Lambda will convert string to Decimal automatically
        const rate = parseFloat(rateString);

        cashbackCategories[categoryKey] = {
            rate: Number(rate.toFixed(2)),  // Ensure it's a clean number
            description: `${cat.category} - ${cat.rate}`
        };
    });

    // Generate card_id from card name
    const card_id = aiResponse.card_name.toLowerCase()
        .replace(/[^a-z0-9\s]/g, '')
        .replace(/\s+/g, '-');

    const result = {
        card_id: card_id,
        card_name: aiResponse.card_name,
        bank: aiResponse.issuer,
        card_type: 'Credit Card',
        cashback_categories: cashbackCategories
    };

    console.log('Converted card data:', result);
    return result;
}

/**
 * Recommend the best card for a purchase
 * @param {Array} cardList - List of all available cards
 * @param {string} purchaseDescription - Description of the purchase
 * @returns {Promise<Object>} Recommendation with best card and reasoning
 */
async function recommendBestCard(cardList, purchaseDescription) {
    try {
        console.log('Recommending card for:', purchaseDescription);
        console.log('Available cards:', cardList.length);

        // Format card list for the prompt
        const formattedCardList = cardList.map(card => {
            const categories = card.cashback_categories ?
                Object.entries(card.cashback_categories).map(([key, value]) =>
                    `${value.description || key}`
                ).join(', ') : 'No cashback info';

            return `${card.card_name} (${card.bank}): ${categories}`;
        }).join('\n');

        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${CONFIG.OPENAI_API_KEY}`
            },
            body: JSON.stringify({
                model: "gpt-4o-mini",
                messages: [
                    {
                        role: "system",
                        content: `You are a credit card cashback optimizer. Analyze purchases and recommend the best card to maximize cashback rewards. Return response in this JSON format:
{
  "recommended_card": "Card name",
  "purchase_category": "Detected category (e.g., dining, travel, gas)",
  "cashback_rate": "Rate for this category (e.g., 3%)",
  "reasoning": "Brief explanation why this card is best",
  "estimated_cashback": "Estimated cashback amount if purchase value is mentioned"
}`
                    },
                    {
                        role: "user",
                        content: `Available cards:\n${formattedCardList}\n\nPurchase: ${purchaseDescription}\n\nWhich card should I use to maximize cashback?`
                    }
                ],
                response_format: { type: "json_object" }
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.error('OpenAI API error:', errorData);
            throw new Error(`OpenAI API error: ${response.status} - ${errorData.error?.message || 'Unknown error'}`);
        }

        const data = await response.json();
        const recommendation = JSON.parse(data.choices[0].message.content);

        console.log('Recommendation:', recommendation);
        return recommendation;

    } catch (error) {
        console.error('Error recommending card:', error);
        throw error;
    }
}

/**
 * Analyze purchase image and recommend best card
 * @param {string} base64Image - Base64 encoded image
 * @param {Array} cardList - List of all available cards
 * @returns {Promise<Object>} Recommendation with best card and reasoning
 */
async function recommendCardFromImage(base64Image, cardList) {
    try {
        console.log('Analyzing purchase image...');
        console.log('Available cards:', cardList.length);

        // Format card list
        const formattedCardList = cardList.map(card => {
            const categories = card.cashback_categories ?
                Object.entries(card.cashback_categories).map(([key, value]) =>
                    `${value.description || key}`
                ).join(', ') : 'No cashback info';

            return `${card.card_name} (${card.bank}): ${categories}`;
        }).join('\n');

        const response = await fetch('https://api.openai.com/v1/chat/completions', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'Authorization': `Bearer ${CONFIG.OPENAI_API_KEY}`
            },
            body: JSON.stringify({
                model: "gpt-4o-mini",
                messages: [
                    {
                        role: "system",
                        content: `You are a credit card cashback optimizer. Analyze receipt/purchase images and recommend the best card to maximize cashback. Return response in this JSON format:
{
  "recommended_card": "Card name",
  "purchase_category": "Detected category",
  "purchase_description": "What was purchased",
  "cashback_rate": "Rate for this category",
  "reasoning": "Brief explanation",
  "estimated_cashback": "Estimated cashback if amount visible"
}`
                    },
                    {
                        role: "user",
                        content: [
                            {
                                type: "text",
                                text: `Available cards:\n${formattedCardList}\n\nAnalyze this receipt/purchase and recommend which card gives the best cashback.`
                            },
                            {
                                type: "image_url",
                                image_url: {
                                    url: `data:image/jpeg;base64,${base64Image}`
                                }
                            }
                        ]
                    }
                ],
                response_format: { type: "json_object" },
                max_tokens: 1000
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            console.error('OpenAI API error:', errorData);
            throw new Error(`OpenAI API error: ${response.status} - ${errorData.error?.message || 'Unknown error'}`);
        }

        const data = await response.json();
        const recommendation = JSON.parse(data.choices[0].message.content);

        console.log('Recommendation:', recommendation);
        return recommendation;

    } catch (error) {
        console.error('Error analyzing image:', error);
        throw error;
    }
}
