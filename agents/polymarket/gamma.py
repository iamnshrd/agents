import httpx
import time
import os
from typing import Any
from agents.utils.metrics import gamma_requests_total, gamma_cache_hits_total
import json
from agents.utils.objects import Market, PolymarketEvent, ClobReward, Tag


class GammaMarketClient:
    def __init__(self):
        self.gamma_url = "https://gamma-api.polymarket.com"
        self.gamma_markets_endpoint = self.gamma_url + "/markets"
        self.gamma_events_endpoint = self.gamma_url + "/events"
        self._client = httpx.Client(timeout=httpx.Timeout(10.0, connect=5.0))

        # Throttling config
        try:
            self._req_per_sec = float(os.getenv("GAMMA_RPS", "5"))
        except Exception:
            self._req_per_sec = 5.0
        self._min_interval = 1.0 / max(0.1, self._req_per_sec)
        self._last_req_ts = 0.0

        # Cache config
        try:
            self._cache_ttl_seconds = float(os.getenv("GAMMA_CACHE_TTL", "120"))
        except Exception:
            self._cache_ttl_seconds = 120.0
        self._markets_cache: dict[str, tuple[list[Any], float]] = {}
        self._events_cache: dict[str, tuple[list[Any], float]] = {}

        # Pagination safety cap
        try:
            self._max_pages = int(os.getenv("GAMMA_MAX_PAGES", "100"))
        except Exception:
            self._max_pages = 100

    def parse_pydantic_market(self, market_object: dict) -> Market:
        try:
            if "clobRewards" in market_object:
                clob_rewards: list[ClobReward] = []
                for clob_rewards_obj in market_object["clobRewards"]:
                    clob_rewards.append(ClobReward(**clob_rewards_obj))
                market_object["clobRewards"] = clob_rewards

            if "events" in market_object:
                events: list[PolymarketEvent] = []
                for market_event_obj in market_object["events"]:
                    events.append(self.parse_nested_event(market_event_obj))
                market_object["events"] = events

            # These two fields below are returned as stringified lists from the api
            if "outcomePrices" in market_object:
                market_object["outcomePrices"] = json.loads(
                    market_object["outcomePrices"]
                )
            if "clobTokenIds" in market_object:
                market_object["clobTokenIds"] = json.loads(
                    market_object["clobTokenIds"]
                )

            return Market(**market_object)
        except Exception as err:
            print(f"[parse_market] Caught exception: {err}")
            print("exception while handling object:", market_object)

    # Event parser for events nested under a markets api response
    def parse_nested_event(self, event_object: dict()) -> PolymarketEvent:
        print("[parse_nested_event] called with:", event_object)
        try:
            if "tags" in event_object:
                print("tags here", event_object["tags"])
                tags: list[Tag] = []
                for tag in event_object["tags"]:
                    tags.append(Tag(**tag))
                event_object["tags"] = tags

            return PolymarketEvent(**event_object)
        except Exception as err:
            print(f"[parse_event] Caught exception: {err}")
            print("\n", event_object)

    def parse_pydantic_event(self, event_object: dict) -> PolymarketEvent:
        try:
            if "tags" in event_object:
                print("tags here", event_object["tags"])
                tags: list[Tag] = []
                for tag in event_object["tags"]:
                    tags.append(Tag(**tag))
                event_object["tags"] = tags
            return PolymarketEvent(**event_object)
        except Exception as err:
            print(f"[parse_event] Caught exception: {err}")

    def _throttle(self) -> None:
        now = time.time()
        wait = self._min_interval - (now - self._last_req_ts)
        if wait > 0:
            time.sleep(wait)
        self._last_req_ts = time.time()

    def _cache_key(self, params: dict | None) -> str:
        if not params:
            return "{}"
        try:
            items = sorted(params.items(), key=lambda x: x[0])
            return "&".join([f"{k}={v}" for k, v in items])
        except Exception:
            return str(params)

    def get_markets(
        self, querystring_params={}, parse_pydantic=False, local_file_path=None
    ) -> "list[Market]":
        if parse_pydantic and local_file_path is not None:
            raise Exception(
                'Cannot use "parse_pydantic" and "local_file" params simultaneously.'
            )

        # Cache lookup
        key = self._cache_key(querystring_params)
        cached = self._markets_cache.get(key)
        if cached:
            data, ts = cached
            if time.time() - ts <= self._cache_ttl_seconds:
                gamma_cache_hits_total.labels(resource="markets").inc()
                return data if not parse_pydantic else [self.parse_pydantic_market(o) for o in data]

        response = self._get_with_retries(self.gamma_markets_endpoint, params=querystring_params)
        if response.status_code == 200:
            gamma_requests_total.labels(endpoint="markets", status="200").inc()
            data = response.json()
            if local_file_path is not None:
                with open(local_file_path, "w+") as out_file:
                    json.dump(data, out_file)
            elif not parse_pydantic:
                # store in cache
                self._markets_cache[key] = (data, time.time())
                return data
            else:
                markets: list[Market] = []
                for market_object in data:
                    markets.append(self.parse_pydantic_market(market_object))
                self._markets_cache[key] = (data, time.time())
                return markets
        else:
            try:
                gamma_requests_total.labels(endpoint="markets", status=str(response.status_code)).inc()
            except Exception:
                pass
            print(f"Error response returned from api: HTTP {response.status_code}")
            raise Exception()

    def get_events(
        self, querystring_params={}, parse_pydantic=False, local_file_path=None
    ) -> "list[PolymarketEvent]":
        if parse_pydantic and local_file_path is not None:
            raise Exception(
                'Cannot use "parse_pydantic" and "local_file" params simultaneously.'
            )

        # Cache lookup
        key = self._cache_key(querystring_params)
        cached = self._events_cache.get(key)
        if cached:
            data, ts = cached
            if time.time() - ts <= self._cache_ttl_seconds:
                gamma_cache_hits_total.labels(resource="events").inc()
                return data if not parse_pydantic else [self.parse_pydantic_event(o) for o in data]

        response = self._get_with_retries(self.gamma_events_endpoint, params=querystring_params)
        if response.status_code == 200:
            gamma_requests_total.labels(endpoint="events", status="200").inc()
            data = response.json()
            if local_file_path is not None:
                with open(local_file_path, "w+") as out_file:
                    json.dump(data, out_file)
            elif not parse_pydantic:
                self._events_cache[key] = (data, time.time())
                return data
            else:
                events: list[PolymarketEvent] = []
                for market_event_obj in data:
                    events.append(self.parse_event(market_event_obj))
                self._events_cache[key] = (data, time.time())
                return events
        else:
            try:
                gamma_requests_total.labels(endpoint="events", status=str(response.status_code)).inc()
            except Exception:
                pass
            raise Exception()

    def get_all_markets(self, limit=2) -> "list[Market]":
        return self.get_markets(querystring_params={"limit": limit})

    def get_all_events(self, limit=2) -> "list[PolymarketEvent]":
        return self.get_events(querystring_params={"limit": limit})

    def get_current_markets(self, limit=4) -> "list[Market]":
        return self.get_markets(
            querystring_params={
                "active": True,
                "closed": False,
                "archived": False,
                "limit": limit,
            }
        )

    def get_all_current_markets(self, limit=100) -> "list[Market]":
        offset = 0
        all_markets = []
        pages = 0
        while True:
            params = {
                "active": True,
                "closed": False,
                "archived": False,
                "limit": limit,
                "offset": offset,
            }
            market_batch = self.get_markets(querystring_params=params)
            all_markets.extend(market_batch)

            if len(market_batch) < limit:
                break
            offset += limit
            pages += 1
            if pages >= self._max_pages:
                break

        return all_markets

    def get_current_events(self, limit=4) -> "list[PolymarketEvent]":
        return self.get_events(
            querystring_params={
                "active": True,
                "closed": False,
                "archived": False,
                "limit": limit,
            }
        )

    def get_clob_tradable_markets(self, limit=2) -> "list[Market]":
        return self.get_markets(
            querystring_params={
                "active": True,
                "closed": False,
                "archived": False,
                "limit": limit,
                "enableOrderBook": True,
            }
        )

    def get_market(self, market_id: int) -> dict():
        url = self.gamma_markets_endpoint + "/" + str(market_id)
        print(url)
        response = self._get_with_retries(url)
        return response.json()

    def _get_with_retries(self, url: str, params: dict | None = None, retries: int = 3, backoff: float = 0.5) -> httpx.Response:
        last_exc = None
        for attempt in range(1, retries + 1):
            try:
                self._throttle()
                resp = self._client.get(url, params=params)
                if resp.status_code == 200:
                    return resp
                # retry on transient statuses
                if resp.status_code in {408, 429, 500, 502, 503, 504}:
                    time.sleep(backoff * attempt)
                    continue
                return resp
            except httpx.HTTPError as e:
                last_exc = e
                time.sleep(backoff * attempt)
        if last_exc:
            raise last_exc
        raise Exception("Request failed without exception")


if __name__ == "__main__":
    gamma = GammaMarketClient()
    market = gamma.get_market("253123")
    try:
        # Lazy import to avoid heavy dependency when not needed
        from agents.polymarket.polymarket import Polymarket
        poly = Polymarket()
        obj = poly.map_api_to_market(market)
        print(obj)
    except Exception as e:
        print(f"Polymarket demo disabled: {e}")
