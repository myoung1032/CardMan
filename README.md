About the Project: CardMan – AI-Powered Credit Card Cashback Optimizer

##  Inspiration

Many people own multiple credit cards but rarely maximize their cashback potential because the reward structure is complex and dynamic: changing by category, time, or even specific merchants. I often found myself hesitating at checkout: “Which card should I use for dining?” or “Does this one give better travel points?”


That everyday frustration inspired CardMan, an intelligent AI agent that automatically identifies the best credit card for each purchase to help users earn more without thinking.

## What It Does

CardMan simplifies credit card management through an AI workflow:


Add Your Cards: Users upload either a photo of their cards or simply type the card name.


The image is parsed using AWS Bedrock’s foundation model via AgentCore to extract card identity and features.


If necessary, an external search (OpenAI gpt-4o-mini) cross-checks reward structures and verifies benefit details.


Detect Purchase Category: When a user uploads a receipt, product photo, or text like “I bought dinner at Chipotle”, CardMan uses natural language reasoning to detect the purchase type (e.g., dining, travel, gas).


Recommend the Best Card: The agent compares all available cards, their cashback multipliers, and category limits, then recommends the optimal card instantly.


\[
\text{BestCard} = \arg\max_{c \in \mathcal{C}} (r_c \times v_t)
\]


where \( r_c \) is the cashback rate for card \( c \), and \( v_t \) is the transaction value in category \( t \).


## How It’s Built


**Architecture Overview**


Frontend: Simple web interface where users upload photos or text.


Backend Stack:


Amazon Bedrock (GPT-OSS-120B for text + Nova Pro for image): Core reasoning engine that interprets card and transaction data.


AWS Lambda: Executes business logic and handles API calls.


API Gateway: Connects front-end requests to Lambda functions.


DynamoDB: Stores user card profiles, categories, and usage history.


External Tools: Optional OpenAI GPT-4o-mini integration for supplemental card detail lookups.


All components are modular and stateless, allowing easy scaling and reproducibility.


## What We Learned


Building an autonomous AI agent requires balancing reasoning and retrieval — Bedrock’s AgentCore made orchestration between LLM and APIs seamless.


Prompt engineering and structured reasoning (chain-of-thought-style decomposition) dramatically improved result accuracy.


AWS services such as Lambda + DynamoDB are ideal for lightweight, cost-effective deployments.


##  Challenges


Parsing credit card text and benefit tiers from raw images required strong OCR reasoning — combining Bedrock and GPT-4o-mini improved accuracy.


Handling ambiguous consumption categories (e.g., “Starbucks in Target”) demanded context-sensitive classification logic.


Managing data privacy and security while processing card details was critical — CardMan uses only anonymized metadata and does not store sensitive card numbers.


## Future Work


Integrate real-time transaction data via Plaid or bank APIs.


Expand to multi-country support with regional card benefits.


Add personalized financial insights, helping users optimize spending patterns over time.
