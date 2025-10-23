import boto3
from boto3.dynamodb.conditions import Key
from decimal import Decimal
import json
import time
from datetime import datetime

# 初始化 DynamoDB 客户端
dynamodb = boto3.resource('dynamodb', region_name='us-east-1')
cards_table = dynamodb.Table('cards')
user_cards_table = dynamodb.Table('user-cards')

# ============ Cards 表操作 ============

def create_card(card_id, card_data):
    """
    创建新的银行卡信息

    示例:
    create_card('chase-sapphire-preferred', {
        'card_name': 'Chase Sapphire Preferred',
        'bank': 'Chase',
        'card_type': 'Credit Card',
        'annual_fee': 95,
        'cashback_categories': {
            'dining': {'rate': 3, 'description': '餐饮3%返现'},
            'travel': {'rate': 3, 'description': '旅行3%返现'},
            'default': {'rate': 1, 'description': '其他消费1%返现'}
        },
        'signup_bonus': '60000 points',
        'benefits': ['旅行保险', '租车保险', '免费酒店会员'],
        'image_url': 'https://example.com/card.jpg'
    })
    """
    item = {
        'card_id': card_id,
        'created_at': datetime.now().isoformat(),
        **card_data
    }

    response = cards_table.put_item(Item=item)
    return response

def get_card(card_id):
    """
    获取单张卡片信息
    """
    response = cards_table.get_item(Key={'card_id': card_id})
    return response.get('Item', None)

def get_all_cards():
    """
    获取所有卡片信息
    """
    response = cards_table.scan()
    return response.get('Items', [])

def update_card(card_id, update_data):
    """
    更新卡片信息
    """
    update_expression = "SET "
    expression_values = {}

    for key, value in update_data.items():
        update_expression += f"{key} = :{key}, "
        expression_values[f":{key}"] = value

    update_expression = update_expression.rstrip(", ")

    response = cards_table.update_item(
        Key={'card_id': card_id},
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values,
        ReturnValues="ALL_NEW"
    )
    return response

def delete_card(card_id):
    """
    删除卡片信息
    """
    response = cards_table.delete_item(Key={'card_id': card_id})
    return response

def search_cards_by_category(category):
    """
    根据返现类别搜索卡片（需要扫描）
    """
    response = cards_table.scan(
        FilterExpression='attribute_exists(cashback_categories.#cat)',
        ExpressionAttributeNames={'#cat': category}
    )
    return response.get('Items', [])

# ============ User-Cards 表操作 ============

def add_card_to_user(user_id, card_id, card_info=None):
    """
    为用户添加一张卡

    示例:
    add_card_to_user('user-001', 'chase-sapphire-preferred', {
        'card_name': 'Chase Sapphire Preferred',
        'bank': 'Chase',
        'notes': '主力卡',
        'last_four_digits': '1234'
    })
    """
    # 如果没有提供卡片信息，从 cards 表获取
    if not card_info:
        card = get_card(card_id)
        if not card:
            raise ValueError(f"Card {card_id} not found")
        card_info = {
            'card_name': card['card_name'],
            'bank': card['bank']
        }

    item = {
        'user_id': user_id,
        'card_id': card_id,
        'added_date': datetime.now().isoformat(),
        'card_status': 'active',
        **card_info
    }

    response = user_cards_table.put_item(Item=item)
    return response

def get_user_cards(user_id):
    """
    获取用户的所有卡片
    """
    response = user_cards_table.query(
        KeyConditionExpression=Key('user_id').eq(user_id)
    )
    return response.get('Items', [])

def get_user_card(user_id, card_id):
    """
    获取用户的特定卡片
    """
    response = user_cards_table.get_item(
        Key={
            'user_id': user_id,
            'card_id': card_id
        }
    )
    return response.get('Item', None)

def update_user_card(user_id, card_id, update_data):
    """
    更新用户的卡片信息（如备注、状态等）
    """
    update_expression = "SET "
    expression_values = {}

    for key, value in update_data.items():
        update_expression += f"{key} = :{key}, "
        expression_values[f":{key}"] = value

    update_expression = update_expression.rstrip(", ")

    response = user_cards_table.update_item(
        Key={
            'user_id': user_id,
            'card_id': card_id
        },
        UpdateExpression=update_expression,
        ExpressionAttributeValues=expression_values,
        ReturnValues="ALL_NEW"
    )
    return response

