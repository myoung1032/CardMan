import json
import boto3
import os
from decimal import Decimal
from datetime import datetime

# Initialize AWS services
dynamodb = boto3.resource('dynamodb')
cards_table = dynamodb.Table(os.environ.get('CARDS_TABLE', 'cards'))
user_cards_table = dynamodb.Table(os.environ.get('USER_CARDS_TABLE', 'user-cards'))

# Custom JSON encoder for DynamoDB Decimal types
class DecimalEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, Decimal):
            return float(obj)
        return super(DecimalEncoder, self).default(obj)

# CORS headers
CORS_HEADERS = {
    'Access-Control-Allow-Origin': '*',
    'Access-Control-Allow-Headers': 'Content-Type,X-Amz-Date,Authorization,X-Api-Key,X-Amz-Security-Token',
    'Access-Control-Allow-Methods': 'GET,POST,PUT,DELETE,OPTIONS'
}

def lambda_handler(event, context):
    """
    Main Lambda handler for CardMan API
    Compatible with both API Gateway payload format 1.0 and 2.0
    """
    print(f"Event: {json.dumps(event)}")

    # Detect payload format version and normalize
    if 'requestContext' in event and 'http' in event['requestContext']:
        # Payload format 2.0
        method = event['requestContext']['http']['method']
        path = event['rawPath']
        body = event.get('body', '{}')
    else:
        # Payload format 1.0
        method = event.get('httpMethod', 'GET')
        path = event.get('path', '/')
        body = event.get('body', '{}')

    # Handle OPTIONS (CORS preflight)
    if method == 'OPTIONS':
        return {
            'statusCode': 200,
            'headers': CORS_HEADERS,
            'body': ''
        }

    try:
        # Route to appropriate handler
        if path == '/api/cards':
            if method == 'GET':
                return get_all_cards()
            elif method == 'POST':
                body_data = json.loads(body) if body else {}
                return create_card(body_data)

        elif path.startswith('/api/cards/') and len(path.split('/')) == 4:
            card_id = path.split('/')[-1]
            if method == 'GET':
                return get_card(card_id)
            elif method == 'DELETE':
                return delete_card(card_id)

        elif path.startswith('/api/users/') and path.endswith('/cards'):
            # /api/users/{user_id}/cards
            user_id = path.split('/')[-2]
            if method == 'GET':
                return get_user_cards(user_id)
            elif method == 'POST':
                body_data = json.loads(body) if body else {}
                return add_card_to_user(user_id, body_data)

        elif path.startswith('/api/users/') and path.count('/') == 5:
            # /api/users/{user_id}/cards/{card_id}
            parts = path.split('/')
            user_id = parts[3]
            card_id = parts[5]
            if method == 'DELETE':
                return remove_card_from_user(user_id, card_id)

        # Route not found
        return response(404, {'error': 'Route not found', 'path': path, 'method': method})

    except Exception as e:
        print(f"Error: {str(e)}")
        import traceback
        traceback.print_exc()
        return response(500, {'error': str(e)})

# ============ Cards Table Operations ============

def get_all_cards():
    """Get all cards from the cards table"""
    try:
        result = cards_table.scan()
        items = result.get('Items', [])

        # Handle pagination if there are many items
        while 'LastEvaluatedKey' in result:
            result = cards_table.scan(ExclusiveStartKey=result['LastEvaluatedKey'])
            items.extend(result.get('Items', []))

        return response(200, {'cards': items})
    except Exception as e:
        return response(500, {'error': f'Failed to get cards: {str(e)}'})

def get_card(card_id):
    """Get a specific card by ID"""
    try:
        result = cards_table.get_item(Key={'card_id': card_id})

        if 'Item' not in result:
            return response(404, {'error': 'Card not found'})

        return response(200, result['Item'])
    except Exception as e:
        return response(500, {'error': f'Failed to get card: {str(e)}'})

