import os
import json
import ast
import re
from typing import List, Dict, Any

import math

from dotenv import load_dotenv
from openai import OpenAI

from agents.polymarket.gamma import GammaMarketClient as Gamma
from agents.connectors.chroma import PolymarketRAG as Chroma
from agents.utils.objects import SimpleEvent, SimpleMarket
from agents.application.prompts import Prompter
from agents.polymarket.polymarket import Polymarket
from agents.utils.market_dto import normalize_market

def retain_keys(data, keys_to_retain):
    if isinstance(data, dict):
        return {
            key: retain_keys(value, keys_to_retain)
            for key, value in data.items()
            if key in keys_to_retain
        }
    elif isinstance(data, list):
        return [retain_keys(item, keys_to_retain) for item in data]
    else:
        return data

class Executor:
    def __init__(self, default_model='gpt-3.5-turbo-16k') -> None:
        load_dotenv()
        max_token_model = {'gpt-3.5-turbo-16k':15000, 'gpt-4-1106-preview':95000}
        self.token_limit = max_token_model.get(default_model)
        self.prompter = Prompter()
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.default_model = default_model
        self.client = OpenAI(api_key=self.openai_api_key)
        self.gamma = Gamma()
        self.chroma = Chroma()
        self.polymarket = Polymarket()

    def _chat(self, prompt_text: str) -> str:
        response = self.client.chat.completions.create(
            model=self.default_model,
            messages=[{"role": "user", "content": prompt_text}],
            temperature=0,
        )
        return response.choices[0].message.content

    def get_llm_response(self, user_input: str) -> str:
        system_text = str(self.prompter.market_analyst())
        combined = f"{system_text}\n\n{user_input}"
        return self._chat(combined)

    def get_superforecast(
        self, event_title: str, market_question: str, outcome: str
    ) -> str:
        messages = self.prompter.superforecaster(
            description=event_title, question=market_question, outcome=outcome
        )
        return self._chat(messages)


    def estimate_tokens(self, text: str) -> int:
        # This is a rough estimate. For more accurate results, consider using a tokenizer.
        return len(text) // 4  # Assuming average of 4 characters per token

    def process_data_chunk(self, data1: List[Dict[Any, Any]], data2: List[Dict[Any, Any]], user_input: str) -> str:
        system_text = str(self.prompter.prompts_polymarket(data1=data1, data2=data2))
        combined = f"{system_text}\n\n{user_input}"
        return self._chat(combined)


    def divide_list(self, original_list, i):
        # Calculate the size of each sublist
        sublist_size = math.ceil(len(original_list) / i)
        
        # Use list comprehension to create sublists
        return [original_list[j:j+sublist_size] for j in range(0, len(original_list), sublist_size)]
    
    def get_polymarket_llm(self, user_input: str) -> str:
        data1 = self.gamma.get_current_events()
        data2 = self.gamma.get_current_markets()
        
        combined_data = str(self.prompter.prompts_polymarket(data1=data1, data2=data2))
        
        # Estimate total tokens
        total_tokens = self.estimate_tokens(combined_data)
        
        # Set a token limit (adjust as needed, leaving room for system and user messages)
        token_limit = self.token_limit
        if total_tokens <= token_limit:
            # If within limit, process normally
            return self.process_data_chunk(data1, data2, user_input)
        else:
            # If exceeding limit, process in chunks
            chunk_size = len(combined_data) // ((total_tokens // token_limit) + 1)
            print(f'total tokens {total_tokens} exceeding llm capacity, now will split and answer')
            group_size = (total_tokens // token_limit) + 1 # 3 is safe factor
            keys_no_meaning = ['image','pagerDutyNotificationEnabled','resolvedBy','endDate','clobTokenIds','negRiskMarketID','conditionId','updatedAt','startDate']
            useful_keys = ['id','questionID','description','liquidity','clobTokenIds','outcomes','outcomePrices','volume','startDate','endDate','question','questionID','events']
            data1 = retain_keys(data1, useful_keys)
            cut_1 = self.divide_list(data1, group_size)
            cut_2 = self.divide_list(data2, group_size)
            cut_data_12 = zip(cut_1, cut_2)

            results = []

            for cut_data in cut_data_12:
                sub_data1 = cut_data[0]
                sub_data2 = cut_data[1]
                sub_tokens = self.estimate_tokens(str(self.prompter.prompts_polymarket(data1=sub_data1, data2=sub_data2)))

                result = self.process_data_chunk(sub_data1, sub_data2, user_input)
                results.append(result)
            
            combined_result = " ".join(results)
            
        
            
            return combined_result
    def filter_events(self, events: "list[SimpleEvent]") -> str:
        prompt = self.prompter.filter_events(events)
        return self._chat(prompt)

    def filter_events_with_rag(self, events: "list[SimpleEvent]") -> str:
        prompt = self.prompter.filter_events()
        print()
        print("... prompting ... ", prompt)
        print()
        return self.chroma.events(events, prompt)

    def map_filtered_events_to_markets(
        self, filtered_events: "list[SimpleEvent]"
    ) -> "list[SimpleMarket]":
        markets = []
        for e in filtered_events:
            data = json.loads(e[0].json())
            market_ids = data["metadata"]["markets"].split(",")
            for market_id in market_ids:
                market_data = self.gamma.get_market(market_id)
                formatted_market_data = self.polymarket.map_api_to_market(market_data)
                markets.append(formatted_market_data)
        return markets

    def filter_markets(self, markets) -> "list[tuple]":
        prompt = self.prompter.filter_markets()
        print()
        print("... prompting ... ", prompt)
        print()
        return self.chroma.markets(markets, prompt)

    def filter_markets_simple(self, markets) -> list[dict]:
        """Heuristic filter without RAG/DB to avoid readonly issues."""
        normalized = []
        for m in markets:
            try:
                # markets may come as dicts or Documents; extract dict
                if isinstance(m, (list, tuple)) and m and hasattr(m[0], "dict"):
                    md = m[0].dict().get("metadata", {})
                elif hasattr(m, "dict"):
                    md = m.dict().get("metadata", {})
                elif isinstance(m, dict):
                    md = m
                else:
                    md = {}
                n = normalize_market(md)
                normalized.append(n)
            except Exception:
                continue
        # score by presence of prices, lower spread (if present), fallback to id
        def score(n: dict) -> tuple:
            prices = n.get("outcomePrices") or []
            has_price = 1 if prices else 0
            # spread may exist in original md; default high
            spread = md.get("spread", 0.5) if (md := n) else 0.5
            return (has_price, -float(spread), -n.get("id", 0))
        normalized.sort(key=score, reverse=True)
        # return top 20
        return normalized[:20]

    def source_best_trade(self, market_object) -> str:
        # Универсальная распаковка разных форматов market_object
        market = None
        description = ""
        try:
            # Формат: (Document, score)
            if isinstance(market_object, (list, tuple)) and market_object and hasattr(market_object[0], "dict"):
                market_document = market_object[0].dict()
                market = market_document.get("metadata", {})
                description = market_document.get("page_content", "")
            # Формат: dict с полями market
            elif isinstance(market_object, dict):
                market = market_object
                description = market.get("description", "")
            # Формат: список/кортеж, где нулевой элемент dict
            elif isinstance(market_object, (list, tuple)) and market_object and isinstance(market_object[0], dict):
                market = market_object[0]
                description = market.get("description", "")
        except Exception:
            pass

        if market is None:
            raise ValueError("Unsupported market_object format")

        # Нормализация рынка в единый формат
        n = normalize_market(market)
        outcome_prices = n.get("outcomePrices", [])
        outcomes = n.get("outcomes", [])
        question = n.get("question", "")

        # Fallback: если нет цен/исходов, пробуем получить цену из CLOB по token id
        if (not outcome_prices) or (len(outcome_prices) < 2):
            try:
                raw_ids = n.get("clobTokenIds", [])
                token_ids = raw_ids
                if isinstance(token_ids, list) and token_ids:
                    price = float(self.polymarket.get_orderbook_price_cached(str(token_ids[0])))
                    price = max(0.01, min(0.99, price))
                    outcome_prices = [price, round(1.0 - price, 4)]
                if not outcomes:
                    outcomes = ["Yes", "No"]
            except Exception:
                pass

        prompt = self.prompter.superforecaster(question, description, outcomes)
        print()
        print("... prompting ... ", prompt)
        print()
        content = self._chat(prompt)

        print("result: ", content)
        print()
        prompt = self.prompter.one_best_trade(content, outcomes, outcome_prices)
        print("... prompting ... ", prompt)
        print()
        content = self._chat(prompt)

        print("result: ", content)
        print()
        return content

    def format_trade_prompt_for_execution(self, best_trade: str) -> float:
        data = best_trade.split(",")
        # price = re.findall(r"\d+\.\d+", data[0])[0]
        size = re.findall(r"\d+\.\d+", data[1])[0]
        usdc_balance = self.polymarket.get_usdc_balance()
        return float(size) * usdc_balance

    def source_best_market_to_create(self, filtered_markets) -> str:
        prompt = self.prompter.create_new_market(filtered_markets)
        print()
        print("... prompting ... ", prompt)
        print()
        content = self._chat(prompt)
        return content