def remove_card_from_user(user_id, card_id):
    """
    从用户账户中移除卡片
    """
    response = user_cards_table.delete_item(
        Key={
            'user_id': user_id,
            'card_id': card_id
        }
    )
    return response

def get_user_active_cards(user_id):
    """
    获取用户的所有活跃卡片
    """
    response = user_cards_table.query(
        KeyConditionExpression=Key('user_id').eq(user_id),
        FilterExpression='card_status = :status',
        ExpressionAttributeValues={':status': 'active'}
    )
    return response.get('Items', [])

# ============ 高级查询 ============

def get_user_cards_with_details(user_id):
    """
    获取用户卡片及完整的卡片详情（联表查询）
    """
    # 获取用户的卡片
    user_cards = get_user_cards(user_id)

    # 获取每张卡的详细信息
    result = []
    for user_card in user_cards:
        card_details = get_card(user_card['card_id'])
        if card_details:
            # 合并用户卡片信息和卡片详情
            combined = {
                **card_details,
                'user_notes': user_card.get('notes', ''),
                'user_status': user_card.get('card_status', 'active'),
                'added_date': user_card.get('added_date', ''),
                'last_four_digits': user_card.get('last_four_digits', '')
            }
            result.append(combined)

    return result

def recommend_best_card_for_category(category):
    """
    推荐某个类别返现最高的卡
    """
    all_cards = get_all_cards()

    best_card = None
    highest_rate = 0

    for card in all_cards:
        categories = card.get('cashback_categories', {})
        if category in categories:
            rate = categories[category].get('rate', 0)
            if rate > highest_rate:
                highest_rate = rate
                best_card = card

    return best_card

# ============ 使用示例 ============

if __name__ == "__main__":
    # 1. 创建几张银行卡
    print("Creating cards...")

    create_card('chase-sapphire-preferred', {
        'card_name': 'Chase Sapphire Preferred',
        'bank': 'Chase',
        'card_type': 'Credit Card',
        'annual_fee': 95,
        'cashback_categories': {
            'dining': {'rate': 3, 'description': '餐饮3%返现'},
            'travel': {'rate': 3, 'description': '旅行3%返现'},
            'streaming': {'rate': 3, 'description': '流媒体3%返现'},
            'default': {'rate': 1, 'description': '其他消费1%返现'}
        },
        'signup_bonus': '60000 points',
        'benefits': ['旅行保险', '租车保险', 'Priority Pass'],
        'image_url': 'https://example.com/chase-sapphire.jpg'
    })

    create_card('amex-gold', {
        'card_name': 'American Express Gold Card',
        'bank': 'American Express',
        'card_type': 'Credit Card',
        'annual_fee': 250,
        'cashback_categories': {
            'dining': {'rate': 4, 'description': '餐饮4倍积分'},
            'grocery': {'rate': 4, 'description': '超市4倍积分'},
            'default': {'rate': 1, 'description': '其他消费1倍积分'}
        },
        'signup_bonus': '60000 points',
        'benefits': ['餐饮积分', '超市积分', 'Uber Credits'],
        'image_url': 'https://example.com/amex-gold.jpg'
    })

    # 2. 为用户添加卡片
    print("\nAdding cards to user...")

    add_card_to_user('user-001', 'chase-sapphire-preferred', {
        'card_name': 'Chase Sapphire Preferred',
        'bank': 'Chase',
        'notes': '主力旅行卡',
        'last_four_digits': '1234'
    })

    add_card_to_user('user-001', 'amex-gold', {
        'card_name': 'American Express Gold Card',
        'bank': 'American Express',
        'notes': '吃饭专用',
        'last_four_digits': '5678'
    })

    # 3. 查询用户的所有卡片
    print("\nUser's cards:")
    user_cards = get_user_cards('user-001')
    print(json.dumps(user_cards, indent=2, default=str))

    # 4. 获取用户卡片的完整信息
    print("\nUser's cards with full details:")
    detailed_cards = get_user_cards_with_details('user-001')
    print(json.dumps(detailed_cards, indent=2, default=str))

    # 5. 推荐餐饮返现最高的卡
    print("\nBest card for dining:")
    best_dining_card = recommend_best_card_for_category('dining')
    print(json.dumps(best_dining_card, indent=2, default=str))

    # 6. 更新用户卡片状态
    print("\nUpdating card status...")
    update_user_card('user-001', 'chase-sapphire-preferred', {
        'notes': '主力旅行卡 - 已激活所有福利',
        'card_status': 'active'
    })