def create_card(data):
    """Create a new card"""
    try:
        # Validate required fields
        required_fields = ['card_id', 'card_name', 'bank', 'cashback_categories']
        for field in required_fields:
            if field not in data:
                return response(400, {'error': f'Missing required field: {field}'})

        # Check if card already exists
        existing = cards_table.get_item(Key={'card_id': data['card_id']})
        if 'Item' in existing:
            return response(400, {'error': 'Card ID already exists'})

        # Convert float and numeric strings to Decimal for DynamoDB
        def convert_to_decimal(obj):
            if isinstance(obj, float):
                return Decimal(str(obj))
            elif isinstance(obj, str):
                # Try to convert numeric strings to Decimal
                try:
                    # Check if string looks like a number
                    if obj.replace('.', '', 1).replace('-', '', 1).isdigit():
                        return Decimal(obj)
                except:
                    pass
                return obj
            elif isinstance(obj, dict):
                return {k: convert_to_decimal(v) for k, v in obj.items()}
            elif isinstance(obj, list):
                return [convert_to_decimal(item) for item in obj]
            return obj

        # Add metadata and convert types
        item = convert_to_decimal({
            **data,
            'created_at': datetime.now().isoformat()
        })

        # Save to DynamoDB
        cards_table.put_item(Item=item)

        return response(201, {'message': 'Card created successfully', 'card': item})

    except Exception as e:
        return response(500, {'error': f'Failed to create card: {str(e)}'})

def delete_card(card_id):
    """Delete a card"""
    try:
        # Check if card exists
        result = cards_table.get_item(Key={'card_id': card_id})
        if 'Item' not in result:
            return response(404, {'error': 'Card not found'})

        # Delete from cards table
        cards_table.delete_item(Key={'card_id': card_id})

        return response(200, {'message': 'Card deleted successfully'})

    except Exception as e:
        return response(500, {'error': f'Failed to delete card: {str(e)}'})

# ============ User Cards Table Operations ============

def get_user_cards(user_id):
    """Get all cards for a specific user"""
    try:
        result = user_cards_table.query(
            KeyConditionExpression='user_id = :uid',
            ExpressionAttributeValues={':uid': user_id}
        )

        user_cards = result.get('Items', [])

        # Get full card details for each user card
        detailed_cards = []
        for user_card in user_cards:
            card_id = user_card['card_id']
            card_result = cards_table.get_item(Key={'card_id': card_id})

            if 'Item' in card_result:
                # Merge user card info with full card details
                detailed_card = {
                    **card_result['Item'],
                    'added_date': user_card.get('added_date'),
                    'card_status': user_card.get('card_status'),
                    'user_notes': user_card.get('notes', '')
                }
                detailed_cards.append(detailed_card)

        return response(200, detailed_cards)

    except Exception as e:
        return response(500, {'error': f'Failed to get user cards: {str(e)}'})

def add_card_to_user(user_id, data):
    """Add a card to user's wallet"""
    try:
        # Validate
        if 'card_id' not in data:
            return response(400, {'error': 'Missing card_id'})

        card_id = data['card_id']

        # Check if card exists
        card_result = cards_table.get_item(Key={'card_id': card_id})
        if 'Item' not in card_result:
            return response(404, {'error': 'Card not found'})

        # Check if user already has this card
        existing = user_cards_table.get_item(
            Key={'user_id': user_id, 'card_id': card_id}
        )
        if 'Item' in existing:
            return response(400, {'error': 'User already has this card'})

        # Add to user's wallet
        user_card_item = {
            'user_id': user_id,
            'card_id': card_id,
            'card_name': card_result['Item']['card_name'],
            'bank': card_result['Item']['bank'],
            'added_date': datetime.now().isoformat(),
            'card_status': 'active',
            'notes': data.get('notes', '')
        }

        user_cards_table.put_item(Item=user_card_item)

        return response(201, {
            'message': 'Card added to wallet successfully',
            'user_card': user_card_item
        })

    except Exception as e:
        return response(500, {'error': f'Failed to add card to user: {str(e)}'})

def remove_card_from_user(user_id, card_id):
    """Remove a card from user's wallet"""
    try:
        # Check if user has this card
        result = user_cards_table.get_item(
            Key={'user_id': user_id, 'card_id': card_id}
        )
        if 'Item' not in result:
            return response(404, {'error': 'Card not found in user wallet'})

        # Remove from wallet
        user_cards_table.delete_item(
            Key={'user_id': user_id, 'card_id': card_id}
        )

        return response(200, {'message': 'Card removed from wallet successfully'})

    except Exception as e:
        return response(500, {'error': f'Failed to remove card from user: {str(e)}'})

# ============ Helper Functions ============

def response(status_code, body):
    """Create HTTP response with CORS headers"""
    return {
        'statusCode': status_code,
        'headers': CORS_HEADERS,
        'body': json.dumps(body, cls=DecimalEncoder)
    }
